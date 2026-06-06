import structlog
from typing import Dict, Any, List
from pydantic import UUID4

from app.domain.exceptions import TenderNotFoundException, TenderNotParsedException
from app.domain.repositories import ITenderRepository, ITenderMetadataRepository
from app.application.risk_engine import RiskEngine
from app.schemas.risk import RiskCategory, RiskSeverity

logger = structlog.get_logger("app.risk")


class RiskService:
    """Orchestrates database retrieval and executes the Risk Analysis Engine on a tender."""

    def __init__(
        self,
        tender_repo: ITenderRepository,
        metadata_repo: ITenderMetadataRepository,
        risk_engine: RiskEngine,
    ):
        self.tender_repo = tender_repo
        self.metadata_repo = metadata_repo
        self.risk_engine = risk_engine

    async def analyze_tender_risks(self, tender_id: UUID4) -> Dict[str, Any]:
        """Loads tender document and metadata, evaluates compliance risks, and returns results."""
        logger.info("Starting risk analysis for tender", tender_id=str(tender_id))

        # 1. Fetch Tender
        tender = await self.tender_repo.get_by_id(tender_id)
        if not tender:
            logger.error("Tender not found for risk analysis", tender_id=str(tender_id))
            raise TenderNotFoundException(str(tender_id))

        # 2. Fetch Tender Metadata
        metadata = await self.metadata_repo.get_by_tender_id(tender_id)
        if not metadata or not metadata.raw_text:
            logger.error("Tender metadata or raw text missing", tender_id=str(tender_id))
            raise TenderNotParsedException(str(tender_id))

        # 3. Evaluate Risks using the Engine
        raw_text = metadata.raw_text
        completion_period = metadata.completion_period
        emd = metadata.emd
        tender_value = tender.tender_value

        risk_results = self.risk_engine.evaluate_all(
            raw_text=raw_text,
            completion_period=completion_period,
            emd=emd,
            tender_value=tender_value
        )

        # 4. Calculate Overall Risk Score and Category
        total_score = sum(r["score"] for r in risk_results)
        overall_risk_score = round(total_score / 6.0, 2)

        if overall_risk_score < 3.0:
            overall_category = RiskCategory.LOW
        elif overall_risk_score < 6.0:
            overall_category = RiskCategory.MEDIUM
        else:
            overall_category = RiskCategory.HIGH

        # 5. Consolidate Unique Recommendations for MEDIUM or HIGH risks
        recommendations = []
        for r in risk_results:
            if r["recommendation"] and r["severity"] in (RiskSeverity.MEDIUM, RiskSeverity.HIGH):
                if r["recommendation"] not in recommendations:
                    recommendations.append(r["recommendation"])

        logger.info(
            "Risk analysis complete",
            tender_id=str(tender_id),
            overall_score=overall_risk_score,
            overall_category=overall_category,
            risks_detected_count=len([r for r in risk_results if r["severity"] != RiskSeverity.NONE])
        )

        return {
            "tender_id": tender_id,
            "overall_risk_score": overall_risk_score,
            "overall_risk_category": overall_category,
            "risks_detected": risk_results,
            "recommendations": recommendations,
        }
