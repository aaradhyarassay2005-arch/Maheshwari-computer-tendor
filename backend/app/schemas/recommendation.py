from enum import Enum
from decimal import Decimal
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, UUID4


class BidRecommendation(str, Enum):
    GO = "GO"
    REVIEW = "REVIEW"
    NO_BID = "NO_BID"


class RecommendationRequest(BaseModel):
    annual_turnovers: List[Decimal] = Field(
        ...,
        description="List of turnovers for preceding financial years"
    )
    net_worth: Decimal = Field(
        ...,
        description="Net worth of the bidder"
    )
    eligibility_rules: List[str] = Field(
        default_factory=list,
        description="List of eligibility rules to check technical project matching"
    )


class RecommendationResponse(BaseModel):
    recommendation: BidRecommendation = Field(..., description="GO, REVIEW, or NO_BID decision")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Certainty score of evaluation (0.0 to 1.0)")
    win_probability: float = Field(..., ge=0.0, le=100.0, description="Calculated win probability percentage (0 to 100)")
    financial_qualification: Dict[str, Any] = Field(..., description="Financial qualification details")
    best_matching_project: Optional[Dict[str, Any]] = Field(None, description="Details of the highest matching past project")
    risk_level: str = Field(..., description="Overall risk level (LOW, MEDIUM, HIGH)")
    risk_summary: str = Field(..., description="Executive summary of compliance risks")
    required_documents: List[str] = Field(..., description="Dynamic checklist of required documents")
    key_reasons: List[str] = Field(..., description="List of key pros and cons reasons")
    decision_explanation: str = Field(..., description="Explainable reasoning detailing the logic")
