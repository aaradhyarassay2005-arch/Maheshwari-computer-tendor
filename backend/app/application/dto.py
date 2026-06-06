from datetime import datetime
from decimal import Decimal
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class TenderCreateDTO(BaseModel):
    tender_number: str = Field(..., min_length=1)
    department: Optional[str] = None
    tender_value: Optional[Decimal] = Field(None, ge=0)
    closing_date: Optional[datetime] = None
    status: Optional[str] = None
    source_url: Optional[str] = None


class TenderUpdateDTO(BaseModel):
    tender_number: Optional[str] = None
    department: Optional[str] = None
    tender_value: Optional[Decimal] = Field(None, ge=0)
    closing_date: Optional[datetime] = None
    status: Optional[str] = None
    source_url: Optional[str] = None


class ExcelImportSummaryDTO(BaseModel):
    total_rows: int
    successful_imports: int
    duplicates_skipped: int
    validation_failures: int
    errors: List[Dict[str, Any]] = []
