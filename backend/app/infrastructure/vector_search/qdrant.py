import asyncio
import logging
from typing import List, Dict, Any
from pydantic import UUID4
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels

from app.core.config import settings
from app.domain.models import PastProject
from app.domain.repositories import IVectorSearchProvider

logger = logging.getLogger(__name__)


class QdrantVectorSearchProvider(IVectorSearchProvider):
    """Qdrant-backed vector search database provider."""

    def __init__(self, collection_name: str = "past_projects"):
        self.collection_name = collection_name
        self._client = None

    def _get_client(self) -> QdrantClient:
        if self._client is None:
            if settings.QDRANT_URL:
                logger.info(f"Connecting to Qdrant server at: {settings.QDRANT_URL}")
                self._client = QdrantClient(
                    url=settings.QDRANT_URL,
                    api_key=settings.QDRANT_API_KEY,
                )
            elif settings.QDRANT_PATH:
                logger.info(f"Initializing Qdrant local storage at: {settings.QDRANT_PATH}")
                self._client = QdrantClient(path=settings.QDRANT_PATH)
            else:
                logger.info("Initializing in-memory Qdrant client")
                self._client = QdrantClient(location=":memory:")
        return self._client

    def _sync_initialize(self) -> None:
        client = self._get_client()
        # Check if collection exists
        collections = client.get_collections().collections
        exists = any(c.name == self.collection_name for c in collections)

        if not exists:
            logger.info(f"Creating Qdrant collection: {self.collection_name}")
            client.create_collection(
                collection_name=self.collection_name,
                vectors_config=qmodels.VectorParams(
                    size=1024,  # BAAI/bge-large-en-v1.5 dimension size
                    distance=qmodels.Distance.COSINE,
                ),
            )
            logger.info("Collection created successfully")
        else:
            logger.info(f"Qdrant collection '{self.collection_name}' already exists")

    def _sync_upsert_project(self, project: PastProject, embedding: List[float]) -> None:
        client = self._get_client()
        # Prepare payload
        payload = {
            "project_id": str(project.id),
            "project_name": project.project_name,
            "client": project.client,
            "project_value": str(project.project_value),
            "completion_date": project.completion_date.isoformat() if project.completion_date else None,
            "domain": project.domain,
            "location": project.location,
            "document_type": project.document_type,
            "document_path": project.document_path,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        }


        # Upsert point
        # Point ID is mapped from UUID string directly as standard string UUID
        client.upsert(
            collection_name=self.collection_name,
            points=[
                qmodels.PointStruct(
                    id=str(project.id),
                    vector=embedding,
                    payload=payload,
                )
            ],
        )

    def _sync_search_similar_projects(self, embedding: List[float], limit: int) -> List[dict]:
        import time
        from app.core.observability import QDRANT_SEARCH_TIME
        
        start_time = time.time()
        client = self._get_client()
        results = client.search(
            collection_name=self.collection_name,
            query_vector=embedding,
            limit=limit,
        )
        duration = time.time() - start_time
        try:
            QDRANT_SEARCH_TIME.labels(collection=self.collection_name).observe(duration)
        except Exception:
            pass

        matches = []
        for res in results:
            matches.append({
                "payload": res.payload,
                "score": res.score,
            })
        return matches

    def _sync_delete_project(self, project_id: str) -> None:
        client = self._get_client()
        client.delete(
            collection_name=self.collection_name,
            points_selector=qmodels.PointIdsList(
                points=[project_id]
            ),
        )

    async def initialize(self) -> None:
        await asyncio.to_thread(self._sync_initialize)

    async def upsert_project(self, project: PastProject, embedding: List[float]) -> None:
        await asyncio.to_thread(self._sync_upsert_project, project, embedding)

    async def search_similar_projects(self, embedding: List[float], limit: int = 10) -> List[dict]:
        return await asyncio.to_thread(self._sync_search_similar_projects, embedding, limit)

    async def delete_project(self, project_id: UUID4) -> None:
        await asyncio.to_thread(self._sync_delete_project, str(project_id))
