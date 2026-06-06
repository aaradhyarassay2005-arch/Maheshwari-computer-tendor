from fastapi import APIRouter, Depends, status
import structlog
from pydantic import UUID4

from app.api.dependencies import get_risk_service
from app.application.risk_service import RiskService
from app.schemas.risk import RiskAnalysisResponse

logger = structlog.get_logger("app.api.risk")
router = APIRouter(prefix="/tenders", tags=["risk"])


@router.post(
    "/{id}/risk",
    response_model=RiskAnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Analyze tender compliance risks",
)
async def analyze_tender_risks(
    id: UUID4,
    service: RiskService = Depends(get_risk_service),
):
    """
    Executes compliance risk analysis on a tender by evaluating its metadata and raw text.
    Raises:
        HTTP 404: If the tender does not exist.
        HTTP 400: If the tender has not been parsed/extracted yet.
    """
    logger.info("Received risk analysis request", tender_id=str(id))
    result = await service.analyze_tender_risks(id)
    return result
