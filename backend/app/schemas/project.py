from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, UUID4


class PastProjectResponse(BaseModel):
    id: UUID4
    project_name: str
    client: str
    project_value: Decimal
    completion_date: Optional[date] = None
    domain: str
    location: str
    document_type: str
    document_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class ProjectsListResponse(BaseModel):
    items: List[PastProjectResponse]
    total: int


class CapabilityResponse(BaseModel):
    domain: str
    project_count: int
    total_value: Decimal
    max_value: Decimal
    locations: List[str]

    model_config = {
        "from_attributes": True
    }
