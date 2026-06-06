import pytest
from httpx import AsyncClient
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.infrastructure.db.models import TenderBOQItemORM
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository


@pytest.mark.asyncio
async def test_trigger_boq_extract_api(client: AsyncClient, db_session):
    t_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)

    # Insert Tender
    tender = Tender(
        id=uuid4(),
        tender_number="TND-API-BOQ-TRIG",
        department="Engineering",
        source_url="https://example.com/api-boq.pdf",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await t_repo.add(tender)

    # Insert Document
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="api-boq.pdf",
        file_path="tests/test_files/test_boq_replica.pdf",
        status=TenderDocumentStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)
    await db_session.commit()

    res = await client.post(f"/api/v1/tenders/{tender.id}/boq/extract")
    assert res.status_code == 202
    data = res.json()
    assert data["tender_id"] == str(tender.id)
    assert data["status"] == "PROCESSING"


@pytest.mark.asyncio
async def test_get_boq_items_api(client: AsyncClient, db_session):
    t_repo = SQLAlchemyTenderRepository(db_session)

    # Insert Tender
    tender = Tender(
        id=uuid4(),
        tender_number="TND-API-BOQ-GET",
        department="Engineering",
        source_url="https://example.com/api-boq-get.pdf",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await t_repo.add(tender)

    # Insert dummy BOQItem directly into DB
    boq_id = uuid4()
    orm_item = TenderBOQItemORM(
        id=boq_id,
        tender_id=tender.id,
        document_id=None,
        item_code="10A",
        item_name="Supplying and fitting rails",
        quantity=Decimal("50.50"),
        unit="Nos",
        unit_rate=Decimal("12000.00"),
        amount=Decimal("606000.00"),
        schedule_name="Schedule X",
        confidence=0.95,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(orm_item)
    await db_session.commit()

    res = await client.get(f"/api/v1/tenders/{tender.id}/boq")
    assert res.status_code == 200
    data = res.json()
    assert data["tender_id"] == str(tender.id)
    assert data["total"] == 1
    
    item = data["items"][0]
    assert item["id"] == str(boq_id)
    assert item["item_code"] == "10A"
    assert item["item_name"] == "Supplying and fitting rails"
    assert item["quantity"] == "50.50"
    assert item["unit"] == "Nos"
    assert item["unit_rate"] == "12000.00"
    assert item["amount"] == "606000.00"
    assert item["schedule_name"] == "Schedule X"
    assert item["confidence"] == 0.95
