from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import UUID4
import structlog

from app.api.dependencies import get_document_repository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.application.downloader import TenderDownloaderService
from app.schemas.documents import TenderDocumentResponse, TriggerDownloadResponse
from app.domain.models import TenderDocumentStatus

logger = structlog.get_logger("app.api.documents")
router = APIRouter(prefix="/tenders", tags=["documents"])


@router.get(
    "/{id}/document",
    response_model=TenderDocumentResponse,
    summary="Retrieve Tender Document status/metadata",
)
async def get_tender_document(
    id: UUID4,
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
):
    doc = await doc_repo.get_by_tender_id(id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender document not found for tender {id}",
        )
    return doc


async def run_standalone_download(tender_id: UUID4):
    """Executes a document download task in an isolated, thread-safe session block."""
    from app.core.database import async_session_maker
    from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
    from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
    from app.infrastructure.storage.local import LocalStorageProvider
    from app.infrastructure.downloader.httpx import HTTPXPDFDownloader
    from app.application.downloader import TenderDownloaderService
    
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
            await service.download_document(tender_id)
            await session.commit()
        except Exception:
            await session.rollback()
            logger.exception("Background task download failed", tender_id=str(tender_id))


@router.post(
    "/{id}/download",
    response_model=TriggerDownloadResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger document download",
)
async def trigger_document_download(
    id: UUID4,
    background_tasks: BackgroundTasks,
    doc_repo: SQLAlchemyTenderDocumentRepository = Depends(get_document_repository),
):
    doc = await doc_repo.get_by_tender_id(id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender document record not found for tender {id}",
        )

    # Reset status and attempts for clean retry/trigger
    doc.status = TenderDocumentStatus.PENDING
    doc.attempts = 0
    doc.error_message = None
    await doc_repo.update(doc)

    # Queue download task in the background using standalone session manager
    background_tasks.add_task(run_standalone_download, id)

    # Return immediate PENDING state
    return TriggerDownloadResponse(
        tender_id=id,
        status=TenderDocumentStatus.PENDING,
        message="Download initiated in the background."
    )
