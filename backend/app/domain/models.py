from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, UUID4


class TenderStatus(str, Enum):
    NEW = "NEW"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    PARSED = "PARSED"
    FAILED = "FAILED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class TenderDocumentStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    DOWNLOADED = "DOWNLOADED"
    FAILED = "FAILED"


class Tender(BaseModel):
    id: UUID4
    tender_number: str = Field(..., min_length=1)
    department: str = Field(..., min_length=1)
    source_url: str = Field(..., min_length=1)
    tender_value: Optional[Decimal] = Field(None, ge=0)
    closing_date: Optional[date] = None
    status: TenderStatus = TenderStatus.NEW
    created_at: datetime
    updated_at: datetime


class TenderDocument(BaseModel):
    id: UUID4
    tender_id: UUID4
    file_name: Optional[str] = None
    file_path: Optional[str] = None
    sha256: Optional[str] = None
    file_size: int = Field(0, ge=0)
    mime_type: Optional[str] = None
    downloaded_at: Optional[datetime] = None
    status: TenderDocumentStatus = TenderDocumentStatus.PENDING
    attempts: int = Field(0, ge=0)
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class TenderMetadata(BaseModel):
    id: UUID4
    tender_id: UUID4
    document_id: Optional[UUID4] = None
    tender_number: str = "UNKNOWN"
    tender_number_confidence: float = 0.0
    department: str = "UNKNOWN"
    department_confidence: float = 0.0
    tender_value: Optional[Decimal] = None
    tender_value_confidence: float = 0.0
    emd: Optional[Decimal] = None
    emd_confidence: float = 0.0
    closing_date: Optional[date] = None
    closing_date_confidence: float = 0.0
    completion_period: str = "UNKNOWN"
    completion_period_confidence: float = 0.0
    tender_type: str = "UNKNOWN"
    tender_type_confidence: float = 0.0
    zone: str = "UNKNOWN"
    zone_confidence: float = 0.0
    bid_system: str = "UNKNOWN"
    bid_system_confidence: float = 0.0
    contract_type: str = "UNKNOWN"
    contract_type_confidence: float = 0.0
    raw_text: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class BOQItem(BaseModel):
    id: UUID4
    tender_id: UUID4
    document_id: Optional[UUID4] = None
    item_code: str = "UNKNOWN"
    item_name: str = "UNKNOWN"
    quantity: Optional[Decimal] = None
    unit: str = "UNKNOWN"
    unit_rate: Optional[Decimal] = None
    amount: Optional[Decimal] = None
    schedule_name: str = "UNKNOWN"
    confidence: float = 0.0
    created_at: datetime
    updated_at: datetime


class PastProject(BaseModel):
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


class UserRole(str, Enum):
    SUPER_ADMIN = "SUPER_ADMIN"
    ADMIN = "ADMIN"
    MANAGER = "MANAGER"
    ANALYST = "ANALYST"
    VIEWER = "VIEWER"

    @property
    def level(self) -> int:
        levels = {
            UserRole.SUPER_ADMIN: 50,
            UserRole.ADMIN: 40,
            UserRole.MANAGER: 30,
            UserRole.ANALYST: 20,
            UserRole.VIEWER: 10
        }
        return levels.get(self, 0)


class User(BaseModel):
    id: UUID4
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    google_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str


class UserResponse(BaseModel):
    id: UUID4
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime


class UserSession(BaseModel):
    id: UUID4
    user_id: UUID4
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class AuditLog(BaseModel):
    id: UUID4
    timestamp: datetime
    user_id: Optional[str] = None
    user_role: Optional[str] = None
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    ip_address: Optional[str] = None
    client_agent: Optional[str] = None
    change_diff: Optional[str] = None  # JSON string representation


class TenderReview(BaseModel):
    id: UUID4
    tender_id: UUID4
    verdict: TenderStatus
    reviewer_id: str
    reviewed_at: datetime
    original_values: str  # JSON string representation
    corrected_values: str  # JSON string representation
    comments: Optional[str] = None






