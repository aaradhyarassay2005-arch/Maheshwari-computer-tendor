from decimal import Decimal
from typing import List, Optional
from pydantic import BaseModel, Field


class QualificationRequest(BaseModel):
    tender_value: Decimal = Field(
        ...,
        ge=0,
        description="Target Tender Value to evaluate credentials against"
    )
    domain: str = Field(
        ...,
        min_length=1,
        description="Business domain (e.g. 'OFC') to filter similar projects"
    )
    annual_turnovers: List[Decimal] = Field(
        default_factory=list,
        description="List of turnovers for the preceding financial years"
    )
    net_worth: Decimal = Field(
        default=Decimal("0.00"),
        description="Current net worth of the bidder"
    )
    rules: Optional[List[str]] = Field(
        default=None,
        description="List of rules to evaluate (e.g. ['35_RULE', 'TURNOVER_RULE']). If null, evaluates all."
    )


class RuleEvaluationResult(BaseModel):
    rule_name: str
    passed: bool
    actual_value: Decimal
    required_value: Decimal
    reasoning: str


class QualificationResponse(BaseModel):
    qualified: bool
    confidence: float
    results: List[RuleEvaluationResult]
    summary_reasoning: str
