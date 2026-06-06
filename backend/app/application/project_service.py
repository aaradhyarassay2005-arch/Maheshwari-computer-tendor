import structlog
from uuid import uuid4
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple

from app.domain.models import PastProject
from app.domain.repositories import (
    IPastProjectRepository,
    IProjectExtractor,
    IStorageProvider,
    IPDFExtractor,
    IEmbeddingProvider,
    IVectorSearchProvider,
)


logger = structlog.get_logger("app.projects")


class ProjectService:
    def __init__(
        self,
        project_repo: IPastProjectRepository,
        extractor: IProjectExtractor,
        storage: IStorageProvider,
        primary_extractor: IPDFExtractor,
        fallback_extractor: IPDFExtractor,
        embedding_provider: Optional[IEmbeddingProvider] = None,
        vector_search_provider: Optional[IVectorSearchProvider] = None,
    ):
        self.project_repo = project_repo
        self.extractor = extractor
        self.storage = storage
        self.primary_extractor = primary_extractor
        self.fallback_extractor = fallback_extractor
        self.embedding_provider = embedding_provider
        self.vector_search_provider = vector_search_provider


    async def extract_and_save_project(
        self, filename: str, content: bytes, doc_type: str
    ) -> PastProject:
        """Saves project document to local storage, extracts metadata, and stores record in database."""
        # Save file to disk
        saved_path = await self.storage.save(filename, content)
        logger.info("Saved project document", path=saved_path, filename=filename)

        raw_text = ""
        # 1. Primary Extractor (pdfplumber)
        try:
            logger.info("Attempting text extraction with primary extractor", path=saved_path)
            raw_text = await self.primary_extractor.extract_text(saved_path)
        except Exception as e:
            logger.warn("Primary text extraction failed, falling back", error=str(e), path=saved_path)

        # 2. Fallback Extractor (PyMuPDF)
        if not raw_text or not raw_text.strip():
            try:
                logger.info("Attempting text extraction with fallback extractor", path=saved_path)
                raw_text = await self.fallback_extractor.extract_text(saved_path)
            except Exception as e:
                logger.error("Fallback text extraction failed", error=str(e), path=saved_path)

        # 3. If extraction failed completely, use default empty text
        if not raw_text:
            raw_text = ""

        # 4. Extract structured details using rule-based provider
        extracted_details = await self.extractor.extract_project_details(raw_text, doc_type)

        # 5. Enforce numeric validations (negative values not allowed, reset to 0.00)
        project_value = extracted_details.get("project_value", Decimal("0.00"))
        if project_value < Decimal("0.0"):
            logger.warn(
                "Extracted negative project value, resetting to 0.00",
                value=str(project_value),
            )
            project_value = Decimal("0.00")

        # 6. Create Domain Entity
        now = datetime.now(timezone.utc)
        project = PastProject(
            id=uuid4(),
            project_name=extracted_details.get("project_name", "UNKNOWN"),
            client=extracted_details.get("client", "UNKNOWN"),
            project_value=project_value,
            completion_date=extracted_details.get("completion_date"),
            domain=extracted_details.get("domain", "Other"),
            location=extracted_details.get("location", "UNKNOWN"),
            document_type=doc_type,
            document_path=saved_path,
            created_at=now,
            updated_at=now,
        )

        # 7. Persist
        saved_project = await self.project_repo.add(project)
        logger.info(
            "Successfully extracted and saved past project credential",
            project_id=str(saved_project.id),
            project_name=saved_project.project_name,
        )

        # 8. Index in vector search if providers are registered
        if self.embedding_provider and self.vector_search_provider:
            try:
                await self.vector_search_provider.initialize()
                text = (
                    f"Project Name: {saved_project.project_name}. "
                    f"Client: {saved_project.client}. "
                    f"Domain: {saved_project.domain}. "
                    f"Location: {saved_project.location}."
                )
                logger.info("Generating embedding for automatic indexing", project_id=str(saved_project.id))
                embedding = await self.embedding_provider.embed_text(text, is_query=False)
                await self.vector_search_provider.upsert_project(saved_project, embedding)
                logger.info("Automatically indexed project in vector search", project_id=str(saved_project.id))
            except Exception as e:
                logger.error(
                    "Failed to automatically index project in vector search",
                    error=str(e),
                    project_id=str(saved_project.id),
                )

        return saved_project


    async def list_projects(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        domain: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[Decimal] = None,
    ) -> Tuple[List[PastProject], int]:
        """Queries past projects with pagination, full-text search, and metadata filters."""
        return await self.project_repo.list(
            skip=skip,
            limit=limit,
            search=search,
            domain=domain,
            location=location,
            min_value=min_value,
        )

    async def get_capabilities(self) -> List[dict]:
        """Generates capability aggregates grouped by domain."""
        return await self.project_repo.get_capabilities()
