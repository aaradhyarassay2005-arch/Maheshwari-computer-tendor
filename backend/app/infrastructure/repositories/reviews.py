from typing import List, Optional
from pydantic import UUID4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import TenderReview
from app.domain.repositories import ITenderReviewRepository
from app.infrastructure.db.models import TenderReviewORM


def to_domain_tender_review(orm: TenderReviewORM) -> TenderReview:
    return TenderReview(
        id=orm.id,
        tender_id=orm.tender_id,
        verdict=orm.verdict,
        reviewer_id=orm.reviewer_id,
        reviewed_at=orm.reviewed_at,
        original_values=orm.original_values,
        corrected_values=orm.corrected_values,
        comments=orm.comments
    )


class SQLAlchemyTenderReviewRepository(ITenderReviewRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, review: TenderReview) -> TenderReview:
        orm = TenderReviewORM(
            id=review.id,
            tender_id=review.tender_id,
            verdict=review.verdict,
            reviewer_id=review.reviewer_id,
            reviewed_at=review.reviewed_at,
            original_values=review.original_values,
            corrected_values=review.corrected_values,
            comments=review.comments
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_tender_review(orm)

    async def get_by_tender_id(self, tender_id: UUID4) -> List[TenderReview]:
        stmt = select(TenderReviewORM).where(TenderReviewORM.tender_id == tender_id).order_by(TenderReviewORM.reviewed_at.desc())
        result = await self.session.execute(stmt)
        orms = result.scalars().all()
        return [to_domain_tender_review(orm) for orm in orms]

    async def get_by_id(self, id: UUID4) -> Optional[TenderReview]:
        stmt = select(TenderReviewORM).where(TenderReviewORM.id == id)
        result = await self.session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm:
            return to_domain_tender_review(orm)
        return None
