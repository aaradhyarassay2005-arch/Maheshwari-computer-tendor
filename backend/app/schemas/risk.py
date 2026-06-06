from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, UUID4


class RiskCategory(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskSeverity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class RiskDetectionResult(BaseModel):
    risk_name: str = Field(..., description="The name of the risk category detected")
    severity: RiskSeverity = Field(..., description="The severity level of the risk")
    score: float = Field(..., ge=0.0, le=10.0, description="The numeric score for this risk category (0.0 to 10.0)")
    evidence: Optional[str] = Field(None, description="The text evidence or context where the risk was detected")
    recommendation: Optional[str] = Field(None, description="Mitigation recommendation for the specific risk")


class RiskAnalysisResponse(BaseModel):
    tender_id: UUID4 = Field(..., description="UUID of the analyzed tender")
    overall_risk_score: float = Field(..., ge=0.0, le=10.0, description="Weighted average risk score")
    overall_risk_category: RiskCategory = Field(..., description="Overall risk category derived from the score")
    risks_detected: List[RiskDetectionResult] = Field(default_factory=list, description="Breakdown of specific risks detected")
    recommendations: List[str] = Field(default_factory=list, description="Consolidated mitigation recommendations")
