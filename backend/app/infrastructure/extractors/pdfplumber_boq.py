import re
import asyncio
from typing import List, Dict, Any, Optional
from decimal import Decimal
import structlog

from app.domain.repositories import IBOQExtractionProvider

logger = structlog.get_logger("app.extraction.pdfplumber")


class PdfPlumberBOQExtractor(IBOQExtractionProvider):
    """Pdfplumber-based table extraction engine for BOQs."""

    async def extract_boq(self, file_path: str) -> List[dict]:
        # Wrap the blocking pdfplumber extraction in an executor thread
        return await asyncio.to_thread(self._extract_sync, file_path)

    def _extract_sync(self, file_path: str) -> List[dict]:
        logger.info("Starting pdfplumber BOQ extraction", file_path=file_path)
        try:
            import pdfplumber
        except ImportError:
            logger.error("pdfplumber is not installed")
            return []

        items = []
        current_schedule = "UNKNOWN"
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages):
                    # We can also search for schedule names in the page text
                    text = page.extract_text() or ""
                    schedule_matches = re.findall(r"(?i)(Schedule\s*[-–]?\s*[A-Z0-9]+)", text)
                    if schedule_matches:
                        # Take the last schedule name mentioned before tables
                        current_schedule = schedule_matches[-1]

                    tables = page.extract_tables()
                    for table in tables:
                        if not table or len(table) < 2:
                            continue
                        
                        parsed_table_items = self._parse_table(table, current_schedule)
                        items.extend(parsed_table_items)
                        
            # Merge fragments/continuations
            merged_items = self._merge_continuations(items)
            logger.info("pdfplumber BOQ extraction finished", file_path=file_path, count=len(merged_items))
            return merged_items
        except Exception as e:
            logger.error("pdfplumber BOQ extraction failed", error=str(e), file_path=file_path)
            return []

    def _parse_table(self, table: List[List[Optional[str]]], default_schedule: str) -> List[dict]:
        # Clean cells
        cleaned_table = []
        for row in table:
            cleaned_row = []
            for cell in row:
                cleaned_row.append(cell.strip() if cell else "")
            # Only keep rows that are not entirely empty
            if any(cleaned_row):
                cleaned_table.append(cleaned_row)

        if not cleaned_table:
            return []

        # Find headers
        col_mapping = self._identify_columns(cleaned_table[:3])
        if not col_mapping or "item_name" not in col_mapping.values():
            # Fallback based on column count
            num_cols = len(cleaned_table[0])
            if num_cols == 6:
                col_mapping = {0: "item_code", 1: "item_name", 2: "quantity", 3: "unit", 4: "unit_rate", 5: "amount"}
            elif num_cols == 7:
                col_mapping = {0: "item_code", 1: "item_name", 2: "quantity", 3: "unit", 4: "unit_rate", 5: "amount", 6: "schedule_name"}
            else:
                # If we cannot map, make a generic guess
                col_mapping = {}
                for idx in range(num_cols):
                    if idx == 0: col_mapping[idx] = "item_code"
                    elif idx == 1: col_mapping[idx] = "item_name"
                    elif idx == 2: col_mapping[idx] = "quantity"
                    elif idx == 3: col_mapping[idx] = "unit"
                    elif idx == 4: col_mapping[idx] = "unit_rate"
                    elif idx == 5: col_mapping[idx] = "amount"

        rows_to_process = []
        # Identify header rows to skip
        header_indices = set()
        for idx, row in enumerate(cleaned_table[:3]):
            # If row matches column names, skip it
            row_joined = " ".join(row).lower()
            if any(keyword in row_joined for keyword in ["description", "particulars", "quantity", "rate", "amount"]):
                header_indices.add(idx)

        for idx, row in enumerate(cleaned_table):
            if idx in header_indices:
                continue
            
            # Build item dict
            item = {
                "item_code": "",
                "item_name": "",
                "quantity": None,
                "unit": "UNKNOWN",
                "unit_rate": None,
                "amount": None,
                "schedule_name": default_schedule,
            }
            
            for col_idx, field in col_mapping.items():
                if col_idx < len(row):
                    val = row[col_idx].strip()
                    if field in ["item_code", "item_name", "unit", "schedule_name"]:
                        if val:
                            item[field] = val
                    elif field in ["quantity", "unit_rate", "amount"]:
                        if val:
                            item[field] = val  # Keep raw for validation in service

            # Skip empty rows or section headers that span across columns
            if not item["item_name"] and not item["item_code"]:
                continue
                
            # If item_name has something like "Schedule" and no other values, update default schedule
            if item["item_name"] and not item["item_code"] and not item["quantity"] and not item["amount"]:
                sched_match = re.search(r"(?i)(Schedule\s*[-–]?\s*[A-Z0-9]+)", item["item_name"])
                if sched_match:
                    default_schedule = sched_match.group(1)
                    continue

            rows_to_process.append(item)

        return rows_to_process

    def _identify_columns(self, sample_rows: List[List[str]]) -> Dict[int, str]:
        mapping = {}
        for row in sample_rows:
            for idx, cell in enumerate(row):
                val = cell.lower().strip()
                if not val:
                    continue
                if "item" in val or "sl" in val or "s.no" in val or "sno" in val or "code" in val:
                    if "code" in val:
                        mapping[idx] = "item_code"
                    elif idx not in mapping:
                        mapping[idx] = "item_code"
                elif "description" in val or "particulars" in val or "specification" in val or "item of work" in val:
                    mapping[idx] = "item_name"
                elif "qty" in val or "quantity" in val:
                    mapping[idx] = "quantity"
                elif "unit" in val and "rate" not in val:
                    mapping[idx] = "unit"
                elif "rate" in val or "unit rate" in val or "price" in val:
                    mapping[idx] = "unit_rate"
                elif "amount" in val or "total" in val or "value" in val:
                    mapping[idx] = "amount"
                elif "schedule" in val:
                    mapping[idx] = "schedule_name"
        return mapping

    def _merge_continuations(self, items: List[dict]) -> List[dict]:
        if not items:
            return []

        merged = []
        for item in items:
            # A row is a continuation if item_code is missing/empty, quantity and rate/amount are missing,
            # but item_name is populated, AND we already have a previous item in merged.
            is_continuation = (
                not item["item_code"]
                and not item["quantity"]
                and not item["unit_rate"]
                and not item["amount"]
                and item["item_name"]
                and merged
            )
            
            if is_continuation:
                # Merge with previous item name
                prev = merged[-1]
                prev["item_name"] = f"{prev['item_name']} {item['item_name']}".strip()
            else:
                merged.append(item)
                
        return merged
