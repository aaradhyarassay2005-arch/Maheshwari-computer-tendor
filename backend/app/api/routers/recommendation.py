import time
from fastapi import APIRouter, Depends, status, Request
import structlog
from pydantic import UUID4

from app.api.dependencies import get_tender_recommendation_service, get_audit_service
from app.application.recommendation_service import TenderRecommendationService
from app.application.audit_service import AuditLoggingService
from app.schemas.recommendation import RecommendationRequest, RecommendationResponse
from app.core.observability import RECOMMENDATION_LATENCY

logger = structlog.get_logger("app.api.recommendation")
router = APIRouter(prefix="/tenders", tags=["recommendation"])


@router.post(
    "/{id}/recommendation",
    response_model=RecommendationResponse,
    status_code=status.HTTP_200_OK,
    summary="Evaluate executive bid recommendation",
)
async def get_tender_recommendation(
    id: UUID4,
    request: RecommendationRequest,
    http_request: Request,
    service: TenderRecommendationService = Depends(get_tender_recommendation_service),
    audit_service: AuditLoggingService = Depends(get_audit_service),
):
    """
    Computes a comprehensive bid recommendation (GO / REVIEW / NO BID), win probability,
    key pros/cons reasons list, and required checklist documents for the specified tender ID.
    Raises:
        HTTP 404: If the tender does not exist.
        HTTP 400: If the tender has not been parsed/extracted yet.
    """
    logger.info("Received recommendation request", tender_id=str(id))
    
    start_time = time.time()
    result = await service.get_recommendation(
        tender_id=id,
        annual_turnovers=request.annual_turnovers,
        net_worth=request.net_worth,
        eligibility_rules=request.eligibility_rules
    )
    duration = time.time() - start_time

    # Record Latency Metric
    try:
        RECOMMENDATION_LATENCY.labels(verdict=result.recommendation.value).observe(duration)
    except Exception:
        pass

    # Log Audit Trail
    try:
        await audit_service.log_action(
            action="RUN_RECOMMENDATION",
            resource_type="tender",
            resource_id=str(id),
            ip_address=http_request.client.host if http_request.client else None,
            client_agent=http_request.headers.get("user-agent"),
            change_diff={
                "verdict": result.recommendation.value,
                "win_probability": result.win_probability,
            }
        )
    except Exception:
        pass

    return result
