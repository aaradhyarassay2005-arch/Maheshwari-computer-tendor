from datetime import datetime, date
from decimal import Decimal
from typing import Optional, List
from uuid import UUID, uuid4
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, text, func, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domain.models import TenderStatus, TenderDocumentStatus, UserRole


class Base(DeclarativeBase):
    pass


class TenderORM(Base):
    __tablename__ = "tenders"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_number: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    tender_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    closing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[TenderStatus] = mapped_column(
        SQLEnum(TenderStatus, name="tender_status_enum", native_enum=False),
        nullable=False,
        default=TenderStatus.NEW,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    document: Mapped[Optional["TenderDocumentORM"]] = relationship(
        "TenderDocumentORM", back_populates="tender", cascade="all, delete-orphan", uselist=False
    )
    metadata_record: Mapped[Optional["TenderMetadataORM"]] = relationship(
        "TenderMetadataORM", back_populates="tender", cascade="all, delete-orphan", uselist=False
    )
    boq_items: Mapped[List["TenderBOQItemORM"]] = relationship(
        "TenderBOQItemORM", back_populates="tender", cascade="all, delete-orphan"
    )
    reviews: Mapped[List["TenderReviewORM"]] = relationship(
        "TenderReviewORM", back_populates="tender", cascade="all, delete-orphan"
    )



class TenderDocumentORM(Base):
    __tablename__ = "tender_documents"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    file_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    file_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    sha256: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True, index=True)
    file_size: Mapped[int] = mapped_column(nullable=False, default=0)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    downloaded_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[TenderDocumentStatus] = mapped_column(
        SQLEnum(TenderDocumentStatus, name="tender_document_status_enum", native_enum=False),
        nullable=False,
        default=TenderDocumentStatus.PENDING,
        index=True
    )
    attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tender: Mapped["TenderORM"] = relationship("TenderORM", back_populates="document")


class TenderMetadataORM(Base):
    __tablename__ = "tender_metadata"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    document_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tender_documents.id", ondelete="SET NULL"), unique=True, nullable=True, index=True
    )
    
    tender_number: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tender_number_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    department: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    department_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    tender_value: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    tender_value_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    emd: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    emd_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    closing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    closing_date_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    completion_period: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    completion_period_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    tender_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    tender_type_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    zone_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    bid_system: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    bid_system_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    contract_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    contract_type_confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)
    
    raw_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tender: Mapped["TenderORM"] = relationship("TenderORM", back_populates="metadata_record")


class TenderBOQItemORM(Base):
    __tablename__ = "tender_boq_items"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tender_documents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    item_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    item_name: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    quantity: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    unit_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(20, 4), nullable=True)
    schedule_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False, default=0.0)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tender: Mapped["TenderORM"] = relationship("TenderORM", back_populates="boq_items")


class PastProjectORM(Base):
    __tablename__ = "past_projects"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    project_name: Mapped[str] = mapped_column(String(255), nullable=False)
    client: Mapped[str] = mapped_column(String(255), nullable=False)
    project_value: Mapped[Decimal] = mapped_column(Numeric(20, 2), nullable=False, index=True)
    completion_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    domain: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(50), nullable=False)
    document_path: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class AuditLogORM(Base):
    __tablename__ = "audit_logs"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    user_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    user_role: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    resource_type: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    client_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    change_diff: Mapped[Optional[str]] = mapped_column(String, nullable=True)


class TenderReviewORM(Base):
    __tablename__ = "tender_reviews"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    tender_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("tenders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    verdict: Mapped[TenderStatus] = mapped_column(
        SQLEnum(TenderStatus, name="tender_status_enum", native_enum=False),
        nullable=False
    )
    reviewer_id: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    original_values: Mapped[str] = mapped_column(String, nullable=False)
    corrected_values: Mapped[str] = mapped_column(String, nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)

    tender: Mapped["TenderORM"] = relationship("TenderORM", back_populates="reviews")


class UserORM(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", native_enum=False),
        nullable=False,
        default=UserRole.VIEWER,
        index=True
    )
    is_active: Mapped[bool] = mapped_column(nullable=False, default=True)
    google_id: Mapped[Optional[str]] = mapped_column(String(255), unique=True, nullable=True, index=True)
    reset_token: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    reset_token_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    sessions: Mapped[List["SessionORM"]] = relationship(
        "SessionORM", back_populates="user", cascade="all, delete-orphan"
    )


class SessionORM(Base):
    __tablename__ = "sessions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    refresh_token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    is_revoked: Mapped[bool] = mapped_column(nullable=False, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )

    user: Mapped["UserORM"] = relationship("UserORM", back_populates="sessions")






