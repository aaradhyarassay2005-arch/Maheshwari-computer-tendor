import structlog
from decimal import Decimal
from typing import List, Dict, Any, Optional

from app.domain.repositories import IPastProjectRepository
from app.application.qualification_engine import FinancialRuleEngine

logger = structlog.get_logger("app.qualification")


class FinancialValidationService:
    """Orchestrates past project queries and evaluates bidder financial qualification."""

    def __init__(
        self,
        project_repo: IPastProjectRepository,
        rule_engine: FinancialRuleEngine,
    ):
        self.project_repo = project_repo
        self.rule_engine = rule_engine

    async def evaluate_qualification(
        self,
        tender_value: Decimal,
        domain: str,
        annual_turnovers: List[Decimal],
        net_worth: Decimal,
        rules: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Queries project history and evaluates all specified qualification rules."""
        logger.info(
            "Evaluating financial qualification",
            tender_value=str(tender_value),
            domain=domain,
            rules=rules,
        )

        # 1. Retrieve all projects in the specified business domain
        # We load a high limit to get all projects in that domain
        projects, _ = await self.project_repo.list(
            skip=0,
            limit=1000,
            domain=domain,
        )
        logger.info("Retrieved similar domain projects", count=len(projects), domain=domain)

        # 2. Determine which rules to evaluate
        all_percentage_rules = {"35_RULE", "40_RULE", "50_RULE", "60_RULE"}
        target_rules = rules
        if not target_rules:
            target_rules = ["35_RULE", "40_RULE", "50_RULE", "60_RULE", "TURNOVER_RULE", "NET_WORTH_RULE"]

        results = []
        qualified = True

        for rule in target_rules:
            rule_upper = rule.upper()
            if rule_upper in all_percentage_rules:
                # Extract percentage number from rule name, e.g., "35_RULE" -> Decimal("35")
                pct_str = rule_upper.split("_")[0]
                pct = Decimal(pct_str)
                res = self.rule_engine.evaluate_percentage_work_rule(
                    tender_value=tender_value,
                    projects=projects,
                    percentage=pct,
                )
                results.append(res)
                if not res["passed"]:
                    qualified = False

            elif rule_upper == "TURNOVER_RULE":
                res = self.rule_engine.evaluate_turnover_rule(
                    tender_value=tender_value,
                    turnovers=annual_turnovers,
                )
                results.append(res)
                if not res["passed"]:
                    qualified = False

            elif rule_upper == "NET_WORTH_RULE":
                res = self.rule_engine.evaluate_net_worth_rule(
                    tender_value=tender_value,
                    net_worth=net_worth,
                )
                results.append(res)
                if not res["passed"]:
                    qualified = False

        passed_count = sum(1 for r in results if r["passed"])
        total_count = len(results)

        if qualified:
            summary = f"Bidder is QUALIFIED. Passed all {total_count} evaluated financial qualification criteria."
        else:
            summary = f"Bidder is NOT QUALIFIED. Passed {passed_count} of {total_count} evaluated financial qualification criteria."

        logger.info("Financial qualification evaluation complete", qualified=qualified, passed=passed_count, total=total_count)

        return {
            "qualified": qualified,
            "confidence": 1.0,  # Strict mathematical rule validation is 100% deterministic
            "results": results,
            "summary_reasoning": summary,
        }
