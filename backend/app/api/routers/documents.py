from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import UUID4
import structlog

from app.api.dependencies import get_document_repository, get_downloader_service
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
    downloader_service: TenderDownloaderService = Depends(get_downloader_service),
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

    # Queue download task in the background
    background_tasks.add_task(downloader_service.download_document, id)

    # Return immediate PENDING state
    return TriggerDownloadResponse(
        tender_id=id,
        status=TenderDocumentStatus.PENDING,
        message="Download initiated in the background."
    )
