import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional
from app.domain.models import PastProject

logger = logging.getLogger(__name__)


class FinancialRuleEngine:
    """Evaluates deterministic financial qualification criteria for tenders."""

    def evaluate_percentage_work_rule(
        self, tender_value: Decimal, projects: List[PastProject], percentage: Decimal
    ) -> Dict[str, Any]:
        """Evaluates if the bidder has executed at least one project costing >= percentage of tender value."""
        required_value = (percentage / Decimal("100")) * tender_value
        
        # Filter projects that have a value
        valid_projects = [p for p in projects if p.project_value is not None]
        
        highest_value = Decimal("0.00")
        matching_project = None

        for p in valid_projects:
            if p.project_value > highest_value:
                highest_value = p.project_value
                matching_project = p

        passed = highest_value >= required_value

        if passed and matching_project:
            reasoning = (
                f"Passed: Found similar project '{matching_project.project_name}' "
                f"with value of {highest_value:,.2f} which is >= required "
                f"{required_value:,.2f} ({percentage}% of Tender Value)."
            )
        else:
            reasoning = (
                f"Failed: No single similar project with value >= {required_value:,.2f} "
                f"({percentage}% of Tender Value) was found. "
                f"Highest project value found: {highest_value:,.2f}."
            )

        return {
            "rule_name": f"{percentage}_RULE",
            "passed": passed,
            "actual_value": highest_value,
            "required_value": required_value,
            "reasoning": reasoning,
        }

    def evaluate_turnover_rule(
        self,
        tender_value: Decimal,
        turnovers: List[Decimal],
        required_percentage: Decimal = Decimal("150"),
    ) -> Dict[str, Any]:
        """Evaluates if average annual turnover is >= required percentage of tender value (default 150%)."""
        required_value = (required_percentage / Decimal("100")) * tender_value
        
        if turnovers:
            avg_turnover = sum(turnovers) / Decimal(str(len(turnovers)))
        else:
            avg_turnover = Decimal("0.00")

        passed = avg_turnover >= required_value

        if passed:
            reasoning = (
                f"Passed: Average annual turnover of {avg_turnover:,.2f} is >= required "
                f"{required_value:,.2f} ({required_percentage}% of Tender Value)."
            )
        else:
            reasoning = (
                f"Failed: Average annual turnover of {avg_turnover:,.2f} is below the "
                f"required threshold of {required_value:,.2f} ({required_percentage}% of Tender Value)."
            )

        return {
            "rule_name": "TURNOVER_RULE",
            "passed": passed,
            "actual_value": avg_turnover,
            "required_value": required_value,
            "reasoning": reasoning,
        }

    def evaluate_net_worth_rule(
        self,
        tender_value: Decimal,
        net_worth: Decimal,
        required_percentage: Optional[Decimal] = None,
    ) -> Dict[str, Any]:
        """Evaluates if net worth is positive, or satisfies a required percentage of tender value."""
        if required_percentage is not None:
            required_value = (required_percentage / Decimal("100")) * tender_value
            passed = net_worth >= required_value
            rule_name = "NET_WORTH_PERCENT_RULE"
            
            if passed:
                reasoning = (
                    f"Passed: Net worth of {net_worth:,.2f} is >= required "
                    f"{required_value:,.2f} ({required_percentage}% of Tender Value)."
                )
            else:
                reasoning = (
                    f"Failed: Net worth of {net_worth:,.2f} is below the "
                    f"required threshold of {required_value:,.2f} ({required_percentage}% of Tender Value)."
                )
        else:
            required_value = Decimal("0.00")
            passed = net_worth >= required_value
            rule_name = "NET_WORTH_RULE"
            
            if passed:
                reasoning = f"Passed: Net worth of {net_worth:,.2f} is positive."
            else:
                reasoning = f"Failed: Net worth of {net_worth:,.2f} is negative."

        return {
            "rule_name": rule_name,
            "passed": passed,
            "actual_value": net_worth,
            "required_value": required_value,
            "reasoning": reasoning,
        }
