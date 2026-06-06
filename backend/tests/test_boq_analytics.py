import pytest
from decimal import Decimal
from uuid import uuid4
from datetime import datetime, timezone
from httpx import AsyncClient

from app.domain.models import Tender, BOQItem, TenderStatus
from app.domain.exceptions import TenderNotFoundException
from app.application.boq_analytics_engine import BOQAnalyticsEngine
from app.application.boq_analytics_service import BOQAnalyticsService
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.boq import SQLAlchemyBOQItemRepository
from app.infrastructure.db.models import TenderBOQItemORM


def test_classify_item():
    engine = BOQAnalyticsEngine()
    
    assert engine.classify_item("Supply of optical fiber cable 24 Core") == "OFC"
    assert engine.classify_item("uninterruptible power supply system") == "UPS"
    assert engine.classify_item("Cisco Gigabit Ethernet Switch") == "Networking"
    assert engine.classify_item("Outdoor LED signage display board") == "Display Systems"
    assert engine.classify_item("Concrete reinforcement work for foundation") == "Civil Work"
    assert engine.classify_item("Copper wire earthing and MCB switchgear") == "Electrical Work"
    assert engine.classify_item("General office table and chairs") == "Others"


def test_analytics_engine_computations():
    engine = BOQAnalyticsEngine()
    tender_id = uuid4()
    now = datetime.now(timezone.utc)
    
    # Setup 12 dummy items with distinct amounts to check top 10 sorting
    items = []
    for i in range(12):
        items.append(
            BOQItem(
                id=uuid4(),
                tender_id=tender_id,
                item_code=str(i + 1),
                item_name=f"Item matching networking switch {i}",
                quantity=Decimal("10.0"),
                unit="Nos",
                unit_rate=Decimal(str((i + 1) * 100)),
                amount=Decimal(str((i + 1) * 1000)),
                schedule_name="Schedule A",
                confidence=1.0,
                created_at=now,
                updated_at=now
            )
        )
        
    summary = engine.compute_summary(items)
    assert summary["total_items"] == 12
    assert summary["total_quantity"] == Decimal("120.0")
    # Sum of 1000 to 12000 is 78000
    assert summary["total_estimated_value"] == Decimal("78000.0")
    
    # Verify top items contains 10 items sorted descending
    assert len(summary["top_items"]) == 10
    assert summary["top_items"][0].amount == Decimal("12000.0")
    assert summary["top_items"][9].amount == Decimal("3000.0")


def test_analytics_engine_categories():
    engine = BOQAnalyticsEngine()
    tender_id = uuid4()
    now = datetime.now(timezone.utc)
    
    items = [
        BOQItem(id=uuid4(), tender_id=tender_id, item_name="24 core OFC cable", amount=Decimal("10000.00"), created_at=now, updated_at=now),
        BOQItem(id=uuid4(), tender_id=tender_id, item_name="Cisco core Switch", amount=Decimal("20000.00"), created_at=now, updated_at=now),
        BOQItem(id=uuid4(), tender_id=tender_id, item_name="10 KVA UPS", amount=Decimal("30000.00"), created_at=now, updated_at=now),
        BOQItem(id=uuid4(), tender_id=tender_id, item_name="LED Display wall", amount=Decimal("40000.00"), created_at=now, updated_at=now),
    ]
    
    analysis = engine.compute_category_analysis(items)
    # total sum is 100000
    ofc_data = next(r for r in analysis if r["category"] == "OFC")
    assert ofc_data["item_count"] == 1
    assert ofc_data["total_value"] == Decimal("10000.00")
    assert ofc_data["percentage"] == Decimal("10.00")
    
    ups_data = next(r for r in analysis if r["category"] == "UPS")
    assert ups_data["item_count"] == 1
    assert ups_data["total_value"] == Decimal("30000.00")
    assert ups_data["percentage"] == Decimal("30.00")


@pytest.mark.asyncio
async def test_boq_analytics_service_missing_tender(db_session):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    boq_repo = SQLAlchemyBOQItemRepository(db_session)
    engine = BOQAnalyticsEngine()
    
    service = BOQAnalyticsService(tender_repo, boq_repo, engine)
    
    with pytest.raises(TenderNotFoundException):
        await service.get_summary(uuid4())
        
    with pytest.raises(TenderNotFoundException):
        await service.get_category_analysis(uuid4())


@pytest.mark.asyncio
async def test_boq_analytics_endpoints(client: AsyncClient, db_session):
    t_repo = SQLAlchemyTenderRepository(db_session)
    
    tender = Tender(
        id=uuid4(),
        tender_number="TND-ANALYTICS-API",
        department="IT Division",
        source_url="http://x.pdf",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    await t_repo.add(tender)
    
    # Add items directly
    item = TenderBOQItemORM(
        id=uuid4(),
        tender_id=tender.id,
        item_code="1",
        item_name="OFC Optical fiber installation",
        quantity=Decimal("5.0"),
        unit="Mtr",
        unit_rate=Decimal("1000.0"),
        amount=Decimal("5000.0"),
        confidence=1.0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    db_session.add(item)
    await db_session.commit()
    
    # Test GET Summary endpoint
    res_summary = await client.get(f"/api/v1/tenders/{tender.id}/boq/summary")
    assert res_summary.status_code == 200
    sum_data = res_summary.json()
    assert sum_data["total_items"] == 1
    assert sum_data["total_quantity"] == "5.0"
    assert sum_data["total_estimated_value"] == "5000.0"
    assert len(sum_data["top_items"]) == 1
    assert sum_data["top_items"][0]["item_code"] == "1"

    # Test GET Categories endpoint
    res_categories = await client.get(f"/api/v1/tenders/{tender.id}/boq/categories")
    assert res_categories.status_code == 200
    cat_data = res_categories.json()
    assert cat_data["tender_id"] == str(tender.id)
    assert len(cat_data["categories"]) == 7  # All 7 categories should be included
    
    ofc_entry = next(c for c in cat_data["categories"] if c["category"] == "OFC")
    assert ofc_entry["item_count"] == 1
    assert ofc_entry["total_value"] == "5000.0"
    assert ofc_entry["percentage"] == "100.00"
