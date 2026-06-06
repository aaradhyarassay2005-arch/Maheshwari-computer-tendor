import pytest
from decimal import Decimal
from datetime import date, datetime, timezone, timedelta
from uuid import uuid4
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Tender, TenderMetadata, TenderStatus, PastProject
from app.domain.exceptions import TenderNotFoundException, TenderNotParsedException
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository
from app.infrastructure.repositories.projects import SQLAlchemyPastProjectRepository
from app.infrastructure.repositories.boq import SQLAlchemyBOQItemRepository
from app.application.boq_analytics_engine import BOQAnalyticsEngine
from app.application.boq_analytics_service import BOQAnalyticsService
from app.application.qualification_engine import FinancialRuleEngine
from app.application.qualification_service import FinancialValidationService
from app.application.matching_service import ProjectMatchingService
from app.application.ranking_engine import MatchingRankingEngine
from app.application.risk_engine import RiskEngine
from app.application.risk_service import RiskService
from app.application.recommendation_rules import RecommendationRulesEngine
from app.application.recommendation_service import TenderRecommendationService
from app.schemas.recommendation import BidRecommendation
from app.schemas.risk import RiskCategory, RiskSeverity
from app.api.dependencies import get_embedding_provider, get_vector_search_provider
from app.main import app


# Mock dependencies for fast, model-free tests
class DummyEmbeddingProvider:
    async def embed_text(self, text: str, is_query: bool = False):
        return [0.1] * 1024

    async def embed_batch(self, texts):
        return [[0.1] * 1024 for _ in texts]


class DummyVectorSearchProvider:
    def __init__(self):
        self.points = []

    async def initialize(self):
        pass

    async def upsert_project(self, project, embedding):
        self.points.append({
            "id": str(project.id),
            "payload": {
                "project_id": str(project.id),
                "project_name": project.project_name,
                "client": project.client,
                "project_value": str(project.project_value),
                "completion_date": project.completion_date.isoformat() if project.completion_date else None,
                "domain": project.domain,
                "location": project.location,
                "document_type": project.document_type,
            },
            "score": 0.88  # Default similarity score > 0.85
        })

    async def search_similar_projects(self, embedding, limit=5):
        return [
            {
                "payload": pt["payload"],
                "score": pt["score"]
            }
            for pt in self.points[:limit]
        ]


# ==========================================
# 1. DECISION RULES ENGINE UNIT TESTS
# ==========================================

def test_rules_engine_decision_rules():
    engine = RecommendationRulesEngine()
    
    metadata = None
    boq = {"total_items": 0, "total_estimated_value": 0.0}
    financials_passed = {"qualified": True, "results": []}
    financials_failed = {"qualified": False, "summary_reasoning": "Failed turnover threshold", "results": []}
    matching_satisfied = [] 
    risk_low = {"overall_risk_score": 1.5, "overall_risk_category": RiskCategory.LOW, "risks_detected": []}

    # Rule 1: If financial qualification fails -> NO_BID
    res1 = engine.evaluate_recommendation(uuid4(), metadata, boq, financials_failed, matching_satisfied, risk_low)
    assert res1["recommendation"] == BidRecommendation.NO_BID
    assert res1["win_probability"] == 0.0
    assert "qualification criteria" in res1["decision_explanation"]

    # Rule 2: If risk score > 80 (i.e. risk_score > 8.0) -> REVIEW
    risk_high = {"overall_risk_score": 8.5, "overall_risk_category": RiskCategory.HIGH, "risks_detected": []}
    res2 = engine.evaluate_recommendation(uuid4(), metadata, boq, financials_passed, matching_satisfied, risk_high)
    assert res2["recommendation"] == BidRecommendation.REVIEW
    assert "exceeds the acceptable threshold of 8.0" in res2["decision_explanation"]

    # Rule 3: If matching score > 85 (i.e. > 0.85) and qualification passes -> GO
    matching_strong = [{
        "rule": "Execute OFC work",
        "matches": [{
            "eligible": True,
            "score": 0.90,  # 90% match
            "project": {"project_name": "Past OFC Works"}
        }]
    }]
    res3 = engine.evaluate_recommendation(uuid4(), metadata, boq, financials_passed, matching_strong, risk_low)
    assert res3["recommendation"] == BidRecommendation.GO
    assert "strong technical match" in res3["decision_explanation"]
    assert res3["best_matching_project"]["project_name"] == "Past OFC Works"

    # Rule 4 Fallback: If matching score between 40% and 85% -> REVIEW
    matching_marginal = [{
        "rule": "Execute OFC work",
        "matches": [{
            "eligible": True,
            "score": 0.70,  # 70% match
            "project": {"project_name": "Past OFC Works"}
        }]
    }]
    res4 = engine.evaluate_recommendation(uuid4(), metadata, boq, financials_passed, matching_marginal, risk_low)
    assert res4["recommendation"] == BidRecommendation.REVIEW
    assert "marginal" in res4["decision_explanation"]


# ==========================================
# 2. SERVICE ORCHESTRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_recommendation_service_success(db_session: AsyncSession):
    # Initialize repositories
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)
    project_repo = SQLAlchemyPastProjectRepository(db_session)
    boq_repo = SQLAlchemyBOQItemRepository(db_session)

    # Initialize Dummy Vectors and Embeddings
    dummy_vector = DummyVectorSearchProvider()
    dummy_embed = DummyEmbeddingProvider()

    # Register dependencies overrides inside app so service uses them
    app.dependency_overrides[get_embedding_provider] = lambda: dummy_embed
    app.dependency_overrides[get_vector_search_provider] = lambda: dummy_vector

    # Insert Tender
    tender_id = uuid4()
    tender = Tender(
        id=tender_id,
        tender_number="TND-REC-SERVICE-NEW",
        department="Railways",
        source_url="http://x",
        tender_value=Decimal("500000.00"),
        closing_date=date.today(),
        status=TenderStatus.PARSED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Insert Metadata
    meta = TenderMetadata(
        id=uuid4(),
        tender_id=tender_id,
        tender_value=Decimal("500000.00"),
        emd=Decimal("10000.00"),
        completion_period="90 days",
        raw_text="Earnest Money Deposit (EMD) is Rs 10000. OEM MAF required.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await metadata_repo.add(meta)

    # Add past project to SQL & vector search
    project = PastProject(
        id=uuid4(),
        project_name="Past OFC Works Mumbai",
        client="Metro Rail",
        project_value=Decimal("4000000.00"),
        completion_date=date.today() - timedelta(days=100),
        domain="OFC",
        location="Mumbai",
        document_type="LOA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await project_repo.add(project)
    await dummy_vector.upsert_project(project, await dummy_embed.embed_text("Mumbai project"))
    await db_session.commit()

    # Instantiate TenderRecommendationService directly
    boq_analytics_service = BOQAnalyticsService(tender_repo, boq_repo, BOQAnalyticsEngine())
    matching_service = ProjectMatchingService(project_repo, dummy_embed, dummy_vector, MatchingRankingEngine())
    qualification_service = FinancialValidationService(project_repo, FinancialRuleEngine())
    risk_service = RiskService(tender_repo, metadata_repo, RiskEngine())
    rules_engine = RecommendationRulesEngine()

    service = TenderRecommendationService(
        tender_repo=tender_repo,
        metadata_repo=metadata_repo,
        boq_analytics_service=boq_analytics_service,
        matching_service=matching_service,
        qualification_service=qualification_service,
        risk_service=risk_service,
        rules_engine=rules_engine,
    )

    # Execute service
    result = await service.get_recommendation(
        tender_id=tender_id,
        annual_turnovers=[Decimal("1500000.00"), Decimal("2000000.00")],
        net_worth=Decimal("200000.00"),
        eligibility_rules=["Execute OFC work of value at least 30 Lakhs in last 3 years"]
    )

    # Assert outputs
    assert result["recommendation"] == BidRecommendation.GO
 
    assert result["confidence_score"] > 0.0
    assert result["win_probability"] > 0.0
    assert result["best_matching_project"]["project_name"] == "Past OFC Works Mumbai"
    assert any("Turnover Certificate" in doc for doc in result["required_documents"])
    assert any("Manufacturer's Authorization Form" in doc for doc in result["required_documents"])

    
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_recommendation_service_exceptions(db_session: AsyncSession):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)
    project_repo = SQLAlchemyPastProjectRepository(db_session)
    boq_repo = SQLAlchemyBOQItemRepository(db_session)

    dummy_vector = DummyVectorSearchProvider()
    dummy_embed = DummyEmbeddingProvider()

    boq_analytics_service = BOQAnalyticsService(tender_repo, boq_repo, BOQAnalyticsEngine())
    matching_service = ProjectMatchingService(project_repo, dummy_embed, dummy_vector, MatchingRankingEngine())
    qualification_service = FinancialValidationService(project_repo, FinancialRuleEngine())
    risk_service = RiskService(tender_repo, metadata_repo, RiskEngine())
    rules_engine = RecommendationRulesEngine()

    service = TenderRecommendationService(
        tender_repo=tender_repo,
        metadata_repo=metadata_repo,
        boq_analytics_service=boq_analytics_service,
        matching_service=matching_service,
        qualification_service=qualification_service,
        risk_service=risk_service,
        rules_engine=rules_engine,
    )

    # 1. Tender Not Found
    with pytest.raises(TenderNotFoundException):
        await service.get_recommendation(uuid4(), [], Decimal("0"), [])

    # 2. Tender Not Parsed
    tender_id = uuid4()
    t = Tender(
        id=tender_id,
        tender_number="TND-UNPARSED-REC-EX-NEW",
        department="Admin",
        source_url="http://unparsed",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(t)
    await db_session.commit()

    with pytest.raises(TenderNotParsedException):
        await service.get_recommendation(tender_id, [], Decimal("0"), [])


# ==========================================
# 3. API ROUTER INTEGRATION TESTS
# ==========================================

@pytest.mark.asyncio
async def test_recommendation_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    metadata_repo = SQLAlchemyTenderMetadataRepository(db_session)

    # Insert Tender
    tender_id = uuid4()
    tender = Tender(
        id=tender_id,
        tender_number="TND-API-REC-END-NEW",
        department="Engineering",
        source_url="http://x",
        tender_value=Decimal("100000.00"),
        closing_date=date.today(),
        status=TenderStatus.PARSED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Insert Metadata
    metadata = TenderMetadata(
        id=uuid4(),
        tender_id=tender_id,
        tender_number="TND-API-REC-END-NEW",
        tender_value=Decimal("100000.00"),
        emd=Decimal("1000.00"),
        completion_period="12 Months",
        raw_text="Normal tender details.",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await metadata_repo.add(metadata)
    await db_session.commit()

    payload = {
        "annual_turnovers": ["500000.00", "600000.00"],
        "net_worth": "100000.00",
        "eligibility_rules": []
    }

    # Success Case
    response = await client.post(f"/api/v1/tenders/{tender_id}/recommendation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["recommendation"] in ["GO", "REVIEW", "NO_BID"]
    assert "confidence_score" in data
    assert "win_probability" in data
    assert "risk_level" in data
    assert "risk_summary" in data
    assert "required_documents" in data
    assert "key_reasons" in data
    assert "decision_explanation" in data

    # 404 Case
    response_404 = await client.post(f"/api/v1/tenders/{uuid4()}/recommendation", json=payload)
    assert response_404.status_code == 404

    # 400 Case (unparsed)
    unparsed_id = uuid4()
    unparsed_tender = Tender(
        id=unparsed_id,
        tender_number="TND-UNPARSED-API-REC-EX-NEW",
        department="Eng",
        source_url="http://unparsed",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(unparsed_tender)
    await db_session.commit()

    response_400 = await client.post(f"/api/v1/tenders/{unparsed_id}/recommendation", json=payload)
    assert response_400.status_code == 400
