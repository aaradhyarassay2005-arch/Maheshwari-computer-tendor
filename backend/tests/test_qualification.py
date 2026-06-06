import pytest
from decimal import Decimal
from datetime import date
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from app.domain.models import PastProject
from app.infrastructure.repositories.projects import SQLAlchemyPastProjectRepository
from app.application.qualification_engine import FinancialRuleEngine
from app.application.qualification_service import FinancialValidationService


def test_financial_rule_engine_percentage_rules():
    engine = FinancialRuleEngine()
    tender_value = Decimal("1000000.00")  # 10 Lakhs

    # Mock projects
    p1 = PastProject(
        id=uuid4(),
        project_name="P1",
        client="Client A",
        project_value=Decimal("400000.00"),  # 4 Lakhs (40%)
        completion_date=date.today(),
        domain="OFC",
        location="Delhi",
        document_type="LOA",
        created_at=date.today(),
        updated_at=date.today(),
    )
    p2 = PastProject(
        id=uuid4(),
        project_name="P2",
        client="Client B",
        project_value=Decimal("250000.00"),  # 2.5 Lakhs (25%)
        completion_date=date.today(),
        domain="OFC",
        location="Delhi",
        document_type="LOA",
        created_at=date.today(),
        updated_at=date.today(),
    )

    projects = [p1, p2]

    # Evaluate 35% rule (requires >= 3.5 Lakhs)
    res_35 = engine.evaluate_percentage_work_rule(tender_value, projects, Decimal("35"))
    assert res_35["passed"] is True
    assert res_35["actual_value"] == Decimal("400000.00")

    # Evaluate 50% rule (requires >= 5 Lakhs)
    res_50 = engine.evaluate_percentage_work_rule(tender_value, projects, Decimal("50"))
    assert res_50["passed"] is False
    assert res_50["actual_value"] == Decimal("400000.00")


def test_financial_rule_engine_turnover_rule():
    engine = FinancialRuleEngine()
    tender_value = Decimal("1000000.00")

    # turnovers average = 15 Lakhs (150%)
    turnovers_pass = [Decimal("1200000.00"), Decimal("1500000.00"), Decimal("1800000.00")]
    res_pass = engine.evaluate_turnover_rule(tender_value, turnovers_pass)
    assert res_pass["passed"] is True
    assert res_pass["actual_value"] == Decimal("1500000.00")

    # turnovers average = 8 Lakhs (80%)
    turnovers_fail = [Decimal("600000.00"), Decimal("800000.00"), Decimal("1000000.00")]
    res_fail = engine.evaluate_turnover_rule(tender_value, turnovers_fail)
    assert res_fail["passed"] is False
    assert res_fail["actual_value"] == Decimal("800000.00")


def test_financial_rule_engine_net_worth_rule():
    engine = FinancialRuleEngine()
    tender_value = Decimal("1000000.00")

    # Positive net worth (pass)
    res_pos = engine.evaluate_net_worth_rule(tender_value, Decimal("50000.00"))
    assert res_pos["passed"] is True

    # Negative net worth (fail)
    res_neg = engine.evaluate_net_worth_rule(tender_value, Decimal("-5000.00"))
    assert res_neg["passed"] is False

    # Percent threshold net worth (e.g. 10% of 10 Lakhs = 1 Lakh required)
    res_pct_pass = engine.evaluate_net_worth_rule(tender_value, Decimal("150000.00"), Decimal("10"))
    assert res_pct_pass["passed"] is True

    res_pct_fail = engine.evaluate_net_worth_rule(tender_value, Decimal("50000.00"), Decimal("10"))
    assert res_pct_fail["passed"] is False


@pytest.mark.asyncio
async def test_qualification_validation_service(db_session: AsyncSession):
    repo = SQLAlchemyPastProjectRepository(db_session)
    engine = FinancialRuleEngine()
    service = FinancialValidationService(repo, engine)

    # Add project to database
    from datetime import datetime, timezone
    p = PastProject(
        id=uuid4(),
        project_name="Similar OFC project",
        client="Northern Railway",
        project_value=Decimal("2000000.00"),  # 20 Lakhs
        completion_date=date.today(),
        domain="OFC",
        location="Delhi",
        document_type="COMPLETION_CERTIFICATE",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repo.add(p)

    # Evaluate for 50 Lakhs tender (35% is 17.5 Lakhs)
    tender_value = Decimal("5000000.00")
    turnovers = [Decimal("8000000.00"), Decimal("7500000.00"), Decimal("8500000.00")]  # average 80 Lakhs (exceeds 150% = 75 Lakhs)
    net_worth = Decimal("1000000.00")

    result = await service.evaluate_qualification(
        tender_value=tender_value,
        domain="OFC",
        annual_turnovers=turnovers,
        net_worth=net_worth,
        rules=["35_RULE", "TURNOVER_RULE", "NET_WORTH_RULE"]
    )

    assert result["qualified"] is True
    assert len(result["results"]) == 3
    assert result["results"][0]["passed"] is True
    assert result["results"][1]["passed"] is True
    assert result["results"][2]["passed"] is True


@pytest.mark.asyncio
async def test_qualification_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    repo = SQLAlchemyPastProjectRepository(db_session)
    
    # Add similar project
    from datetime import datetime, timezone
    p = PastProject(
        id=uuid4(),
        project_name="High Value Networking project",
        client="Metro Rail",
        project_value=Decimal("5000000.00"),  # 50 Lakhs
        completion_date=date.today(),
        domain="Networking",
        location="Delhi",
        document_type="LOA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repo.add(p)

    payload = {
        "tender_value": "10000000.00",  # 1 Crore (35% is 35 Lakhs, 60% is 60 Lakhs)
        "domain": "Networking",
        "annual_turnovers": ["15000000.00", "20000000.00", "16000000.00"],  # average 1.7 Crore (exceeds 150% = 1.5 Crore)
        "net_worth": "500000.00",
        "rules": ["35_RULE", "60_RULE", "TURNOVER_RULE", "NET_WORTH_RULE"]
    }

    response = await client.post("/api/v1/qualification/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Qualified should be False because 60% rule fails (50 Lakhs project < 60 Lakhs required)
    assert data["qualified"] is False
    assert len(data["results"]) == 4
    
    rule_35 = next(r for r in data["results"] if r["rule_name"] == "35_RULE")
    assert rule_35["passed"] is True
    
    rule_60 = next(r for r in data["results"] if r["rule_name"] == "60_RULE")
    assert rule_60["passed"] is False
