from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import UUID4
import structlog

from app.api.dependencies import get_metadata_repository, get_metadata_extraction_service
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository
from app.application.extraction_service import TenderMetadataExtractionService
from app.schemas.metadata import TenderMetadataResponse, TriggerExtractionResponse

logger = structlog.get_logger("app.api.metadata")
router = APIRouter(prefix="/tenders", tags=["metadata"])


@router.get(
    "/{id}/metadata",
    response_model=TenderMetadataResponse,
    summary="Retrieve extracted Tender Metadata",
)
async def get_tender_metadata(
    id: UUID4,
    meta_repo: SQLAlchemyTenderMetadataRepository = Depends(get_metadata_repository),
):
    metadata = await meta_repo.get_by_tender_id(id)
    if not metadata:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Tender metadata not found for tender {id}",
        )
    return metadata


@router.post(
    "/{id}/extract",
    response_model=TriggerExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger metadata extraction",
)
async def trigger_metadata_extraction(
    id: UUID4,
    background_tasks: BackgroundTasks,
    extraction_service: TenderMetadataExtractionService = Depends(get_metadata_extraction_service),
):
    # Queue extraction task in the background
    background_tasks.add_task(extraction_service.extract_metadata, id)

    return TriggerExtractionResponse(
        tender_id=id,
        status="PROCESSING",
        message="Metadata extraction job initiated in the background."
    )
