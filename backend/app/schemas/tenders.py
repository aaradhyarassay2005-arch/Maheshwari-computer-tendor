from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, UUID4

from app.domain.models import TenderStatus


class TenderResponse(BaseModel):
    id: UUID4
    tender_number: str
    department: str
    source_url: str
    tender_value: Optional[Decimal] = None
    closing_date: Optional[date] = None
    status: TenderStatus
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class TendersListResponse(BaseModel):
    items: List[TenderResponse]
    total: int


class TenderCreateRequest(BaseModel):
    tender_number: str = Field(..., min_length=1, max_length=255)
    department: str = Field(..., min_length=1, max_length=255)
    source_url: str = Field(..., min_length=1, max_length=1000)
    tender_value: Optional[Decimal] = Field(None, ge=0)
    closing_date: Optional[date] = None


class TenderUpdateRequest(BaseModel):
    tender_number: Optional[str] = Field(None, min_length=1, max_length=255)
    department: Optional[str] = Field(None, min_length=1, max_length=255)
    source_url: Optional[str] = Field(None, min_length=1, max_length=1000)
    tender_value: Optional[Decimal] = Field(None, ge=0)
    closing_date: Optional[date] = None
    status: Optional[TenderStatus] = None
