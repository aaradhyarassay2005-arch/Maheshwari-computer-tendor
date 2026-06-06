import structlog
from typing import List, Dict, Any, Optional
from pydantic import UUID4

from app.domain.models import PastProject
from app.domain.repositories import (
    IPastProjectRepository,
    IEmbeddingProvider,
    IVectorSearchProvider,
)
from app.application.ranking_engine import MatchingRankingEngine

logger = structlog.get_logger("app.matching")


class ProjectMatchingService:
    """Coordinates semantic embedding generation, vector storage, and eligibility matching."""

    def __init__(
        self,
        project_repo: IPastProjectRepository,
        embedding_provider: IEmbeddingProvider,
        vector_search_provider: IVectorSearchProvider,
        ranking_engine: MatchingRankingEngine,
    ):
        self.project_repo = project_repo
        self.embedding_provider = embedding_provider
        self.vector_search_provider = vector_search_provider
        self.ranking_engine = ranking_engine

    def _build_project_text(self, project: PastProject) -> str:
        """Constructs a descriptive text string representing the project for semantic search."""
        return (
            f"Project Name: {project.project_name}. "
            f"Client: {project.client}. "
            f"Domain: {project.domain}. "
            f"Location: {project.location}."
        )

    async def index_project(self, project: PastProject) -> None:
        """Generates embedding for a single project and indexes it in Qdrant."""
        text = self._build_project_text(project)
        logger.info("Generating embedding for new past project", project_id=str(project.id))
        embedding = await self.embedding_provider.embed_text(text, is_query=False)
        await self.vector_search_provider.upsert_project(project, embedding)
        logger.info("Successfully indexed project embedding in vector search", project_id=str(project.id))

    async def backfill_embeddings(self) -> int:
        """Backfills vector embeddings for all existing projects in SQL database to Qdrant."""
        logger.info("Starting embedding backfill pipeline")
        
        # Ensure vector DB collection is initialized
        await self.vector_search_provider.initialize()

        limit = 50
        skip = 0
        total_backfilled = 0

        while True:
            projects, total = await self.project_repo.list(skip=skip, limit=limit)
            if not projects:
                break

            logger.info("Processing backfill batch", skip=skip, count=len(projects))
            
            texts = [self._build_project_text(p) for p in projects]
            embeddings = await self.embedding_provider.embed_batch(texts)

            for project, embedding in zip(projects, embeddings):
                await self.vector_search_provider.upsert_project(project, embedding)
                total_backfilled += 1

            skip += limit
            if skip >= total:
                break

        logger.info("Embedding backfill pipeline completed", total_backfilled=total_backfilled)
        return total_backfilled

    async def match_eligibility(
        self, eligibility_rule: str, limit: int = 5
    ) -> List[Dict[str, Any]]:
        """Matches eligibility criteria with past projects using semantic search and ranking engine."""
        logger.info("Evaluating eligibility rule matching", rule=eligibility_rule, limit=limit)

        # 1. Parse constraints from rule
        constraints = self.ranking_engine.extract_constraints(eligibility_rule)

        # 2. Embed the eligibility rule
        query_embedding = await self.embedding_provider.embed_text(
            eligibility_rule, is_query=True
        )

        # 3. Retrieve semantically similar projects
        raw_matches = await self.vector_search_provider.search_similar_projects(
            query_embedding, limit=limit
        )

        # 4. Evaluate and rank each project against constraints
        results = []
        for match in raw_matches:
            payload = match["payload"]
            similarity_score = match["score"]

            evaluated = self.ranking_engine.evaluate_project(
                payload, similarity_score, constraints
            )
            results.append(evaluated)

        # Sort: first by eligibility (eligible projects first), then by similarity score descending
        results.sort(key=lambda x: (1 if x["eligible"] else 0, x["score"]), reverse=True)

        logger.info("Matching evaluation completed", matches_count=len(results))
        return results
