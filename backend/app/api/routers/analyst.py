from fastapi import APIRouter, Depends, status
import structlog
from pydantic import UUID4

from app.api.dependencies import get_ai_tender_analyst_service
from app.application.analyst_service import AITenderAnalystService
from app.schemas.analyst import AnalystRequest, AnalystResponse

logger = structlog.get_logger("app.api.analyst")
router = APIRouter(prefix="/tenders", tags=["analyst"])


@router.post(
    "/{id}/analyst",
    response_model=AnalystResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI Tender Analyst report",
)
async def generate_analyst_report(
    id: UUID4,
    request: AnalystRequest,
    service: AITenderAnalystService = Depends(get_ai_tender_analyst_service),
):
    """
    Generates structured AI-powered narratives explaining the pre-calculated rule-based results of
    financial qualification, project matching, compliance risks, and final bid recommendation.
    """
    logger.info("Received AI analyst report request", tender_id=str(id))
    result = await service.generate_analyst_report(
        tender_id=id,
        annual_turnovers=request.annual_turnovers,
        net_worth=request.net_worth,
        eligibility_rules=request.eligibility_rules
    )
    return result
