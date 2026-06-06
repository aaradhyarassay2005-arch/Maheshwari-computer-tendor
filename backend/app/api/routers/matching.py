from fastapi import APIRouter, Depends, HTTPException, status
import structlog

from app.api.dependencies import get_project_matching_service
from app.application.matching_service import ProjectMatchingService
from app.schemas.matching import MatchingRequest, MatchingResponse, BackfillResponse

logger = structlog.get_logger("app.api.matching")
router = APIRouter(prefix="/projects", tags=["project-matching"])


@router.post(
    "/match",
    response_model=MatchingResponse,
    summary="Match an eligibility rule with past projects",
)
async def match_eligibility(
    request: MatchingRequest,
    service: ProjectMatchingService = Depends(get_project_matching_service),
):
    try:
        matches = await service.match_eligibility(
            eligibility_rule=request.eligibility_rule,
            limit=request.limit
        )
        return MatchingResponse(
            rule=request.eligibility_rule,
            matches=matches
        )
    except Exception as e:
        logger.exception("Eligibility matching failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Eligibility matching failed: {str(e)}"
        )


@router.post(
    "/embeddings/backfill",
    response_model=BackfillResponse,
    summary="Manually trigger vector embedding generation backfill pipeline",
)
async def backfill_embeddings(
    service: ProjectMatchingService = Depends(get_project_matching_service),
):
    try:
        count = await service.backfill_embeddings()
        return BackfillResponse(
            backfilled_count=count,
            message=f"Successfully generated and indexed {count} past project embeddings."
        )
    except Exception as e:
        logger.exception("Embedding backfill failed", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Embedding backfill failed: {str(e)}"
        )
