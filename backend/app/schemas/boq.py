from datetime import datetime
from decimal import Decimal
from typing import Optional, List, Any
from pydantic import BaseModel, UUID4, field_serializer


class BOQItemResponse(BaseModel):
    id: UUID4
    tender_id: UUID4
    document_id: Optional[UUID4] = None
    item_code: str
    item_name: str
    quantity: Optional[Decimal] = None
    unit: str
    unit_rate: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    schedule_name: str
    confidence: float
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }

    @field_serializer("quantity", "unit_rate", "amount")
    def serialize_decimal(self, v: Optional[Decimal]) -> Any:
        return str(v) if v is not None else "UNKNOWN"


class BOQItemsListResponse(BaseModel):
    tender_id: UUID4
    total: int
    items: List[BOQItemResponse]


class TriggerBOQExtractionResponse(BaseModel):
    tender_id: UUID4
    status: str
    message: str
