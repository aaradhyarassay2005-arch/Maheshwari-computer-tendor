from typing import List, Optional, Tuple
from pydantic import UUID4
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Tender, TenderStatus
from app.domain.repositories import ITenderRepository
from app.infrastructure.db.models import TenderORM


def to_domain_tender(orm: TenderORM) -> Tender:
    return Tender(
        id=orm.id,
        tender_number=orm.tender_number,
        department=orm.department,
        source_url=orm.source_url,
        tender_value=orm.tender_value,
        closing_date=orm.closing_date,
        status=orm.status,
        created_at=orm.created_at,
        updated_at=orm.updated_at,
    )


class SQLAlchemyTenderRepository(ITenderRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, tender: Tender) -> Tender:
        orm = TenderORM(
            id=tender.id,
            tender_number=tender.tender_number,
            department=tender.department,
            source_url=tender.source_url,
            tender_value=tender.tender_value,
            closing_date=tender.closing_date,
            status=tender.status,
            created_at=tender.created_at,
            updated_at=tender.updated_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_tender(orm)

    async def get_by_id(self, id: UUID4) -> Optional[Tender]:
        stmt = select(TenderORM).where(TenderORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_tender(orm) if orm else None

    async def get_by_tender_number(self, tender_number: str) -> Optional[Tender]:
        stmt = select(TenderORM).where(TenderORM.tender_number == tender_number)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_tender(orm) if orm else None

    async def get_by_source_url(self, source_url: str) -> Optional[Tender]:
        stmt = select(TenderORM).where(TenderORM.source_url == source_url)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        return to_domain_tender(orm) if orm else None

    async def list(
        self, skip: int = 0, limit: int = 10, search: Optional[str] = None
    ) -> Tuple[List[Tender], int]:
        stmt = select(TenderORM).order_by(TenderORM.created_at.desc())
        count_stmt = select(func.count()).select_from(TenderORM)

        if search:
            search_filter = or_(
                TenderORM.tender_number.ilike(f"%{search}%"),
                TenderORM.department.ilike(f"%{search}%")
            )
            stmt = stmt.where(search_filter)
            count_stmt = count_stmt.where(search_filter)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()

        tenders = [to_domain_tender(orm) for orm in orms]
        return tenders, total

    async def update(self, tender: Tender) -> Tender:
        stmt = select(TenderORM).where(TenderORM.id == tender.id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if not orm:
            raise ValueError(f"Tender with ID {tender.id} not found")

        orm.tender_number = tender.tender_number
        orm.department = tender.department
        orm.source_url = tender.source_url
        orm.tender_value = tender.tender_value
        orm.closing_date = tender.closing_date
        orm.status = tender.status
        orm.updated_at = tender.updated_at

        await self.session.flush()
        return to_domain_tender(orm)

    async def delete(self, id: UUID4) -> bool:
        stmt = select(TenderORM).where(TenderORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            await self.session.delete(orm)
            await self.session.flush()
            return True
        return False

    async def bulk_add(self, tenders: List[Tender]) -> List[Tender]:
        orms = [
            TenderORM(
                id=t.id,
                tender_number=t.tender_number,
                department=t.department,
                source_url=t.source_url,
                tender_value=t.tender_value,
                closing_date=t.closing_date,
                status=t.status,
                created_at=t.created_at,
                updated_at=t.updated_at,
            )
            for t in tenders
        ]
        self.session.add_all(orms)
        await self.session.flush()
        return tenders

    async def get_by_statuses(self, statuses: List[TenderStatus]) -> List[Tender]:
        stmt = select(TenderORM).where(TenderORM.status.in_(statuses))
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        return [to_domain_tender(orm) for orm in orms]
