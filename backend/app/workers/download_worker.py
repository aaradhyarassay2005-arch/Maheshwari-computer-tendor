import asyncio
import structlog

from app.domain.models import TenderDocumentStatus
from app.core.database import async_session_maker
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.storage.local import LocalStorageProvider
from app.infrastructure.downloader.httpx import HTTPXPDFDownloader
from app.application.downloader import TenderDownloaderService

logger = structlog.get_logger("app.worker")

# Worker execution control flag
_worker_running = True
_worker_task = None


def stop_worker():
    """Signals the worker loop to stop executing on next tick."""
    global _worker_running
    _worker_running = False
    logger.info("Download worker stop signal received")


async def run_downloader_worker_loop(interval_seconds: int = 15, max_attempts: int = 3):
    """Periodic background worker loop polling for new/failed downloads."""
    logger.info("Starting background download worker loop", interval=interval_seconds)
    global _worker_running
    while _worker_running:
        try:
            # 1. Fetch pending document IDs using a short-lived session
            async with async_session_maker() as session:
                doc_repo = SQLAlchemyTenderDocumentRepository(session)
                pending_docs = await doc_repo.get_pending_or_retryable(max_attempts)
                pending_ids = [doc.tender_id for doc in pending_docs]

            # 2. Process each download in its own isolated transaction
            if pending_ids:
                logger.info("Found pending downloads to process", count=len(pending_ids))
                processed = 0
                completed = 0
                failed = 0
                
                for tender_id in pending_ids:
                    if not _worker_running:
                        break
                        
                    processed += 1
                    async with async_session_maker() as session:
                        try:
                            tender_repo = SQLAlchemyTenderRepository(session)
                            doc_repo = SQLAlchemyTenderDocumentRepository(session)
                            downloader = HTTPXPDFDownloader()
                            storage = LocalStorageProvider()
                            
                            service = TenderDownloaderService(
                                tender_repo=tender_repo,
                                doc_repo=doc_repo,
                                downloader=downloader,
                                storage=storage
                            )
                            
                            res = await service.download_document(tender_id)
                            await session.commit()
                            if res and res.status == TenderDocumentStatus.DOWNLOADED:
                                completed += 1
                            else:
                                failed += 1
                        except Exception:
                            await session.rollback()
                            logger.exception("Failed to process background download", tender_id=str(tender_id))
                            failed += 1
                            
                    # Yield control to event loop and sleep briefly between downloads
                    await asyncio.sleep(0.2)
                    
                logger.info("Download job batch executed", processed=processed, completed=completed, failed=failed)
        except Exception:
            logger.exception("Download worker loop encountered an error")
            
        await asyncio.sleep(interval_seconds)


def start_worker(interval_seconds: int = 15, max_attempts: int = 3):
    """Starts the download worker loop in the background of the event loop."""
    global _worker_task, _worker_running
    _worker_running = True
    _worker_task = asyncio.create_task(
        run_downloader_worker_loop(interval_seconds, max_attempts)
    )
    logger.info("Download worker thread started in background")
    return _worker_task
