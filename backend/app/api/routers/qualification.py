from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.dependencies import get_financial_validation_service
from app.application.qualification_service import FinancialValidationService
from app.schemas.qualification import QualificationRequest, QualificationResponse

logger = structlog.get_logger("app.api.qualification")
router = APIRouter(prefix="/qualification", tags=["qualification"])


@router.post(
    "/evaluate",
    response_model=QualificationResponse,
    summary="Evaluate bidder financial qualification criteria",
)
async def evaluate_qualification(
    request: QualificationRequest,
    service: FinancialValidationService = Depends(get_financial_validation_service),
):
    try:
        result = await service.evaluate_qualification(
            tender_value=request.tender_value,
            domain=request.domain,
            annual_turnovers=request.annual_turnovers,
            net_worth=request.net_worth,
            rules=request.rules
        )
        return result
    except Exception as e:
        logger.exception("Financial qualification evaluation failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Financial qualification evaluation failed: {str(e)}"
        )
