import re
import logging
from decimal import Decimal
from datetime import date, timedelta, datetime
from typing import Optional, Dict, Any, List


logger = logging.getLogger(__name__)


class MatchingRankingEngine:
    """Extracts constraints from eligibility rules and evaluates projects against them."""

    def __init__(self):
        # Compiled patterns for value constraints
        self._pattern_lakh = re.compile(
            r"(?i)\b(\d+(?:\.\d+)?)\s*(?:lakh|lakhs|lac|lacs|lac\b)"
        )
        self._pattern_crore = re.compile(
            r"(?i)\b(\d+(?:\.\d+)?)\s*(?:crore|crores|cr|crs\b)"
        )
        self._pattern_raw_currency = re.compile(
            r"(?i)(?:Rs\.?|INR)\s*([0-9,]{4,15}(?:\.[0-9]{2})?)\b"
        )

        # Compiled patterns for temporal constraints
        self._pattern_years = re.compile(
            r"(?i)\b(?:last|past|preceding)\s*([0-9]+)\s*years\b"
        )

    def extract_constraints(self, rule: str) -> Dict[str, Any]:
        """Parses the eligibility rule text to extract minimum value and age limits."""
        min_value = None
        cutoff_date = None

        # 1. Parse Value Threshold
        # Try Crores first
        cr_match = self._pattern_crore.search(rule)
        if cr_match:
            try:
                val = float(cr_match.group(1))
                min_value = Decimal(str(int(val * 10_000_000)))
            except Exception as e:
                logger.warn(f"Failed to parse Crore threshold in rule: {e}")

        # Try Lakhs
        if min_value is None:
            lk_match = self._pattern_lakh.search(rule)
            if lk_match:
                try:
                    val = float(lk_match.group(1))
                    min_value = Decimal(str(int(val * 100_000)))
                except Exception as e:
                    logger.warn(f"Failed to parse Lakh threshold in rule: {e}")

        # Try Raw Currency (e.g. Rs. 50,00,000)
        if min_value is None:
            raw_match = self._pattern_raw_currency.search(rule)
            if raw_match:
                try:
                    raw_str = re.sub(r"[^\d.]", "", raw_match.group(1))
                    min_value = Decimal(raw_str)
                except Exception as e:
                    logger.warn(f"Failed to parse raw currency threshold in rule: {e}")

        # 2. Parse Temporal Threshold (Years limit)
        years_match = self._pattern_years.search(rule)
        if years_match:
            try:
                years = int(years_match.group(1))
                # cutoff date is exactly N years ago from today
                cutoff_date = date.today() - timedelta(days=years * 365)
            except Exception as e:
                logger.warn(f"Failed to parse years threshold in rule: {e}")

        parsed_constraints = {
            "min_value": min_value,
            "cutoff_date": cutoff_date,
        }

        logger.info(f"Extracted constraints from rule: {parsed_constraints}")
        return parsed_constraints

    def evaluate_project(
        self,
        project_payload: Dict[str, Any],
        similarity_score: float,
        constraints: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Checks if the project payload satisfies the eligibility rule constraints."""
        eligible = True
        reasons = []

        # 1. Check Value Constraint
        min_value = constraints.get("min_value")
        if min_value is not None:
            proj_val_str = project_payload.get("project_value", "0")
            try:
                project_value = Decimal(proj_val_str)
                if project_value < min_value:
                    eligible = False
                    reasons.append(
                        f"Project value of {project_value:,.2f} is below the required threshold of {min_value:,.2f}"
                    )
            except Exception as e:
                logger.error(f"Failed to convert project value '{proj_val_str}': {e}")
                eligible = False
                reasons.append("Project value is missing or unparseable")

        # 2. Check Temporal/Age Constraint
        cutoff_date = constraints.get("cutoff_date")
        if cutoff_date is not None:
            comp_date_str = project_payload.get("completion_date")
            if comp_date_str:
                try:
                    completion_date = date.fromisoformat(comp_date_str)
                    if completion_date < cutoff_date:
                        eligible = False
                        reasons.append(
                            f"Project completion date {completion_date} is older than the required limit of {cutoff_date}"
                        )
                except Exception as e:
                    logger.error(f"Failed to parse ISO completion date '{comp_date_str}': {e}")
                    eligible = False
                    reasons.append("Project completion date format is invalid")
            else:
                eligible = False
                reasons.append("Project completion date is missing but required by temporal constraint")

        return {
            "project": {
                "id": project_payload.get("project_id"),
                "project_name": project_payload.get("project_name", "UNKNOWN"),
                "client": project_payload.get("client", "UNKNOWN"),
                "project_value": Decimal(project_payload.get("project_value", "0.00")),
                "completion_date": date.fromisoformat(project_payload.get("completion_date")) if project_payload.get("completion_date") else None,
                "domain": project_payload.get("domain", "Other"),
                "location": project_payload.get("location", "UNKNOWN"),
                "document_type": project_payload.get("document_type", "UNKNOWN"),
                "document_path": project_payload.get("document_path"),
                "created_at": datetime.fromisoformat(project_payload["created_at"]) if project_payload.get("created_at") else datetime.now(),
                "updated_at": datetime.fromisoformat(project_payload["updated_at"]) if project_payload.get("updated_at") else datetime.now(),
            },
            "score": similarity_score,
            "eligible": eligible,
            "reasons": reasons,
        }

