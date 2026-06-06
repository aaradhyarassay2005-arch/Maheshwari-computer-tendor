import structlog
from decimal import Decimal
from typing import List, Dict, Any
from pydantic import UUID4

from app.domain.exceptions import TenderNotFoundException, TenderNotParsedException
from app.domain.repositories import ITenderRepository, ITenderMetadataRepository
from app.application.boq_analytics_service import BOQAnalyticsService
from app.application.matching_service import ProjectMatchingService
from app.application.qualification_service import FinancialValidationService
from app.application.risk_service import RiskService
from app.application.recommendation_rules import RecommendationRulesEngine

logger = structlog.get_logger("app.recommendation")


class TenderRecommendationService:
    """Coordinates metadata, BOQ analytics, matching, qualification, and risk analysis to evaluate bid recommendations."""

    def __init__(
        self,
        tender_repo: ITenderRepository,
        metadata_repo: ITenderMetadataRepository,
        boq_analytics_service: BOQAnalyticsService,
        matching_service: ProjectMatchingService,
        qualification_service: FinancialValidationService,
        risk_service: RiskService,
        rules_engine: RecommendationRulesEngine,
    ):
        self.tender_repo = tender_repo
        self.metadata_repo = metadata_repo
        self.boq_analytics_service = boq_analytics_service
        self.matching_service = matching_service
        self.qualification_service = qualification_service
        self.risk_service = risk_service
        self.rules_engine = rules_engine

    async def _determine_domain(self, tender_id: UUID4, eligibility_rules: List[str]) -> str:
        """Heuristically determines the business domain of the tender based on BOQ categories or eligibility rules."""
        # 1. Analyze BOQ categories first
        try:
            cats = await self.boq_analytics_service.get_category_analysis(tender_id)
            if cats:
                # Filter out 'Others' and sort by value descending
                filtered = [c for c in cats if c.get("category") != "Others"]
                if filtered:
                    sorted_cats = sorted(filtered, key=lambda x: x.get("total_value", Decimal("0.0")), reverse=True)
                    top_category = sorted_cats[0].get("category")
                    if top_category:
                        logger.info("Determined tender domain from BOQ analytics", tender_id=str(tender_id), domain=top_category)
                        return top_category
        except Exception as e:
            logger.warn("Failed to determine domain from BOQ", error=str(e), tender_id=str(tender_id))

        # 2. Scan eligibility rules for domain keywords
        for rule in eligibility_rules:
            rule_lower = rule.lower()
            if "ofc" in rule_lower or "optical fiber" in rule_lower or "fibre" in rule_lower:
                return "OFC"
            if "network" in rule_lower or "switch" in rule_lower or "router" in rule_lower or "lan" in rule_lower:
                return "Networking"
            if "electrical" in rule_lower or "wiring" in rule_lower or "power" in rule_lower:
                return "Electrical Work"
            if "civil" in rule_lower or "concrete" in rule_lower or "drainage" in rule_lower:
                return "Civil Work"
            if "display" in rule_lower or "screen" in rule_lower or "signage" in rule_lower:
                return "Display Systems"
            if "ups" in rule_lower or "battery" in rule_lower or "inverter" in rule_lower:
                return "UPS"

        # Default fallback
        return "OFC"

    async def get_recommendation(
        self,
        tender_id: UUID4,
        annual_turnovers: List[Decimal],
        net_worth: Decimal,
        eligibility_rules: List[str]
    ) -> Dict[str, Any]:
        """Orchestrates all intelligence modules to compute the unified Go/No-Go bid recommendation."""
        logger.info("Evaluating bid recommendation", tender_id=str(tender_id), rules_count=len(eligibility_rules))

        # 1. Fetch Tender
        tender = await self.tender_repo.get_by_id(tender_id)
        if not tender:
            logger.error("Tender not found for recommendation", tender_id=str(tender_id))
            raise TenderNotFoundException(str(tender_id))

        # 2. Fetch Tender Metadata
        metadata = await self.metadata_repo.get_by_tender_id(tender_id)
        if not metadata or not metadata.raw_text:
            logger.error("Tender metadata or raw text missing", tender_id=str(tender_id))
            raise TenderNotParsedException(str(tender_id))

        # Resolve tender value
        tender_value = tender.tender_value or metadata.tender_value or Decimal("0.00")

        # 3. Determine business domain
        domain = await self._determine_domain(tender_id, eligibility_rules)

        # 4. Fetch BOQ Summary
        try:
            boq_summary = await self.boq_analytics_service.get_summary(tender_id)
        except Exception as e:
            logger.warn("BOQ summary not available, using empty defaults", error=str(e), tender_id=str(tender_id))
            boq_summary = {"total_items": 0, "total_estimated_value": Decimal("0.00")}

        # 5. Evaluate Financial Qualification
        financials_result = await self.qualification_service.evaluate_qualification(
            tender_value=tender_value,
            domain=domain,
            annual_turnovers=annual_turnovers,
            net_worth=net_worth
        )

        # 6. Evaluate Technical Eligibility / Project Matching
        matching_results = []
        for rule in eligibility_rules:
            matches = await self.matching_service.match_eligibility(rule, limit=5)
            matching_results.append({
                "rule": rule,
                "matches": matches
            })

        # 7. Evaluate Compliance Risks
        risk_result = await self.risk_service.analyze_tender_risks(tender_id)

        # 8. Run Recommendation Rules Engine
        result = self.rules_engine.evaluate_recommendation(
            tender_id=tender_id,
            metadata=metadata,
            boq_summary=boq_summary,
            qualification_result=financials_result,
            matching_results=matching_results,
            risk_result=risk_result
        )

        logger.info(
            "Bid recommendation evaluation complete",
            tender_id=str(tender_id),
            recommendation=result["recommendation"],
            win_probability=result["win_probability"]
        )
        return result
