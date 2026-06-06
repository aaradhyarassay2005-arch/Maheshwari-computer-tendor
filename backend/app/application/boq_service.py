import re
import structlog
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4
from typing import List, Optional, Any
from pydantic import UUID4

from app.domain.models import BOQItem, TenderDocumentStatus
from app.domain.repositories import (
    ITenderRepository,
    ITenderDocumentRepository,
    IBOQItemRepository,
    IBOQExtractionProvider,
)

logger = structlog.get_logger("app.boq")


class TenderBOQExtractionService:
    def __init__(
        self,
        tender_repo: ITenderRepository,
        doc_repo: ITenderDocumentRepository,
        boq_repo: IBOQItemRepository,
        primary_extractor: IBOQExtractionProvider,
        fallback_extractor: IBOQExtractionProvider,
    ):
        self.tender_repo = tender_repo
        self.doc_repo = doc_repo
        self.boq_repo = boq_repo
        self.primary_extractor = primary_extractor
        self.fallback_extractor = fallback_extractor

    async def extract_boq(self, tender_id: UUID4) -> List[BOQItem]:
        doc = await self.doc_repo.get_by_tender_id(tender_id)
        if not doc or doc.status != TenderDocumentStatus.DOWNLOADED:
            logger.error("No downloaded document found for BOQ extraction", tender_id=str(tender_id))
            return []

        file_path = doc.file_path
        if not file_path:
            logger.error("Document file path is missing", tender_id=str(tender_id))
            return []

        logger.info("Attempting primary BOQ extraction (Camelot)", tender_id=str(tender_id), path=file_path)
        raw_items = []
        try:
            raw_items = await self.primary_extractor.extract_boq(file_path)
        except Exception as e:
            logger.warn("Primary BOQ extractor failed, falling back", error=str(e), tender_id=str(tender_id))

        if not raw_items:
            logger.info("Primary BOQ extractor returned no items, running fallback (pdfplumber)", tender_id=str(tender_id))
            try:
                raw_items = await self.fallback_extractor.extract_boq(file_path)
            except Exception as e:
                logger.error("Fallback BOQ extractor failed", error=str(e), tender_id=str(tender_id))

        if not raw_items:
            logger.error("All BOQ extraction strategies failed or returned no items", tender_id=str(tender_id))
            return []

        logger.info("Normalizing and validating extracted BOQ items", count=len(raw_items), tender_id=str(tender_id))
        
        normalized_items = []
        now = datetime.now(timezone.utc)
        
        for raw in raw_items:
            item_code = raw.get("item_code", "UNKNOWN") or "UNKNOWN"
            item_name = raw.get("item_name", "UNKNOWN") or "UNKNOWN"
            raw_qty = raw.get("quantity")
            raw_rate = raw.get("unit_rate")
            raw_amt = raw.get("amount")
            raw_unit = raw.get("unit", "UNKNOWN") or "UNKNOWN"
            schedule_name = raw.get("schedule_name", "UNKNOWN") or "UNKNOWN"
            
            qty = self._parse_decimal(raw_qty)
            rate = self._parse_decimal(raw_rate)
            amt = self._parse_decimal(raw_amt)
            
            unit = self._normalize_unit(raw_unit)
            
            # Validation & confidence calculation
            confidence = 1.0
            
            if qty is None or rate is None:
                confidence -= 0.2
            
            if qty is not None and rate is not None and amt is not None:
                expected_amt = qty * rate
                diff = abs(expected_amt - amt)
                if diff > Decimal("1.0"):  # Threshold check
                    confidence -= 0.2
            else:
                if amt is None and qty is not None and rate is not None:
                    amt = qty * rate
                else:
                    confidence -= 0.2
            
            if unit == "UNKNOWN":
                confidence -= 0.1
                
            confidence = max(0.0, min(1.0, confidence))
            
            boq_item = BOQItem(
                id=uuid4(),
                tender_id=tender_id,
                document_id=doc.id,
                item_code=item_code,
                item_name=item_name,
                quantity=qty,
                unit=unit,
                unit_rate=rate,
                amount=amt,
                schedule_name=schedule_name,
                confidence=confidence,
                created_at=now,
                updated_at=now,
            )
            normalized_items.append(boq_item)

        # Purge stale records to avoid duplicates
        logger.info("Clearing old BOQ items and saving new items", tender_id=str(tender_id), count=len(normalized_items))
        await self.boq_repo.delete_by_tender_id(tender_id)
        saved_items = await self.boq_repo.bulk_add(normalized_items)
        
        return saved_items

    def _parse_decimal(self, val: Any) -> Optional[Decimal]:
        if val is None:
            return None
        if isinstance(val, (int, float, Decimal)):
            return Decimal(str(val))
        try:
            # Strip currency signs, commas, and other formatting
            cleaned = re.sub(r"[^\d.-]", "", str(val))
            if not cleaned:
                return None
            return Decimal(cleaned)
        except Exception:
            return None

    def _normalize_unit(self, unit: str) -> str:
        if not unit:
            return "UNKNOWN"
        val = unit.lower().strip()
        
        if val in ["nos", "nos.", "no.", "numbers", "number", "no"]:
            return "Nos"
        if val in ["sqm", "sq.m", "sq.mtr", "sq. mtr", "sq mtr", "square meter", "square meters"]:
            return "Sqm"
        if val in ["cum", "cu.m", "cu.mtr", "cu. mtr", "cu mtr", "cubic meter", "cubic meters"]:
            return "Cum"
        if val in ["mt", "metric ton", "metric tonnes", "metric tonne", "tonnes", "tonne", "ton", "tons"]:
            return "MT"
        if val in ["kg", "kgs", "kilogram", "kilograms"]:
            return "Kg"
        if val in ["m", "mtr", "mtrs", "meter", "meters", "running meter", "running meters", "rmt"]:
            return "Mtr"
            
        return unit.strip().title()
