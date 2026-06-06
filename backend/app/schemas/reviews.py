from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, UUID4
from app.domain.models import TenderStatus


class TenderMetadataCorrections(BaseModel):
    tender_number: Optional[str] = None
    department: Optional[str] = None
    tender_value: Optional[Decimal] = None
    closing_date: Optional[date] = None
    emd: Optional[Decimal] = None
    completion_period: Optional[str] = None
    tender_type: Optional[str] = None
    zone: Optional[str] = None
    bid_system: Optional[str] = None
    contract_type: Optional[str] = None


class ReviewSubmitRequest(BaseModel):
    verdict: TenderStatus = Field(..., description="Must be APPROVED or REJECTED")
    reviewer_id: str = Field(..., min_length=1)
    corrections: Optional[TenderMetadataCorrections] = None
    comments: Optional[str] = None


class ReviewResponse(BaseModel):
    id: UUID4
    tender_id: UUID4
    verdict: TenderStatus
    reviewer_id: str
    reviewed_at: datetime
    original_values: Dict[str, Any]
    corrected_values: Dict[str, Any]
    comments: Optional[str] = None

    model_config = {
        "from_attributes": True
    }
