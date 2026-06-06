import re
import logging
from decimal import Decimal
from typing import List, Dict, Any, Optional

from app.schemas.risk import RiskSeverity

logger = logging.getLogger(__name__)


class RiskEngine:
    """Evaluates tender compliance risks using raw text and metadata."""

    def _find_percentage_near_keywords(self, text: str, keywords: List[str], window: int = 150) -> Optional[float]:
        """Helper to find percentage mentions in text near specific keywords, returning the highest if multiple are found."""
        if not text:
            return None
        text_lower = text.lower()
        found_percentages = []
        for kw in keywords:
            idx = 0
            while True:
                idx = text_lower.find(kw.lower(), idx)
                if idx == -1:
                    break
                
                # Extract snippet window following the keyword
                sub = text[idx : idx + len(kw) + window]
                # Find all numbers followed by % in the window
                matches = re.findall(r'(\d+(?:\.\d+)?)\s*%', sub)
                for m in matches:
                    try:
                        found_percentages.append(float(m))
                    except ValueError:
                        pass
                idx += len(kw)
        
        if found_percentages:
            return max(found_percentages)
        return None


    def _parse_completion_period_days(self, period_str: str) -> Optional[int]:
        """Parses a completion period string into an approximate number of days."""
        if not period_str or period_str.upper() == "UNKNOWN":
            return None
        period_str = period_str.lower()
        
        # Check for days, e.g. "90 days", "90"
        match_days = re.search(r'(\d+)\s*(?:day|days)', period_str)
        if match_days:
            return int(match_days.group(1))
        
        # Check for months, e.g. "3 months"
        match_months = re.search(r'(\d+)\s*(?:month|months)', period_str)
        if match_months:
            return int(match_months.group(1)) * 30
        
        # Check for weeks, e.g. "12 weeks"
        match_weeks = re.search(r'(\d+)\s*(?:week|weeks)', period_str)
        if match_weeks:
            return int(match_weeks.group(1)) * 7
            
        # Check for pure digits
        match_num = re.search(r'^(\d+)$', period_str.strip())
        if match_num:
            return int(match_num.group(1))
            
        return None

    def evaluate_performance_guarantee(self, raw_text: str) -> Dict[str, Any]:
        """Checks for Performance Guarantee/Security Deposit risk."""
        keywords = [
            "Performance Guarantee",
            "Performance Security",
            "Security Deposit",
            "Bank Guarantee",
            "Performance BG",
            "SD Clause"
        ]
        
        # Check if keywords are present
        has_keywords = any(kw.lower() in raw_text.lower() for kw in keywords) if raw_text else False
        
        if not has_keywords:
            return {
                "risk_name": "PERFORMANCE_GUARANTEE",
                "severity": RiskSeverity.NONE,
                "score": 0.0,
                "evidence": "No performance guarantee or security deposit clauses found in text.",
                "recommendation": None
            }

        percentage = self._find_percentage_near_keywords(raw_text, keywords)
        rec = "Arrange bank credit lines early to cover the performance guarantee value without choking working capital."

        if percentage is not None:
            if percentage > 10.0:
                severity = RiskSeverity.HIGH
                score = 8.5
                evidence = f"Performance guarantee/security deposit of {percentage}% exceeds the high risk threshold of 10%."
            elif percentage >= 5.0:
                severity = RiskSeverity.MEDIUM
                score = 5.0
                evidence = f"Performance guarantee/security deposit of {percentage}% is within the medium risk threshold (5% - 10%)."
            else:
                severity = RiskSeverity.LOW
                score = 2.0
                evidence = f"Performance guarantee/security deposit of {percentage}% is within the low risk threshold (< 5%)."
        else:
            # Keywords found, but no percentage could be parsed. Default to Medium.
            severity = RiskSeverity.MEDIUM
            score = 5.0
            evidence = "Performance guarantee or security deposit clauses detected, but specific percentage was not found."

        return {
            "risk_name": "PERFORMANCE_GUARANTEE",
            "severity": severity,
            "score": score,
            "evidence": evidence,
            "recommendation": rec
        }

    def evaluate_liquidated_damages(self, raw_text: str) -> Dict[str, Any]:
        """Checks for Liquidated Damages/Late Delivery penalty risk."""
        keywords = [
            "Liquidated Damages",
            "LD Clause",
            "delay penalty",
            "penalty for delay",
            "0.5% per week",
            "penalty for late"
        ]

        has_keywords = any(kw.lower() in raw_text.lower() for kw in keywords) if raw_text else False

        if not has_keywords:
            return {
                "risk_name": "LIQUIDATED_DAMAGES",
                "severity": RiskSeverity.NONE,
                "score": 0.0,
                "evidence": "No liquidated damages or delay penalty clauses found in text.",
                "recommendation": None
            }

        percentage = self._find_percentage_near_keywords(raw_text, keywords)
        rec = "Carefully review execution timelines and negotiate a lower maximum cap on liquidated damages if possible."

        if percentage is not None:
            if percentage > 10.0:
                severity = RiskSeverity.HIGH
                score = 8.5
                evidence = f"Liquidated damages maximum cap of {percentage}% exceeds the high risk threshold of 10%."
            elif percentage >= 5.0:
                severity = RiskSeverity.MEDIUM
                score = 5.0
                evidence = f"Liquidated damages maximum cap of {percentage}% is within the medium risk threshold (5% - 10%)."
            else:
                severity = RiskSeverity.LOW
                score = 2.0
                evidence = f"Liquidated damages maximum cap of {percentage}% is within the low risk threshold (< 5%)."
        else:
            # Keywords found, but no percentage could be parsed. Default to Medium.
            severity = RiskSeverity.MEDIUM
            score = 5.0
            evidence = "Liquidated damages or late delivery penalty clauses detected, but maximum cap percentage was not found."

        return {
            "risk_name": "LIQUIDATED_DAMAGES",
            "severity": severity,
            "score": score,
            "evidence": evidence,
            "recommendation": rec
        }

    def evaluate_oem_dependency(self, raw_text: str) -> Dict[str, Any]:
        """Checks for OEM dependency/Manufacturer's Authorization Form requirements."""
        keywords = [
            "OEM authorization",
            "MAF",
            "Manufacturer's Authorization",
            "OEM Partner",
            "OEM Certification",
            "Manufacturer Authorization Form"
        ]

        has_keywords = any(kw.lower() in raw_text.lower() for kw in keywords) if raw_text else False

        if has_keywords:
            # Find snippet for evidence
            evidence = "OEM authorization required. Found matching keywords indicating OEM dependence."
            # Search for which keyword matched to provide a better evidence string
            for kw in keywords:
                if raw_text and kw.lower() in raw_text.lower():
                    evidence = f"OEM dependency detected: found '{kw}' in the specifications."
                    break

            return {
                "risk_name": "OEM_DEPENDENCY",
                "severity": RiskSeverity.MEDIUM,
                "score": 5.0,
                "evidence": evidence,
                "recommendation": "Establish early contact with OEMs (e.g. Cisco, Juniper) to secure Manufacturer Authorization Forms (MAF) before bid submission."
            }
        else:
            return {
                "risk_name": "OEM_DEPENDENCY",
                "severity": RiskSeverity.NONE,
                "score": 0.0,
                "evidence": "No OEM authorization or MAF requirements detected.",
                "recommendation": None
            }

    def evaluate_short_completion_time(
        self, completion_period: str, tender_value: Optional[Decimal], raw_text: str
    ) -> Dict[str, Any]:
        """Checks if the project completion period is excessively short."""
        days = self._parse_completion_period_days(completion_period)
        
        # Check tightness keywords
        tightness_keywords = [
            "tight schedule",
            "stringent timeline",
            "urgent completion",
            "rapid deployment",
            "tight timeline"
        ]
        has_tightness_keywords = (
            any(kw.lower() in raw_text.lower() for kw in tightness_keywords)
            if raw_text
            else False
        )

        rec = "Propose a phased execution plan or request a pre-bid timeline extension."

        if days is not None:
            # High risk: less than 3 months (90 days) AND tender value > 50 Lakhs (5,000,000)
            if days < 90 and tender_value is not None and tender_value > Decimal("5000000"):
                return {
                    "risk_name": "SHORT_COMPLETION_TIME",
                    "severity": RiskSeverity.HIGH,
                    "score": 8.5,
                    "evidence": f"Completion period is very short ({days} days) for a high-value tender ({tender_value:,.2f}).",
                    "recommendation": rec
                }
            # Medium risk: less than 6 months (180 days)
            elif days < 180:
                return {
                    "risk_name": "SHORT_COMPLETION_TIME",
                    "severity": RiskSeverity.MEDIUM,
                    "score": 5.0,
                    "evidence": f"Completion period of {days} days is within the medium risk threshold (< 180 days).",
                    "recommendation": rec
                }

        # If keywords are found but numeric thresholds did not trigger High/Medium
        if has_tightness_keywords:
            return {
                "risk_name": "SHORT_COMPLETION_TIME",
                "severity": RiskSeverity.LOW,
                "score": 2.0,
                "evidence": "Tightness/urgency clauses detected in the text, but numeric completion period is standard.",
                "recommendation": rec
            }

        return {
            "risk_name": "SHORT_COMPLETION_TIME",
            "severity": RiskSeverity.NONE,
            "score": 0.0,
            "evidence": "Completion period is standard and no tightness keywords were detected.",
            "recommendation": None
        }

    def evaluate_emd(self, emd: Optional[Decimal], tender_value: Optional[Decimal], raw_text: str) -> Dict[str, Any]:
        """Checks for High EMD (Earnest Money Deposit) requirements."""
        rec = "Utilize EMD exemption options (like MSME registration) or prepare liquid funds."

        if emd is not None and tender_value is not None and tender_value > 0:
            percentage = float((emd / tender_value) * Decimal("100"))
            if percentage > 5.0:
                return {
                    "risk_name": "HIGH_EMD",
                    "severity": RiskSeverity.HIGH,
                    "score": 8.5,
                    "evidence": f"EMD value ({emd:,.2f}) is {percentage:.2f}% of the tender value, which exceeds the high threshold of 5%.",
                    "recommendation": rec
                }
            elif percentage >= 2.0:
                return {
                    "risk_name": "HIGH_EMD",
                    "severity": RiskSeverity.MEDIUM,
                    "score": 5.0,
                    "evidence": f"EMD value ({emd:,.2f}) is {percentage:.2f}% of the tender value (2% - 5% threshold).",
                    "recommendation": rec
                }
            else:
                return {
                    "risk_name": "HIGH_EMD",
                    "severity": RiskSeverity.LOW,
                    "score": 2.0,
                    "evidence": f"EMD value ({emd:,.2f}) is {percentage:.2f}% of the tender value, which is low (< 2%).",
                    "recommendation": rec
                }

        # Fallback keyword checks if numeric metadata is missing
        emd_keywords = ["EMD", "Earnest Money Deposit", "Bid Security"]
        has_keywords = any(kw.lower() in raw_text.lower() for kw in emd_keywords) if raw_text else False

        if has_keywords:
            return {
                "risk_name": "HIGH_EMD",
                "severity": RiskSeverity.LOW,
                "score": 2.0,
                "evidence": "EMD or Bid Security clauses are present in the text, but specific EMD/Tender values are missing.",
                "recommendation": rec
            }

        return {
            "risk_name": "HIGH_EMD",
            "severity": RiskSeverity.NONE,
            "score": 0.0,
            "evidence": "No EMD requirements or clauses found.",
            "recommendation": None
        }

    def evaluate_special_clauses(self, raw_text: str) -> Dict[str, Any]:
        """Checks for restrictive/arbitration special clauses."""
        if not raw_text:
            return {
                "risk_name": "SPECIAL_CLAUSES",
                "severity": RiskSeverity.NONE,
                "score": 0.0,
                "evidence": "No raw text available for special clause analysis.",
                "recommendation": None
            }

        jv_restrictions = [
            "Joint Venture (JV) is not allowed",
            "JV partners not eligible",
            "no joint venture",
            "JV is barred",
            "joint venture is not allowed",
            "JV not permitted",
            "JV shall not be permitted"
        ]
        
        discretion_keywords = [
            "sole discretion of the authority",
            "sole discretion of the purchaser",
            "discretion of the employer"
        ]

        arbitration_keywords = [
            "Arbitration",
            "dispute resolution",
            "governing law",
            "settlement of disputes"
        ]

        has_jv_restrictions = any(kw.lower() in raw_text.lower() for kw in jv_restrictions)
        has_discretion = any(kw.lower() in raw_text.lower() for kw in discretion_keywords)
        has_arbitration = any(kw.lower() in raw_text.lower() for kw in arbitration_keywords)

        rec = "Involve legal counsel to review arbitration clauses and verify JV eligibility criteria."

        if has_jv_restrictions or has_discretion:
            evidence_parts = []
            if has_jv_restrictions:
                evidence_parts.append("JV is not allowed / joint venture restricted")
            if has_discretion:
                evidence_parts.append("arbitrary authority discretion")
            
            return {
                "risk_name": "SPECIAL_CLAUSES",
                "severity": RiskSeverity.HIGH,
                "score": 8.5,
                "evidence": f"High risk special clause(s) found: {', '.join(evidence_parts)}.",
                "recommendation": rec
            }
        elif has_arbitration:
            return {
                "risk_name": "SPECIAL_CLAUSES",
                "severity": RiskSeverity.MEDIUM,
                "score": 5.0,
                "evidence": "Dispute resolution/arbitration clause found.",
                "recommendation": rec
            }

        return {
            "risk_name": "SPECIAL_CLAUSES",
            "severity": RiskSeverity.NONE,
            "score": 0.0,
            "evidence": "No restrictive special clauses or arbitration clauses detected.",
            "recommendation": None
        }

    def evaluate_all(
        self, raw_text: str, completion_period: str, emd: Optional[Decimal], tender_value: Optional[Decimal]
    ) -> List[Dict[str, Any]]:
        """Evaluates all 6 risk areas and returns a list of results."""
        return [
            self.evaluate_performance_guarantee(raw_text),
            self.evaluate_liquidated_damages(raw_text),
            self.evaluate_oem_dependency(raw_text),
            self.evaluate_short_completion_time(completion_period, tender_value, raw_text),
            self.evaluate_emd(emd, tender_value, raw_text),
            self.evaluate_special_clauses(raw_text),
        ]
