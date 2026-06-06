from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Any
from pydantic import BaseModel, UUID4, field_serializer


class TenderMetadataResponse(BaseModel):
    id: UUID4
    tender_id: UUID4
    document_id: Optional[UUID4] = None
    tender_number: str
    tender_number_confidence: float
    department: str
    department_confidence: float
    tender_value: Optional[Decimal] = None
    tender_value_confidence: float
    emd: Optional[Decimal] = None
    emd_confidence: float
    closing_date: Optional[date] = None
    closing_date_confidence: float
    completion_period: str
    completion_period_confidence: float
    tender_type: str
    tender_type_confidence: float
    zone: str
    zone_confidence: float
    bid_system: str
    bid_system_confidence: float
    contract_type: str
    contract_type_confidence: float
    raw_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

    @field_serializer("tender_value", "emd")
    def serialize_decimal(self, v: Optional[Decimal]) -> Any:
        return str(v) if v is not None else "UNKNOWN"

    @field_serializer("closing_date")
    def serialize_date(self, v: Optional[date]) -> Any:
        return v.isoformat() if v is not None else "UNKNOWN"


class TriggerExtractionResponse(BaseModel):
    tender_id: UUID4
    status: str
    message: str
