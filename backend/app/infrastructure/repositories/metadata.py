import datetime
from typing import Optional
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import TenderMetadata
from app.domain.repositories import ITenderMetadataRepository
from app.infrastructure.db.models import TenderMetadataORM


def to_domain_metadata(orm: TenderMetadataORM) -> TenderMetadata:
    return TenderMetadata(
        id=orm.id,
        tender_id=orm.tender_id,
        document_id=orm.document_id,
        tender_number=orm.tender_number or "UNKNOWN",
        tender_number_confidence=orm.tender_number_confidence,
        department=orm.department or "UNKNOWN",
        department_confidence=orm.department_confidence,
        tender_value=orm.tender_value,
        tender_value_confidence=orm.tender_value_confidence,
        emd=orm.emd,
        emd_confidence=orm.emd_confidence,
        closing_date=orm.closing_date,
        closing_date_confidence=orm.closing_date_confidence,
        completion_period=orm.completion_period or "UNKNOWN",
        completion_period_confidence=orm.completion_period_confidence,
        tender_type=orm.tender_type or "UNKNOWN",
        tender_type_confidence=orm.tender_type_confidence,
        zone=orm.zone or "UNKNOWN",
        zone_confidence=orm.zone_confidence,
        bid_system=orm.bid_system or "UNKNOWN",
        bid_system_confidence=orm.bid_system_confidence,
        contract_type=orm.contract_type or "UNKNOWN",
        contract_type_confidence=orm.contract_type_confidence,
        raw_text=orm.raw_text,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyTenderMetadataRepository(ITenderMetadataRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, metadata: TenderMetadata) -> TenderMetadata:
        orm = TenderMetadataORM(
            id=metadata.id,
            tender_id=metadata.tender_id,
            document_id=metadata.document_id,
            tender_number=metadata.tender_number,
            tender_number_confidence=metadata.tender_number_confidence,
            department=metadata.department,
            department_confidence=metadata.department_confidence,
            tender_value=metadata.tender_value,
            tender_value_confidence=metadata.tender_value_confidence,
            emd=metadata.emd,
            emd_confidence=metadata.emd_confidence,
            closing_date=metadata.closing_date,
            closing_date_confidence=metadata.closing_date_confidence,
            completion_period=metadata.completion_period,
            completion_period_confidence=metadata.completion_period_confidence,
            tender_type=metadata.tender_type,
            tender_type_confidence=metadata.tender_type_confidence,
            zone=metadata.zone,
            zone_confidence=metadata.zone_confidence,
            bid_system=metadata.bid_system,
            bid_system_confidence=metadata.bid_system_confidence,
            contract_type=metadata.contract_type,
            contract_type_confidence=metadata.contract_type_confidence,
            raw_text=metadata.raw_text,
            created_at=metadata.created_at,
            updated_at=metadata.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_metadata(orm)

    async def get_by_id(self, id: UUID4) -> Optional[TenderMetadata]:
        stmt = select(TenderMetadataORM).where(TenderMetadataORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_metadata(orm) if orm else None

    async def get_by_tender_id(self, tender_id: UUID4) -> Optional[TenderMetadata]:
        stmt = select(TenderMetadataORM).where(TenderMetadataORM.tender_id == tender_id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_metadata(orm) if orm else None

    async def update(self, metadata: TenderMetadata) -> TenderMetadata:
        stmt = select(TenderMetadataORM).where(TenderMetadataORM.id == metadata.id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"TenderMetadata with ID {metadata.id} not found")
        
        orm.document_id = metadata.document_id
        orm.tender_number = metadata.tender_number
        orm.tender_number_confidence = metadata.tender_number_confidence
        orm.department = metadata.department
        orm.department_confidence = metadata.department_confidence
        orm.tender_value = metadata.tender_value
        orm.tender_value_confidence = metadata.tender_value_confidence
        orm.emd = metadata.emd
        orm.emd_confidence = metadata.emd_confidence
        orm.closing_date = metadata.closing_date
        orm.closing_date_confidence = metadata.closing_date_confidence
        orm.completion_period = metadata.completion_period
        orm.completion_period_confidence = metadata.completion_period_confidence
        orm.tender_type = metadata.tender_type
        orm.tender_type_confidence = metadata.tender_type_confidence
        orm.zone = metadata.zone
        orm.zone_confidence = metadata.zone_confidence
        orm.bid_system = metadata.bid_system
        orm.bid_system_confidence = metadata.bid_system_confidence
        orm.contract_type = metadata.contract_type
        orm.contract_type_confidence = metadata.contract_type_confidence
        orm.raw_text = metadata.raw_text
        orm.updated_at = datetime.datetime.now(datetime.timezone.utc)
        
        await self.session.flush()
        return to_domain_metadata(orm)

    async def delete(self, id: UUID4) -> bool:
        stmt = select(TenderMetadataORM).where(TenderMetadataORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.flush()
            return True
        return False
