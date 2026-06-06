from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import UUID4
import structlog

from app.api.dependencies import get_boq_repository, get_boq_extraction_service
from app.infrastructure.repositories.boq import SQLAlchemyBOQItemRepository
from app.application.boq_service import TenderBOQExtractionService
from app.schemas.boq import BOQItemResponse, BOQItemsListResponse, TriggerBOQExtractionResponse

logger = structlog.get_logger("app.api.boq")
router = APIRouter(prefix="/tenders", tags=["boq"])


@router.get(
    "/{id}/boq",
    response_model=BOQItemsListResponse,
    summary="Retrieve extracted Tender BOQ items",
)
async def get_tender_boq(
    id: UUID4,
    boq_repo: SQLAlchemyBOQItemRepository = Depends(get_boq_repository),
):
    items = await boq_repo.get_by_tender_id(id)
    return BOQItemsListResponse(
        tender_id=id,
        total=len(items),
        items=items
    )


@router.post(
    "/{id}/boq/extract",
    response_model=TriggerBOQExtractionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Manually trigger BOQ extraction",
)
async def trigger_boq_extraction(
    id: UUID4,
    background_tasks: BackgroundTasks,
    boq_service: TenderBOQExtractionService = Depends(get_boq_extraction_service),
):
    background_tasks.add_task(boq_service.extract_boq, id)

    return TriggerBOQExtractionResponse(
        tender_id=id,
        status="PROCESSING",
        message="BOQ extraction job initiated in the background."
    )
