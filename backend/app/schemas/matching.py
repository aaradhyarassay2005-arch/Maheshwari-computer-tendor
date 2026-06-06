from typing import List
from pydantic import BaseModel, Field
from app.schemas.project import PastProjectResponse


class MatchingRequest(BaseModel):
    eligibility_rule: str = Field(
        ...,
        min_length=5,
        description="Eligibility criteria text to match (e.g. 'Executed OFC work of value 20 Lakhs')"
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of matched projects to return"
    )


class MatchingResultResponse(BaseModel):
    project: PastProjectResponse
    score: float
    eligible: bool
    reasons: List[str]


class MatchingResponse(BaseModel):
    rule: str
    matches: List[MatchingResultResponse]


class BackfillResponse(BaseModel):
    backfilled_count: int
    message: str
