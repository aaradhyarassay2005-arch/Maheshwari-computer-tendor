import re
from decimal import Decimal
from datetime import datetime, date
from typing import Dict, Any, List, Tuple, Optional
from app.domain.repositories import IMetadataExtractionProvider


class RuleBasedMetadataExtractor(IMetadataExtractionProvider):
    """Regex-based metadata extraction engine for tender documents."""

    def __init__(self):
        # We compile regex patterns for each field along with their respective confidences.
        # Order matters: first matched pattern wins.

        self._patterns_tender_number: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)Tender\s*(?:Notice\s*|Reference\s*)?No\.?\s*[:\-–]?\s*([A-Za-z0-9\-\/._]{5,50})"), 1.0),
            (re.compile(r"(?i)NIT\s*(?:Notice\s*)?No\.?\s*[:\-–]?\s*([A-Za-z0-9\-\/._]{5,50})"), 0.9),
            (re.compile(r"(?i)Tender\s*Ref(?:erence)?\s*No\.?\s*[:\-–]?\s*([A-Za-z0-9\-\/._]{5,50})"), 0.9),
            (re.compile(r"(?i)Ref\.?\s*No(?:tice)?\s*[:\-–]?\s*([A-Za-z0-9\-\/._]{5,50})"), 0.6),
        ]

        self._patterns_department: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)Department\s*[:\-–]\s*([^\n]{3,100})"), 1.0),
            (re.compile(r"(?i)Ministry\s*of\s*([^\n]{3,100})"), 0.9),
            (re.compile(r"(?i)Office\s*of\s*the\s*([^\n]{3,100})"), 0.8),
            (re.compile(r"(?i)Authority\s*[:\-–]\s*([^\n]{3,100})"), 0.8),
        ]

        self._patterns_tender_value: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Advertised\s*Value|Tender\s*Value|Estimated\s*Cost|Approx\.?\s*Cost)[^\n]*?(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"), 1.0),
            (re.compile(r"(?i)Value\s*of\s*Work[^\n]*?(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"), 0.9),
        ]

        self._patterns_emd: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:EMD|Earnest\s*Money(?:\s*Deposit)?)[^\n]*?(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"), 1.0),
            (re.compile(r"(?i)Earnest\s*Money\s*[:\-–]?[^\n]*?(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"), 0.9),
        ]

        self._patterns_closing_date: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Closing\s*Date(?:\s*&\s*Time)?|Due\s*Date|Bid\s*Submission\s*End\s*Date)[^\n]*?([0-9]{1,2}[/\.\-][0-9]{1,2}[/\.\-][0-9]{2,4})"), 1.0),
            (re.compile(r"(?i)Date\s*of\s*Closing[^\n]*?([0-9]{1,2}[/\.\-][0-9]{1,2}[/\.\-][0-9]{2,4})"), 0.9),
        ]

        self._patterns_completion_period: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Completion\s*Period|Period\s*of\s*Completion|Period\s*of\s*Work|Contract\s*Period)[^\n]*?([0-9]+\s*(?:Months|Days|Weeks|Year|Years))"), 1.0),
            (re.compile(r"(?i)Time\s*Allowed[^\n]*?([0-9]+\s*(?:Months|Days|Weeks|Year|Years))"), 0.9),
        ]

        self._patterns_tender_type: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Tender\s*Type|Type\s*of\s*Tender)\s*[:\-–]?\s*(Open|Limited|Single|Global|Advertised|E-Tender)"), 1.0),
            (re.compile(r"(?i)\b(Open|Limited|Single|Global|Advertised\s*Tender|E-Tender)\s*Tender\b"), 0.8),
        ]

        self._patterns_zone: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(Central|Eastern|Northern|Southern|Western|South\s*Central|East\s*Central|North\s*Central|South\s*Eastern|South\s*Western|North\s*Western|West\s*Central|East\s*Coast|South\s*East\s*Central|Northeast\s*Frontier|Northeastern)\s*Railway"), 1.0),
            (re.compile(r"(?i)(?:Railway\s*Zone|Zone)\s*[:\-–]?\s*([^\n]{3,50})"), 0.8),
        ]

        self._patterns_bid_system: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Bid\s*System|System\s*of\s*Bidding|Bidding\s*System)\s*[:\-–]?\s*([^\n]{3,50})"), 1.0),
            (re.compile(r"(?i)(Single\s*Packet|Two\s*Packet|One\s*Packet|Single\s*Stage|Two\s*Stage)\s*System"), 0.9),
        ]

        self._patterns_contract_type: List[Tuple[re.Pattern, float]] = [
            (re.compile(r"(?i)(?:Contract\s*Type|Type\s*of\s*Contract)\s*[:\-–]?\s*(Works|Goods|Services|Supply|Piecework|Lump\s*sum)"), 1.0),
            (re.compile(r"(?i)\bType\s*of\s*Work\s*[:\-–]?\s*(Works|Goods|Services|Supply|Piecework|Lump\s*sum)"), 0.8),
        ]

    def _clean_string(self, val: str) -> str:
        if not val:
            return "UNKNOWN"
        cleaned = re.sub(r"\s+", " ", val).strip()
        return cleaned if cleaned else "UNKNOWN"

    def _clean_decimal(self, val: str) -> Optional[Decimal]:
        if not val:
            return None
        try:
            is_neg = "-" in val
            # Strip formatting like commas, currency prefixes, spaces
            cleaned = re.sub(r"[^\d.]", "", val)
            dec = Decimal(cleaned)
            return -dec if is_neg else dec
        except Exception:
            return None

    def _clean_date(self, val: str) -> Optional[date]:
        if not val:
            return None
        # Try multiple formats
        cleaned = val.strip().replace(" ", "")
        for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%y", "%d-%m-%y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        return None

    def _extract_field(self, text: str, patterns: List[Tuple[re.Pattern, float]]) -> Tuple[Optional[str], float]:
        for pattern, confidence in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip(), confidence
        return None, 0.0

    async def extract(self, raw_text: str) -> dict:
        """Runs the rule-based extraction matching against the provided text."""
        result: Dict[str, Any] = {}

        # 1. Tender Number
        val, conf = self._extract_field(raw_text, self._patterns_tender_number)
        result["tender_number"] = self._clean_string(val)
        result["tender_number_confidence"] = conf

        # 2. Department
        val, conf = self._extract_field(raw_text, self._patterns_department)
        result["department"] = self._clean_string(val)
        result["department_confidence"] = conf

        # 3. Tender Value
        val, conf = self._extract_field(raw_text, self._patterns_tender_value)
        result["tender_value"] = self._clean_decimal(val)
        result["tender_value_confidence"] = conf if result["tender_value"] is not None else 0.0

        # 4. EMD
        val, conf = self._extract_field(raw_text, self._patterns_emd)
        result["emd"] = self._clean_decimal(val)
        result["emd_confidence"] = conf if result["emd"] is not None else 0.0

        # 5. Closing Date
        val, conf = self._extract_field(raw_text, self._patterns_closing_date)
        result["closing_date"] = self._clean_date(val)
        result["closing_date_confidence"] = conf if result["closing_date"] is not None else 0.0

        # 6. Completion Period
        val, conf = self._extract_field(raw_text, self._patterns_completion_period)
        result["completion_period"] = self._clean_string(val)
        result["completion_period_confidence"] = conf

        # 7. Tender Type
        val, conf = self._extract_field(raw_text, self._patterns_tender_type)
        result["tender_type"] = self._clean_string(val)
        result["tender_type_confidence"] = conf

        # 8. Zone
        val, conf = self._extract_field(raw_text, self._patterns_zone)
        # Check if first group capture matched (e.g. from Northern Railway) and append "Railway" if it matched a raw zone name
        if val and conf == 1.0:
            val = val.title()
            if not val.lower().endswith("railway"):
                val = f"{val} Railway"
        result["zone"] = self._clean_string(val)
        result["zone_confidence"] = conf

        # 9. Bid System
        val, conf = self._extract_field(raw_text, self._patterns_bid_system)
        result["bid_system"] = self._clean_string(val)
        result["bid_system_confidence"] = conf

        # 10. Contract Type
        val, conf = self._extract_field(raw_text, self._patterns_contract_type)
        result["contract_type"] = self._clean_string(val)
        result["contract_type_confidence"] = conf

        # Include raw_text
        result["raw_text"] = raw_text

        return result
