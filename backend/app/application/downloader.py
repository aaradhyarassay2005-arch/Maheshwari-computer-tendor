import hashlib
import structlog
from datetime import datetime, timezone
from urllib.parse import urlparse
from pydantic import UUID4
from typing import Optional, Dict, Any, List

from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.domain.repositories import (
    ITenderRepository,
    ITenderDocumentRepository,
    IStorageProvider,
    IPDFDownloader,
)

logger = structlog.get_logger("app.downloader")


class TenderDownloaderService:
    def __init__(
        self,
        tender_repo: ITenderRepository,
        doc_repo: ITenderDocumentRepository,
        downloader: IPDFDownloader,
        storage: IStorageProvider,
    ):
        self.tender_repo = tender_repo
        self.doc_repo = doc_repo
        self.downloader = downloader
        self.storage = storage

    def _extract_filename(self, url: str, default_name: str) -> str:
        try:
            parsed = urlparse(url)
            path = parsed.path
            filename = path.split("/")[-1]
            if filename and filename.lower().endswith(".pdf"):
                return filename
        except Exception:
            pass
        return default_name

    async def download_document(self, tender_id: UUID4) -> Optional[TenderDocument]:
        doc = await self.doc_repo.get_by_tender_id(tender_id)
        if not doc:
            logger.error("TenderDocument record not found for download", tender_id=str(tender_id))
            return None

        # If already downloaded, skip
        if doc.status == TenderDocumentStatus.DOWNLOADED:
            logger.info("Document already downloaded, skipping", tender_id=str(tender_id))
            return doc

        tender = await self.tender_repo.get_by_id(tender_id)
        if not tender:
            logger.error("Tender entity not found for download", tender_id=str(tender_id))
            return None

        # Transition document and tender status to DOWNLOADING
        now = datetime.now(timezone.utc)
        doc.status = TenderDocumentStatus.DOWNLOADING
        doc.attempts += 1
        doc.updated_at = now
        await self.doc_repo.update(doc)

        tender.status = TenderStatus.DOWNLOADING
        tender.updated_at = now
        await self.tender_repo.update(tender)

        # Commit status transition to release database locks during network I/O
        if hasattr(self.doc_repo, "session") and hasattr(self.doc_repo.session, "commit"):
            await self.doc_repo.session.commit()

        try:
            logger.info(
                "Starting document download",
                tender_id=str(tender_id),
                url=tender.source_url,
                attempt=doc.attempts,
            )

            # Download content
            content = await self.downloader.download(tender.source_url)

            # Validate file content signature (magic bytes)
            if not content.startswith(b"%PDF"):
                raise ValueError("Downloaded file signature mismatch (missing %PDF header)")

            # Generate SHA256 hash
            sha256 = hashlib.sha256(content).hexdigest()

            # Prevent duplicate downloads: check DB for downloaded document with identical hash
            existing_doc = await self.doc_repo.get_by_hash(sha256)
            if existing_doc and existing_doc.status == TenderDocumentStatus.DOWNLOADED:
                raise ValueError(
                    f"Duplicate document hash detected. Document already exists linked to tender {existing_doc.tender_id}"
                )

            # Save file to storage provider
            filename = self._extract_filename(tender.source_url, f"{sha256}.pdf")
            file_path = await self.storage.save(filename, content)

            # Update TenderDocument fields on success
            doc.file_name = filename
            doc.file_path = file_path
            doc.sha256 = sha256
            doc.file_size = len(content)
            doc.mime_type = "application/pdf"
            doc.downloaded_at = now
            doc.status = TenderDocumentStatus.DOWNLOADED
            doc.error_message = None
            doc.updated_at = now
            saved_doc = await self.doc_repo.update(doc)

            # Update parent Tender status
            tender.status = TenderStatus.DOWNLOADED
            tender.updated_at = now
            await self.tender_repo.update(tender)

            logger.info(
                "Document download completed successfully",
                tender_id=str(tender_id),
                doc_id=str(doc.id),
                hash=sha256,
            )
            return saved_doc

        except Exception as e:
            error_msg = str(e)
            
            # Increment Prometheus Download Failures Metric
            try:
                from app.core.observability import DOWNLOAD_FAILURES
                parsed_url = urlparse(tender.source_url)
                host = parsed_url.netloc or "unknown"
                DOWNLOAD_FAILURES.labels(error_class=e.__class__.__name__, host_domain=host).inc()
            except Exception:
                pass

            logger.exception(
                "Document download failed",
                tender_id=str(tender_id),
                attempt=doc.attempts,
            )

            # Update TenderDocument fields on failure
            doc.status = TenderDocumentStatus.FAILED
            doc.error_message = error_msg[:1000]
            doc.updated_at = now
            await self.doc_repo.update(doc)

            # Update parent Tender status
            tender.status = TenderStatus.FAILED
            tender.updated_at = now
            await self.tender_repo.update(tender)

            return None

    async def run_background_downloads(self, max_attempts: int = 3) -> Dict[str, int]:
        """Scans database for pending or failed documents and downloads their files."""
        docs = await self.doc_repo.get_pending_or_retryable(max_attempts)
        summary = {"total_scanned": len(docs), "processed": 0, "completed": 0, "failed": 0}

        for doc in docs:
            summary["processed"] += 1
            res = await self.download_document(doc.tender_id)
            if res and res.status == TenderDocumentStatus.DOWNLOADED:
                summary["completed"] += 1
            else:
                summary["failed"] += 1

        return summary
