import pytest
from decimal import Decimal
from datetime import date, datetime, timezone
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Tender, TenderMetadata, TenderStatus
from app.domain.exceptions import TenderNotFoundException, TenderNotParsedException
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository
from app.application.risk_engine import RiskEngine
from app.application.risk_service import RiskService
from app.schemas.risk import RiskSeverity, RiskCategory


# ==========================================
# 1. UNIT TESTS FOR RISK ENGINE
# ==========================================

def test_performance_guarantee_rules():
    engine = RiskEngine()

    # Case 1: No keywords
    res = engine.evaluate_performance_guarantee("This is a simple contract.")
    assert res["severity"] == RiskSeverity.NONE
    assert res["score"] == 0.0

    # Case 2: High risk (> 10%)
    res = engine.evaluate_performance_guarantee("Performance Guarantee of 12% is required.")
    assert res["severity"] == RiskSeverity.HIGH
    assert res["score"] == 8.5
    assert "12" in res["evidence"]

    # Case 3: Medium risk (5% to 10%)
    res = engine.evaluate_performance_guarantee("A Security Deposit of 7.5% must be submitted.")
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0
    assert "7.5" in res["evidence"]

    # Case 4: Low risk (< 5%)
    res = engine.evaluate_performance_guarantee("Performance BG is 3.5% of contract value.")
    assert res["severity"] == RiskSeverity.LOW
    assert res["score"] == 2.0
    assert "3.5" in res["evidence"]

    # Case 5: Keyword found, no percentage parsed
    res = engine.evaluate_performance_guarantee("Bidders must provide a Bank Guarantee as performance security.")
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0
    assert "not found" in res["evidence"]


def test_liquidated_damages_rules():
    engine = RiskEngine()

    # Case 1: No keywords
    res = engine.evaluate_liquidated_damages("Standard terms apply.")
    assert res["severity"] == RiskSeverity.NONE
    assert res["score"] == 0.0

    # Case 2: High risk (> 10%)
    res = engine.evaluate_liquidated_damages("Liquidated Damages: 0.5% per week up to a maximum cap of 15%.")
    assert res["severity"] == RiskSeverity.HIGH
    assert res["score"] == 8.5

    # Case 3: Medium risk (5% to 10% or default)
    res = engine.evaluate_liquidated_damages("Delay penalty clause is capped at 10%.")
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0

    # Case 4: Low risk (< 5%)
    res = engine.evaluate_liquidated_damages("Penalty for delay is 2% total.")
    assert res["severity"] == RiskSeverity.LOW
    assert res["score"] == 2.0


def test_oem_dependency_rules():
    engine = RiskEngine()

    # Case 1: No keywords
    res = engine.evaluate_oem_dependency("No OEM specifications.")
    assert res["severity"] == RiskSeverity.NONE
    assert res["score"] == 0.0

    # Case 2: Keyword present
    res = engine.evaluate_oem_dependency("Bidders must provide a Manufacturer's Authorization Form (MAF).")
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0
    assert "MAF" in res["evidence"]


def test_short_completion_time_rules():
    engine = RiskEngine()

    # Case 1: High risk (< 90 days and > 50 Lakhs)
    res = engine.evaluate_short_completion_time(
        completion_period="60 days",
        tender_value=Decimal("6000000.00"),
        raw_text="Urgent execution needed."
    )
    assert res["severity"] == RiskSeverity.HIGH
    assert res["score"] == 8.5

    # Case 2: Medium risk (< 180 days)
    res = engine.evaluate_short_completion_time(
        completion_period="120 days",
        tender_value=Decimal("1000000.00"),
        raw_text="Standard schedule."
    )
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0

    # Case 3: Low risk (tightness keywords, but period >= 180 days)
    res = engine.evaluate_short_completion_time(
        completion_period="240 days",
        tender_value=Decimal("1000000.00"),
        raw_text="The schedule contains a tight timeline."
    )
    assert res["severity"] == RiskSeverity.LOW
    assert res["score"] == 2.0

    # Case 4: No risk
    res = engine.evaluate_short_completion_time(
        completion_period="360 days",
        tender_value=Decimal("1000000.00"),
        raw_text="Standard project duration."
    )
    assert res["severity"] == RiskSeverity.NONE
    assert res["score"] == 0.0


def test_emd_rules():
    engine = RiskEngine()

    # Case 1: High risk (> 5%)
    res = engine.evaluate_emd(
        emd=Decimal("60000.00"),
        tender_value=Decimal("1000000.00"),
        raw_text=""
    )
    assert res["severity"] == RiskSeverity.HIGH
    assert res["score"] == 8.5

    # Case 2: Medium risk (2% to 5%)
    res = engine.evaluate_emd(
        emd=Decimal("35000.00"),
        tender_value=Decimal("1000000.00"),
        raw_text=""
    )
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0

    # Case 3: Low risk (< 2%)
    res = engine.evaluate_emd(
        emd=Decimal("10000.00"),
        tender_value=Decimal("1000000.00"),
        raw_text=""
    )
    assert res["severity"] == RiskSeverity.LOW
    assert res["score"] == 2.0

    # Case 4: Fallback keywords
    res = engine.evaluate_emd(
        emd=None,
        tender_value=None,
        raw_text="Earnest Money Deposit details are enclosed."
    )
    assert res["severity"] == RiskSeverity.LOW
    assert res["score"] == 2.0


def test_special_clauses_rules():
    engine = RiskEngine()

    # Case 1: High risk (JV restrictions)
    res = engine.evaluate_special_clauses("Joint Venture (JV) is not allowed under any circumstances.")
    assert res["severity"] == RiskSeverity.HIGH
    assert res["score"] == 8.5
    assert "JV is not allowed" in res["evidence"]

    # Case 2: Medium risk (Arbitration)
    res = engine.evaluate_special_clauses("Disputes will be settled via Arbitration in Delhi.")
    assert res["severity"] == RiskSeverity.MEDIUM
    assert res["score"] == 5.0

    # Case 3: No risk
    res = engine.evaluate_special_clauses("Standard boilerplate clauses.")
    assert res["severity"] == RiskSeverity.NONE
    assert res["score"] == 0.0


# ==========================================
# 2. SERVICE ORCHESTRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_risk_service_success(db_session: AsyncSession):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)
    engine = RiskEngine()
    service = RiskService(tender_repo, metadata_repo, engine)

    tender_id = uuid4()
    # Insert dummy Tender
    tender = Tender(
        id=tender_id,
        tender_number="TND-RISK-TEST",
        department="Engineering",
        source_url="http://example.com/risk.pdf",
        tender_value=Decimal("6000000.00"), # 60 Lakhs
        closing_date=date.today(),
        status=TenderStatus.PARSED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Insert metadata triggering some risks: OEM, JV restrict, and High EMD (350k / 6M = 5.8%)
    metadata = TenderMetadata(
        id=uuid4(),
        tender_id=tender_id,
        document_id=None,
        tender_number="TND-RISK-TEST",
        tender_value=Decimal("6000000.00"),
        emd=Decimal("350000.00"), # High EMD (>5%)
        completion_period="60 days", # Short completion (<90 days + >50 Lakhs = High Risk)
        raw_text="Bidders must submit a Manufacturer's Authorization Form (MAF). Joint Venture (JV) is not allowed.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await metadata_repo.add(metadata)
    await db_session.commit()

    # Execute service
    result = await service.analyze_tender_risks(tender_id)

    assert result["tender_id"] == tender_id
    # Scores:
    # 1. Performance Guarantee: 0.0 (None)
    # 2. Liquidated Damages: 0.0 (None)
    # 3. OEM Dependency: 5.0 (Medium)
    # 4. Short Completion Time: 8.5 (High)
    # 5. High EMD: 8.5 (High)
    # 6. Special Clauses: 8.5 (High)
    # Sum: 30.5 / 6 = 5.08
    assert result["overall_risk_score"] == 5.08
    assert result["overall_risk_category"] == RiskCategory.MEDIUM
    assert len(result["risks_detected"]) == 6
    assert len(result["recommendations"]) == 4 # OEM, Short Completion, EMD, Special Clauses


@pytest.mark.asyncio
async def test_risk_service_exceptions(db_session: AsyncSession):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)
    engine = RiskEngine()
    service = RiskService(tender_repo, metadata_repo, engine)

    # Tender does not exist
    with pytest.raises(TenderNotFoundException):
        await service.analyze_tender_risks(uuid4())

    # Tender exists but no metadata (not parsed)
    tender_id = uuid4()
    tender = Tender(
        id=tender_id,
        tender_number="TND-UNPARSED",
        department="Engineering",
        source_url="http://x",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)
    await db_session.commit()

    with pytest.raises(TenderNotParsedException):
        await service.analyze_tender_risks(tender_id)


# ==========================================
# 3. API ROUTER INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_risk_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)

    tender_id = uuid4()
    tender = Tender(
        id=tender_id,
        tender_number="TND-API-RISK",
        department="Engineering",
        source_url="http://x",
        tender_value=Decimal("100000.00"),
        closing_date=date.today(),
        status=TenderStatus.PARSED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    metadata = TenderMetadata(
        id=uuid4(),
        tender_id=tender_id,
        tender_number="TND-API-RISK",
        tender_value=Decimal("100000.00"),
        emd=Decimal("1000.00"),
        completion_period="12 Months",
        raw_text="No special risks in this document.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await metadata_repo.add(metadata)
    await db_session.commit()

    # Success Case
    response = await client.post(f"/api/v1/tenders/{tender_id}/risk")
    assert response.status_code == 200
    data = response.json()
    assert data["tender_id"] == str(tender_id)
    assert data["overall_risk_score"] == 0.33  # EMD = 1.0% which is Low (2.0 score), others 0.0. Average = 2.0 / 6 = 0.33
    assert data["overall_risk_category"] == "LOW"
    assert len(data["risks_detected"]) == 6

    # 404 Case (non-existent UUID)
    response_404 = await client.post(f"/api/v1/tenders/{uuid4()}/risk")
    assert response_404.status_code == 404

    # 400 Case (unparsed tender)
    unparsed_id = uuid4()
    unparsed_tender = Tender(
        id=unparsed_id,
        tender_number="TND-UNPARSED-API",
        department="Eng",
        source_url="http://unparsed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(unparsed_tender)
    await db_session.commit()

    response_400 = await client.post(f"/api/v1/tenders/{unparsed_id}/risk")
    assert response_400.status_code == 400
    assert "has not been parsed yet" in response_400.json()["detail"]
