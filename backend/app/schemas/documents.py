from datetime import datetime
from typing import Optional
from pydantic import BaseModel, UUID4
from app.domain.models import TenderDocumentStatus


class TenderDocumentResponse(BaseModel):
    id: UUID4
    tender_id: UUID4
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    sha256: Optional[str] = None
    file_size: int
    mime_type: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    status: TenderDocumentStatus
    attempts: int
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {
        "from_attributes": True
    }


class TriggerDownloadResponse(BaseModel):
    tender_id: UUID4
    status: TenderDocumentStatus
    message: str
