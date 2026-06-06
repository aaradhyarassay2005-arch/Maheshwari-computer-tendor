from typing import List
from pydantic import UUID4
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import DownloadHistory
from app.domain.repositories import IDownloadHistoryRepository
from app.infrastructure.db.models import DownloadHistoryORM


def to_domain_history(orm: DownloadHistoryORM) -> DownloadHistory:
    return DownloadHistory(
        id=orm.id,
        tender_id=orm.tender_id,
        status=orm.status,
        attempt_number=orm.attempt_number,
        error_message=orm.error_message,
        created_at=orm.created_at,
    )


class SQLAlchemyDownloadHistoryRepository(IDownloadHistoryRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, history: DownloadHistory) -> DownloadHistory:
        orm = DownloadHistoryORM(
            id=history.id,
            tender_id=history.tender_id,
            status=history.status,
            attempt_number=history.attempt_number,
            error_message=history.error_message,
            created_at=history.created_at,
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_history(orm)

    async def get_by_tender_id(self, tender_id: UUID4) -> List[DownloadHistory]:
        stmt = select(DownloadHistoryORM).where(DownloadHistoryORM.tender_id == tender_id).order_by(DownloadHistoryORM.created_at.asc())
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        return [to_domain_history(orm) for orm in orms]

    async def get_attempts_count(self, tender_id: UUID4) -> int:
        stmt = select(func.count()).select_from(DownloadHistoryORM).where(DownloadHistoryORM.tender_id == tender_id)
        result = await self.session.execute(stmt)
        return result.scalar_one()
