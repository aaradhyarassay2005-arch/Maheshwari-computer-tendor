import pytest
from decimal import Decimal
from datetime import date, timedelta
from typing import List
from httpx import AsyncClient
from pydantic import UUID4

from app.application.ranking_engine import MatchingRankingEngine
from app.application.matching_service import ProjectMatchingService
from app.domain.models import PastProject
from app.domain.repositories import IEmbeddingProvider, IVectorSearchProvider
from app.infrastructure.repositories.projects import SQLAlchemyPastProjectRepository
from app.api.dependencies import get_embedding_provider, get_vector_search_provider
from app.main import app


class DummyEmbeddingProvider(IEmbeddingProvider):
    async def embed_text(self, text: str, is_query: bool = False) -> List[float]:
        # Return a dummy 1024-dimension vector
        return [0.1] * 1024

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 1024 for _ in texts]


class DummyVectorSearchProvider(IVectorSearchProvider):
    def __init__(self):
        self.initialized = False
        self.points = []

    async def initialize(self) -> None:
        self.initialized = True

    async def upsert_project(self, project: PastProject, embedding: List[float]) -> None:
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
            "vector": embedding,
        })

    async def search_similar_projects(self, embedding: List[float], limit: int = 10) -> List[dict]:
        # Return all points as matching with a dummy score
        return [
            {
                "payload": pt["payload"],
                "score": 0.85,
            }
            for pt in self.points[:limit]
        ]

    async def delete_project(self, project_id: UUID4) -> None:
        self.points = [p for p in self.points if p["id"] != str(project_id)]


def test_ranking_engine_constraint_extraction():
    engine = MatchingRankingEngine()

    # Test Lakhs
    c1 = engine.extract_constraints("Must have executed similar work of value Rs. 50 Lakhs in past years")
    assert c1["min_value"] == Decimal("5000000")

    # Test Crores
    c2 = engine.extract_constraints("Rule: value of work not less than 1.5 Crore")
    assert c2["min_value"] == Decimal("15000000")

    # Test Raw currency
    c3 = engine.extract_constraints("Worth at least INR 25,00,000")
    assert c3["min_value"] == Decimal("2500000")

    # Test years / age cutoff
    c4 = engine.extract_constraints("Completed in the last 5 years")
    assert c4["cutoff_date"] is not None
    # Verify cutoff date is approx 5 years ago
    expected_cutoff = date.today() - timedelta(days=5 * 365)
    assert abs((c4["cutoff_date"] - expected_cutoff).days) < 2


def test_ranking_engine_project_evaluation():
    engine = MatchingRankingEngine()

    # Rule with value 20 Lakhs, completed last 3 years
    constraints = {
        "min_value": Decimal("2000000"),
        "cutoff_date": date.today() - timedelta(days=3 * 365),
    }

    # Project 1: Satisfies all
    p1 = {
        "project_id": "p1",
        "project_name": "OFC deployment",
        "project_value": "2500000.00",
        "completion_date": (date.today() - timedelta(days=365)).isoformat(),
        "domain": "OFC",
    }
    res1 = engine.evaluate_project(p1, 0.9, constraints)
    assert res1["eligible"] is True
    assert len(res1["reasons"]) == 0

    # Project 2: Value below threshold
    p2 = {
        "project_id": "p2",
        "project_name": "Small OFC",
        "project_value": "1500000.00",
        "completion_date": (date.today() - timedelta(days=365)).isoformat(),
        "domain": "OFC",
    }
    res2 = engine.evaluate_project(p2, 0.85, constraints)
    assert res2["eligible"] is False
    assert any("value of 1,500,000.00 is below" in r for r in res2["reasons"])

    # Project 3: Completion date older than limit
    p3 = {
        "project_id": "p3",
        "project_name": "Old OFC",
        "project_value": "3000000.00",
        "completion_date": (date.today() - timedelta(days=4 * 365)).isoformat(),
        "domain": "OFC",
    }
    res3 = engine.evaluate_project(p3, 0.88, constraints)
    assert res3["eligible"] is False
    assert any("older than the required limit" in r for r in res3["reasons"])


@pytest.mark.asyncio
async def test_project_matching_service_backfill_and_match(db_session):
    repo = SQLAlchemyPastProjectRepository(db_session)
    embedding = DummyEmbeddingProvider()
    vector_search = DummyVectorSearchProvider()
    ranking = MatchingRankingEngine()

    # Insert dummy project to DB
    from uuid import uuid4
    from datetime import datetime, timezone
    p = PastProject(
        id=uuid4(),
        project_name="Cisco Router installation",
        client="Central Railway",
        project_value=Decimal("3000000.00"),
        completion_date=date.today() - timedelta(days=100),
        domain="Networking",
        location="Mumbai",
        document_type="LOA",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repo.add(p)

    service = ProjectMatchingService(repo, embedding, vector_search, ranking)

    # Test backfill
    count = await service.backfill_embeddings()
    assert count == 1
    assert len(vector_search.points) == 1
    assert vector_search.points[0]["payload"]["project_name"] == "Cisco Router installation"

    # Test match
    rule = "Executed Networking work of value 20 Lakhs in last 5 years"
    matches = await service.match_eligibility(rule, limit=5)
    assert len(matches) == 1
    assert matches[0]["project"]["project_name"] == "Cisco Router installation"
    assert matches[0]["eligible"] is True


@pytest.mark.asyncio
async def test_matching_api_endpoints(client: AsyncClient, db_session):
    repo = SQLAlchemyPastProjectRepository(db_session)
    dummy_vector = DummyVectorSearchProvider()
    dummy_embed = DummyEmbeddingProvider()

    # Pre-populate project
    from uuid import uuid4
    from datetime import datetime, timezone
    p = PastProject(
        id=uuid4(),
        project_name="Optical fiber cable laying",
        client="Western Railway",
        project_value=Decimal("5000000.00"),
        completion_date=date.today() - timedelta(days=50),
        domain="OFC",
        location="Ahmedabad",
        document_type="WORK_ORDER",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await repo.add(p)

    # Index project in dummy vector DB
    await dummy_vector.upsert_project(p, await dummy_embed.embed_text("text"))

    # Register overrides
    app.dependency_overrides[get_embedding_provider] = lambda: dummy_embed
    app.dependency_overrides[get_vector_search_provider] = lambda: dummy_vector

    try:
        # 1. Test Match API
        payload = {
            "eligibility_rule": "The bidder must have executed OFC projects of value at least 30 Lakhs in the last 3 years",
            "limit": 5
        }
        res_match = await client.post("/api/v1/projects/match", json=payload)
        assert res_match.status_code == 200
        data = res_match.json()
        assert data["rule"] == payload["eligibility_rule"]
        assert len(data["matches"]) == 1
        assert data["matches"][0]["project"]["project_name"] == "Optical fiber cable laying"
        assert data["matches"][0]["eligible"] is True

        # Test Match API with failing threshold
        payload_fail = {
            "eligibility_rule": "Value of work at least 80 Lakhs",
            "limit": 5
        }
        res_fail = await client.post("/api/v1/projects/match", json=payload_fail)
        assert res_fail.status_code == 200
        data_fail = res_fail.json()
        assert data_fail["matches"][0]["eligible"] is False
        assert len(data_fail["matches"][0]["reasons"]) > 0

        # 2. Test Backfill API
        res_backfill = await client.post("/api/v1/projects/embeddings/backfill")
        assert res_backfill.status_code == 200
        backfill_data = res_backfill.json()
        assert backfill_data["backfilled_count"] == 1

    finally:
        app.dependency_overrides.clear()
