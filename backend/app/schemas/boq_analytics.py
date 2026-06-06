from decimal import Decimal
from typing import List, Optional, Any
from pydantic import BaseModel, UUID4, field_serializer

from app.schemas.boq import BOQItemResponse


class BOQSummaryResponse(BaseModel):
    total_items: int
    total_quantity: Decimal
    total_estimated_value: Decimal
    top_items: List[BOQItemResponse]

    @field_serializer("total_quantity", "total_estimated_value")
    def serialize_decimal(self, v: Decimal) -> Any:
        return str(v) if v is not None else "0.0"


class BOQCategoryAnalysisResponse(BaseModel):
    category: str
    item_count: int
    total_value: Decimal
    percentage: Decimal

    @field_serializer("total_value", "percentage")
    def serialize_decimal(self, v: Decimal) -> Any:
        return str(v) if v is not None else "0.0"


class BOQCategoriesResponse(BaseModel):
    tender_id: UUID4
    categories: List[BOQCategoryAnalysisResponse]
