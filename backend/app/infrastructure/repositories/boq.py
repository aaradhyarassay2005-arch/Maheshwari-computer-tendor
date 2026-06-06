import datetime
from typing import List, Optional
from pydantic import UUID4
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import BOQItem
from app.domain.repositories import IBOQItemRepository
from app.infrastructure.db.models import TenderBOQItemORM


def to_domain_boq(orm: TenderBOQItemORM) -> BOQItem:
    return BOQItem(
        id=orm.id,
        tender_id=orm.tender_id,
        document_id=orm.document_id,
        item_code=orm.item_code or "UNKNOWN",
        item_name=orm.item_name or "UNKNOWN",
        quantity=orm.quantity,
        unit=orm.unit or "UNKNOWN",
        unit_rate=orm.unit_rate,
        amount=orm.amount,
        schedule_name=orm.schedule_name or "UNKNOWN",
        confidence=orm.confidence,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyBOQItemRepository(IBOQItemRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, item: BOQItem) -> BOQItem:
        orm = TenderBOQItemORM(
            id=item.id,
            tender_id=item.tender_id,
            document_id=item.document_id,
            item_code=item.item_code,
            item_name=item.item_name,
            quantity=item.quantity,
            unit=item.unit,
            unit_rate=item.unit_rate,
            amount=item.amount,
            schedule_name=item.schedule_name,
            confidence=item.confidence,
            created_at=item.created_at,
            updated_at=item.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_boq(orm)

    async def get_by_tender_id(self, tender_id: UUID4) -> List[BOQItem]:
        stmt = select(TenderBOQItemORM).where(TenderBOQItemORM.tender_id == tender_id).order_by(TenderBOQItemORM.created_at.asc())
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        return [to_domain_boq(orm) for orm in orms]

    async def bulk_add(self, items: List[BOQItem]) -> List[BOQItem]:
        orms = []
        for item in items:
            orm = TenderBOQItemORM(
                id=item.id,
                tender_id=item.tender_id,
                document_id=item.document_id,
                item_code=item.item_code,
                item_name=item.item_name,
                quantity=item.quantity,
                unit=item.unit,
                unit_rate=item.unit_rate,
                amount=item.amount,
                schedule_name=item.schedule_name,
                confidence=item.confidence,
                created_at=item.created_at,
                updated_at=item.updated_at,
            )
            orms.append(orm)
        self.session.add_all(orms)
        await self.session.flush()
        return [to_domain_boq(orm) for orm in orms]

    async def delete_by_tender_id(self, tender_id: UUID4) -> None:
        stmt = delete(TenderBOQItemORM).where(TenderBOQItemORM.tender_id == tender_id)
        await self.session.execute(stmt)
        await self.session.flush()
