import structlog
from typing import List, Optional
from pydantic import UUID4

from app.domain.models import BOQItem
from app.domain.repositories import ITenderRepository, IBOQItemRepository
from app.domain.exceptions import TenderNotFoundException
from app.application.boq_analytics_engine import BOQAnalyticsEngine

logger = structlog.get_logger("app.boq.analytics")


class BOQAnalyticsService:
    def __init__(
        self,
        tender_repo: ITenderRepository,
        boq_repo: IBOQItemRepository,
        analytics_engine: BOQAnalyticsEngine,
    ):
        self.tender_repo = tender_repo
        self.boq_repo = boq_repo
        self.analytics_engine = analytics_engine

    async def get_summary(self, tender_id: UUID4) -> dict:
        tender = await self.tender_repo.get_by_id(tender_id)
        if not tender:
            raise TenderNotFoundException(str(tender_id))

        items = await self.boq_repo.get_by_tender_id(tender_id)
        logger.info("Computing BOQ summary analytics", tender_id=str(tender_id), count=len(items))
        return self.analytics_engine.compute_summary(items)

    async def get_category_analysis(self, tender_id: UUID4) -> List[dict]:
        tender = await self.tender_repo.get_by_id(tender_id)
        if not tender:
            raise TenderNotFoundException(str(tender_id))

        items = await self.boq_repo.get_by_tender_id(tender_id)
        logger.info("Computing BOQ category analytics", tender_id=str(tender_id), count=len(items))
        return self.analytics_engine.compute_category_analysis(items)
