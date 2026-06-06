from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import UUID4
import structlog

from app.api.dependencies import get_boq_analytics_service
from app.application.boq_analytics_service import BOQAnalyticsService
from app.schemas.boq_analytics import BOQSummaryResponse, BOQCategoriesResponse

logger = structlog.get_logger("app.api.boq.analytics")
router = APIRouter(prefix="/tenders", tags=["boq-analytics"])


@router.get(
    "/{id}/boq/summary",
    response_model=BOQSummaryResponse,
    summary="Get aggregated summary statistics for BOQ items",
)
async def get_boq_summary(
    id: UUID4,
    analytics_service: BOQAnalyticsService = Depends(get_boq_analytics_service),
):
    return await analytics_service.get_summary(id)


@router.get(
    "/{id}/boq/categories",
    response_model=BOQCategoriesResponse,
    summary="Get categorization analysis and material distribution",
)
async def get_boq_categories(
    id: UUID4,
    analytics_service: BOQAnalyticsService = Depends(get_boq_analytics_service),
):
    analysis_results = await analytics_service.get_category_analysis(id)
    return BOQCategoriesResponse(
        tender_id=id,
        categories=analysis_results
    )
