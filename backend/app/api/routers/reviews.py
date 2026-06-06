from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4
from typing import List
import structlog

from app.api.dependencies import get_tender_review_service
from app.application.review_service import TenderReviewService
from app.schemas.reviews import ReviewSubmitRequest, ReviewResponse
from app.schemas.tenders import TenderResponse

logger = structlog.get_logger("app.api.reviews")
router = APIRouter(prefix="/reviews", tags=["human-reviews"])


@router.get(
    "/queue",
    response_model=List[TenderResponse],
    summary="Get tenders pending human review (PARSED status)"
)
async def get_review_queue(
    service: TenderReviewService = Depends(get_tender_review_service)
):
    try:
        tenders = await service.get_review_queue()
        return tenders
    except Exception as e:
        logger.exception("Failed to fetch review queue", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch review queue: {str(e)}"
        )


@router.post(
    "/{tender_id}/submit",
    response_model=ReviewResponse,
    summary="Submit human review decision and metadata corrections"
)
async def submit_review(
    tender_id: UUID4,
    request: ReviewSubmitRequest,
    service: TenderReviewService = Depends(get_tender_review_service)
):
    try:
        review_res = await service.submit_review(tender_id=tender_id, request=request)
        return review_res
    except ValueError as e:
        logger.warning("Invalid review submission", tender_id=str(tender_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Failed to submit review", tender_id=str(tender_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit review: {str(e)}"
        )


@router.get(
    "/{tender_id}/history",
    response_model=List[ReviewResponse],
    summary="Get review submission history for a specific tender"
)
async def get_review_history(
    tender_id: UUID4,
    service: TenderReviewService = Depends(get_tender_review_service)
):
    try:
        history = await service.get_review_history(tender_id=tender_id)
        return history
    except Exception as e:
        logger.exception("Failed to fetch review history", tender_id=str(tender_id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch review history: {str(e)}"
        )
