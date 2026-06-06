import datetime
from typing import List, Optional
from pydantic import UUID4
from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import TenderDocument, TenderDocumentStatus
from app.domain.repositories import ITenderDocumentRepository
from app.infrastructure.db.models import TenderDocumentORM


def to_domain_document(orm: TenderDocumentORM) -> TenderDocument:
    return TenderDocument(
        id=orm.id,
        tender_id=orm.tender_id,
        file_name=orm.file_name,
        file_path=orm.file_path,
        sha256=orm.sha256,
        file_size=orm.file_size,
        mime_type=orm.mime_type,
        downloaded_at=orm.downloaded_at,
        status=orm.status,
        attempts=orm.attempts,
        error_message=orm.error_message,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyTenderDocumentRepository(ITenderDocumentRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, document: TenderDocument) -> TenderDocument:
        orm = TenderDocumentORM(
            id=document.id,
            tender_id=document.tender_id,
            file_name=document.file_name,
            file_path=document.file_path,
            sha256=document.sha256,
            file_size=document.file_size,
            mime_type=document.mime_type,
            downloaded_at=document.downloaded_at,
            status=document.status,
            attempts=document.attempts,
            error_message=document.error_message,
            created_at=document.created_at,
            updated_at=document.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_document(orm)

    async def get_by_id(self, id: UUID4) -> Optional[TenderDocument]:
        stmt = select(TenderDocumentORM).where(TenderDocumentORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_document(orm) if orm else None

    async def get_by_tender_id(self, tender_id: UUID4) -> Optional[TenderDocument]:
        stmt = select(TenderDocumentORM).where(TenderDocumentORM.tender_id == tender_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_document(orm) if orm else None

    async def get_by_hash(self, sha256: str) -> Optional[TenderDocument]:
        stmt = select(TenderDocumentORM).where(TenderDocumentORM.sha256 == sha256)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_document(orm) if orm else None

    async def update(self, document: TenderDocument) -> TenderDocument:
        stmt = select(TenderDocumentORM).where(TenderDocumentORM.id == document.id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"TenderDocument with ID {document.id} not found")
        
        orm.file_name = document.file_name
        orm.file_path = document.file_path
        orm.sha256 = document.sha256
        orm.file_size = document.file_size
        orm.mime_type = document.mime_type
        orm.downloaded_at = document.downloaded_at
        orm.status = document.status
        orm.attempts = document.attempts
        orm.error_message = document.error_message
        orm.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        await self.session.flush()
        return to_domain_document(orm)

    async def delete(self, id: UUID4) -> bool:
        stmt = select(TenderDocumentORM).where(TenderDocumentORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.flush()
            return True
        return False

    async def get_pending_or_retryable(self, max_attempts: int) -> List[TenderDocument]:
        stmt = select(TenderDocumentORM).where(
            or_(
                TenderDocumentORM.status == TenderDocumentStatus.PENDING,
                and_(
                    TenderDocumentORM.status == TenderDocumentStatus.FAILED,
                    TenderDocumentORM.attempts < max_attempts
                )
            )
        )
        result = await self.session.execute(stmt)
        return [to_domain_document(orm) for orm in result.scalars().all()]

    async def bulk_add(self, documents: List[TenderDocument]) -> List[TenderDocument]:
        orms = []
        for doc in documents:
            orm = TenderDocumentORM(
                id=doc.id,
                tender_id=doc.tender_id,
                file_name=doc.file_name,
                file_path=doc.file_path,
                sha256=doc.sha256,
                file_size=doc.file_size,
                mime_type=doc.mime_type,
                downloaded_at=doc.downloaded_at,
                status=doc.status,
                attempts=doc.attempts,
                error_message=doc.error_message,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
            )
            self.session.add(orm)
            orms.append(orm)
        await self.session.flush()
        return [to_domain_document(orm) for orm in orms]

