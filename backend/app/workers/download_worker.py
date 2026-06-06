import asyncio
import structlog

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
            # Open transactional session
            async with async_session_maker() as session:
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
                
                summary = await service.run_background_downloads(max_attempts=max_attempts)
                if summary["processed"] > 0:
                    logger.info("Download job summary executed", **summary)
                    await session.commit()
                else:
                    await session.rollback()
        except Exception as e:
            logger.error("Download worker loop encountered an error", error=str(e))
            
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
