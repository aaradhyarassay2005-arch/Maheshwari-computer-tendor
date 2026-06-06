from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Tuple
from pydantic import UUID4
from app.domain.models import Tender, TenderDocument, TenderMetadata, TenderStatus, BOQItem, PastProject, AuditLog, TenderReview



class ITenderRepository(ABC):
    @abstractmethod
    async def add(self, tender: Tender) -> Tender:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID4) -> Optional[Tender]:
        pass

    @abstractmethod
    async def get_by_tender_number(self, tender_number: str) -> Optional[Tender]:
        pass

    @abstractmethod
    async def get_by_source_url(self, source_url: str) -> Optional[Tender]:
        pass

    @abstractmethod
    async def list(
        self, skip: int = 0, limit: int = 10, search: Optional[str] = None
    ) -> Tuple[List[Tender], int]:
        pass

    @abstractmethod
    async def update(self, tender: Tender) -> Tender:
        pass

    @abstractmethod
    async def delete(self, id: UUID4) -> bool:
        pass

    @abstractmethod
    async def bulk_add(self, tenders: List[Tender]) -> List[Tender]:
        pass

    @abstractmethod
    async def get_by_statuses(self, statuses: List[TenderStatus]) -> List[Tender]:
        pass


class ITenderDocumentRepository(ABC):
    @abstractmethod
    async def add(self, document: TenderDocument) -> TenderDocument:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID4) -> Optional[TenderDocument]:
        pass

    @abstractmethod
    async def get_by_tender_id(self, tender_id: UUID4) -> Optional[TenderDocument]:
        pass

    @abstractmethod
    async def get_by_hash(self, sha256: str) -> Optional[TenderDocument]:
        pass

    @abstractmethod
    async def update(self, document: TenderDocument) -> TenderDocument:
        pass

    @abstractmethod
    async def delete(self, id: UUID4) -> bool:
        pass

    @abstractmethod
    async def get_pending_or_retryable(self, max_attempts: int) -> List[TenderDocument]:
        pass

    @abstractmethod
    async def bulk_add(self, documents: List[TenderDocument]) -> List[TenderDocument]:
        pass


class ITenderMetadataRepository(ABC):
    @abstractmethod
    async def add(self, metadata: TenderMetadata) -> TenderMetadata:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID4) -> Optional[TenderMetadata]:
        pass

    @abstractmethod
    async def get_by_tender_id(self, tender_id: UUID4) -> Optional[TenderMetadata]:
        pass

    @abstractmethod
    async def update(self, metadata: TenderMetadata) -> TenderMetadata:
        pass

    @abstractmethod
    async def delete(self, id: UUID4) -> bool:
        pass


class IStorageProvider(ABC):
    @abstractmethod
    async def save(self, filename: str, content: bytes) -> str:
        """Saves content buffer to storage provider and returns file path/URI."""
        pass

    @abstractmethod
    async def delete(self, file_path: str) -> None:
        """Removes target file from storage provider."""
        pass


class IPDFDownloader(ABC):
    @abstractmethod
    async def download(self, url: str) -> bytes:
        """Downloads files over HTTP. Raises exception on failure."""
        pass


class IPDFExtractor(ABC):
    @abstractmethod
    async def extract_text(self, file_path: str) -> str:
        """Extracts text from a local PDF file path. Raises exception on error."""
        pass


class IMetadataExtractionProvider(ABC):
    @abstractmethod
    async def extract(self, raw_text: str) -> dict:
        """Parses raw text to extract metadata fields and confidence scores."""
        pass


class IBOQItemRepository(ABC):
    @abstractmethod
    async def add(self, item: BOQItem) -> BOQItem:
        pass

    @abstractmethod
    async def get_by_tender_id(self, tender_id: UUID4) -> List[BOQItem]:
        pass

    @abstractmethod
    async def bulk_add(self, items: List[BOQItem]) -> List[BOQItem]:
        pass

    @abstractmethod
    async def delete_by_tender_id(self, tender_id: UUID4) -> None:
        pass


class IBOQExtractionProvider(ABC):
    @abstractmethod
    async def extract_boq(self, file_path: str) -> List[dict]:
        """Extracts structured BOQ items from PDF file."""
        pass


class IPastProjectRepository(ABC):
    @abstractmethod
    async def add(self, project: PastProject) -> PastProject:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID4) -> Optional[PastProject]:
        pass

    @abstractmethod
    async def list(
        self,
        skip: int = 0,
        limit: int = 10,
        search: Optional[str] = None,
        domain: Optional[str] = None,
        location: Optional[str] = None,
        min_value: Optional[Decimal] = None,
    ) -> Tuple[List[PastProject], int]:
        pass

    @abstractmethod
    async def get_capabilities(self) -> List[dict]:
        pass


class IProjectExtractor(ABC):
    @abstractmethod
    async def extract_project_details(self, raw_text: str, doc_type: str) -> dict:
        """Parses raw text to extract project details based on document type."""
        pass


class IEmbeddingProvider(ABC):
    @abstractmethod
    async def embed_text(self, text: str) -> List[float]:
        pass

    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class IVectorSearchProvider(ABC):
    @abstractmethod
    async def initialize(self) -> None:
        """Create collections or setup indexes."""
        pass

    @abstractmethod
    async def upsert_project(self, project: PastProject, embedding: List[float]) -> None:
        pass

    @abstractmethod
    async def search_similar_projects(self, embedding: List[float], limit: int = 10) -> List[dict]:
        """Returns list of matching points containing payload metadata and vector scores."""
        pass

    @abstractmethod
    async def delete_project(self, project_id: UUID4) -> None:
        pass


class IAuditLogRepository(ABC):
    @abstractmethod
    async def add(self, audit_log: AuditLog) -> AuditLog:
        pass

    @abstractmethod
    async def list(self, skip: int = 0, limit: int = 100) -> Tuple[List[AuditLog], int]:
        pass


class ITenderReviewRepository(ABC):
    @abstractmethod
    async def add(self, review: TenderReview) -> TenderReview:
        pass

    @abstractmethod
    async def get_by_tender_id(self, tender_id: UUID4) -> List[TenderReview]:
        pass

    @abstractmethod
    async def get_by_id(self, id: UUID4) -> Optional[TenderReview]:
        pass






