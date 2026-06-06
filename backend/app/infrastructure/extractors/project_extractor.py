import re
import logging
from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple

from app.domain.repositories import IProjectExtractor

logger = logging.getLogger(__name__)


class RuleBasedProjectExtractor(IProjectExtractor):
    """Regex-based project credential extraction engine."""

    def __init__(self):
        # We compile regex patterns for each field
        self._patterns_project_name: List[re.Pattern] = [
            re.compile(r"(?i)(?:Name\s*of\s*work|Project\s*Name|Award\s*of\s*work\s*for)\s*[:\-–]?\s*([^\n\r]+)"),
            re.compile(r"(?i)(?:Work\s*Name|Description\s*of\s*work)\s*[:\-–]?\s*([^\n\r]+)"),
            re.compile(r"(?i)^Subject\s*[:\-–]?\s*([^\n\r]+)", re.MULTILINE),
        ]

        self._patterns_client: List[re.Pattern] = [
            re.compile(r"(?i)(?:Client|Customer|Employer|Organization|Issued\s*by)\s*[:\-–]?\s*([^\n\r]{3,100})"),
        ]

        # Standard suffixes to look for in raw text lines for client fallback
        self._client_suffixes = [
            r"Railways", r"Metro", r"Limited", r"Corporation", 
            r"Pvt\.\s*Ltd\.", r"Ltd\.", r"Government\s*of\s*India", 
            r"Govt\.\s*of\s*India", r"Municipal\s*Corporation", r"Authority"
        ]

        self._patterns_project_value: List[re.Pattern] = [
            re.compile(r"(?i)(?:Value\s*of\s*Work|Contract\s*Value|Total\s*Value|Award\s*Value|Invoiced\s*Amount|Project\s*Value)[^\n]*?(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"),
            re.compile(r"(?i)(?:Amount|Price|Value)\s*[:\-–]?\s*(?:Rs\.?|INR)?\s*(-?[0-9,]+(?:\.[0-9]{2})?)"),
        ]

        self._patterns_completion_date: List[re.Pattern] = [
            re.compile(r"(?i)(?:Completion\s*Date|Date\s*of\s*Completion|Completed\s*on|Invoice\s*Date)[^\n]*?([0-9]{1,2}[/\.\-][0-9]{1,2}[/\.\-][0-9]{2,4})"),
            re.compile(r"(?i)(?:Date|Dated)\s*[:\-–]?\s*([0-9]{1,2}[/\.\-][0-9]{1,2}[/\.\-][0-9]{2,4})"),
        ]

        self._patterns_location: List[re.Pattern] = [
            re.compile(r"(?i)(?:Location|Site|Place\s*of\s*execution|Executed\s*at|Venue)\s*[:\-–]?\s*([A-Za-z0-9\s,\(\)\-]{3,100})"),
        ]

        # Classification patterns for domains with word boundaries \b
        self._domain_classifications = [
            ("OFC", re.compile(r"(?i)\b(OFC|optical\s+fiber|fiber\s+optic)\b")),
            ("Networking", re.compile(r"(?i)\b(switch|router|lan|network|networking|cisco|ethernet)\b")),
            ("Civil Work", re.compile(r"(?i)\b(civil|excavation|foundation|concrete|building|reinforcement|earthwork|road|bridge|structure)\b")),
            ("Electrical Work", re.compile(r"(?i)\b(electrical|earthing|wiring|mcb|switchgear|power\s+supply|substation|cabling|lighting)\b")),
        ]

    def _clean_string(self, val: Optional[str]) -> str:
        if not val:
            return "UNKNOWN"
        cleaned = re.sub(r"\s+", " ", val).strip()
        # Limit length to 255 chars
        if len(cleaned) > 255:
            cleaned = cleaned[:252] + "..."
        return cleaned if cleaned else "UNKNOWN"

    def _clean_decimal(self, val: Optional[str]) -> Decimal:
        if not val:
            return Decimal("0.00")
        try:
            is_neg = "-" in val
            cleaned = re.sub(r"[^\d.]", "", val)
            dec = Decimal(cleaned)
            return -dec if is_neg else dec
        except Exception as e:
            logger.warning(f"Error parsing decimal project value '{val}': {e}", exc_info=True)
            return Decimal("0.00")


    def _clean_date(self, val: Optional[str]) -> Optional[date]:
        if not val:
            return None
        cleaned = val.strip().replace(" ", "")
        for fmt in ("%d/%m/%Y", "%d.%m.%Y", "%d-%m-%Y", "%Y-%m-%d", "%d/%m/%y", "%d.%m.%y", "%d-%m-%y"):
            try:
                return datetime.strptime(cleaned, fmt).date()
            except ValueError:
                continue
        logger.warning(f"Failed to parse date string '{val}' against known formats")
        return None

    def _extract_field(self, text: str, patterns: List[re.Pattern]) -> Optional[str]:
        for pattern in patterns:
            match = pattern.search(text)
            if match:
                return match.group(1).strip()
        return None

    def _fallback_client(self, text: str) -> Optional[str]:
        # Search line-by-line for lines containing client suffixes
        for line in text.splitlines():
            line_str = line.strip()
            for suffix in self._client_suffixes:
                if re.search(r"(?i)\b" + suffix + r"\b", line_str):
                    # Clean up prefix noise if line contains standard terms
                    # e.g., "Issued by: Northern Railway" -> "Northern Railway"
                    cleaned = re.sub(r"(?i)^.*(?:issued\s*by|client|customer|employer|authority|to)\s*[:\-–]?\s*", "", line_str)
                    if len(cleaned) > 3 and len(cleaned) < 100:
                        return cleaned
        return None

    def _classify_domain(self, text: str) -> str:
        # Check domain classifications against the text
        for domain, pattern in self._domain_classifications:
            if pattern.search(text):
                return domain
        return "Other"

    async def extract_project_details(self, raw_text: str, doc_type: str) -> dict:
        """Parses raw text to extract project details."""
        logger.info(f"Extracting project credentials from document type: {doc_type}")
        
        # 1. Project Name
        proj_name_raw = self._extract_field(raw_text, self._patterns_project_name)
        project_name = self._clean_string(proj_name_raw)

        # 2. Client
        client_raw = self._extract_field(raw_text, self._patterns_client)
        if not client_raw:
            client_raw = self._fallback_client(raw_text)
        client = self._clean_string(client_raw)

        # 3. Project Value
        val_raw = self._extract_field(raw_text, self._patterns_project_value)
        project_value = self._clean_decimal(val_raw)

        # 4. Completion Date
        date_raw = self._extract_field(raw_text, self._patterns_completion_date)
        completion_date = self._clean_date(date_raw)

        # 5. Location
        loc_raw = self._extract_field(raw_text, self._patterns_location)
        location = self._clean_string(loc_raw)

        # 6. Domain
        # We classify based on project_name first, then raw_text
        domain = self._classify_domain(project_name)
        if domain == "Other":
            domain = self._classify_domain(raw_text)

        extracted = {
            "project_name": project_name,
            "client": client,
            "project_value": project_value,
            "completion_date": completion_date,
            "domain": domain,
            "location": location,
            "document_type": doc_type,
        }

        logger.info(f"Extracted details: {extracted}")
        return extracted
