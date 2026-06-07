import io
import re
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import uuid4
import structlog
import pandas as pd
from pydantic import UUID4

from app.domain.models import Tender, TenderStatus, TenderDocument, TenderDocumentStatus, TenderMetadata
from app.domain.repositories import ITenderRepository, ITenderDocumentRepository, ITenderMetadataRepository
from app.domain.exceptions import TenderNotFoundException, TenderAlreadyExistsException
from app.schemas.imports import ExcelImportResponse

logger = structlog.get_logger("app.services")


def is_valid_url(url: Optional[str]) -> bool:
    """Validates URL syntax integrity."""
    if not url:
        return False
    from urllib.parse import urlparse
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


class TenderService:
    def __init__(
        self,
        tender_repo: ITenderRepository,
        doc_repo: ITenderDocumentRepository,
        metadata_repo: Optional[ITenderMetadataRepository] = None
    ):
        self.tender_repo = tender_repo
        self.doc_repo = doc_repo
        self.metadata_repo = metadata_repo

    async def create_tender(
        self,
        tender_number: str,
        department: str,
        source_url: str,
        tender_value: Optional[Decimal] = None,
        closing_date: Optional[date] = None,
    ) -> Tender:
        # Check uniqueness
        existing = await self.tender_repo.get_by_tender_number(tender_number)
        if existing:
            raise TenderAlreadyExistsException(tender_number)

        now = datetime.now(timezone.utc)
        tender = Tender(
            id=uuid4(),
            tender_number=tender_number,
            department=department,
            source_url=source_url,
            tender_value=tender_value,
            closing_date=closing_date,
            status=TenderStatus.NEW,
            created_at=now,
            updated_at=now,
        )
        logger.info("Creating new tender", tender_number=tender_number, department=department)
        saved_tender = await self.tender_repo.add(tender)

        if source_url:
            doc = TenderDocument(
                id=uuid4(),
                tender_id=saved_tender.id,
                file_size=0,
                status=TenderDocumentStatus.PENDING,
                attempts=0,
                created_at=now,
                updated_at=now,
            )
            await self.doc_repo.add(doc)

        return saved_tender

    async def get_tender(self, id: UUID4) -> Optional[Tender]:
        return await self.tender_repo.get_by_id(id)

    async def list_tenders(
        self, skip: int = 0, limit: int = 10, search: Optional[str] = None
    ) -> Tuple[List[Tender], int]:
        return await self.tender_repo.list(skip=skip, limit=limit, search=search)

    async def update_tender(
        self,
        id: UUID4,
        tender_number: Optional[str] = None,
        department: Optional[str] = None,
        source_url: Optional[str] = None,
        tender_value: Optional[Decimal] = None,
        closing_date: Optional[date] = None,
        status: Optional[TenderStatus] = None,
    ) -> Tender:
        existing = await self.tender_repo.get_by_id(id)
        if not existing:
            raise TenderNotFoundException(str(id))

        # Check conflict on tender_number update
        if tender_number is not None and tender_number != existing.tender_number:
            conflict = await self.tender_repo.get_by_tender_number(tender_number)
            if conflict:
                raise TenderAlreadyExistsException(tender_number)

        now = datetime.now(timezone.utc)
        updated_tender = Tender(
            id=existing.id,
            tender_number=tender_number if tender_number is not None else existing.tender_number,
            department=department if department is not None else existing.department,
            source_url=source_url if source_url is not None else existing.source_url,
            tender_value=tender_value if tender_value is not None else existing.tender_value,
            closing_date=closing_date if closing_date is not None else existing.closing_date,
            status=status if status is not None else existing.status,
            created_at=existing.created_at,
            updated_at=now,
        )
        logger.info("Updating tender", id=str(id), tender_number=updated_tender.tender_number)
        return await self.tender_repo.update(updated_tender)

    async def delete_tender(self, id: UUID4) -> bool:
        logger.info("Deleting tender", id=str(id))
        return await self.tender_repo.delete(id)

    async def import_tenders_from_excel(self, file_content: bytes) -> ExcelImportResponse:
        try:
            # Read using pandas and openpyxl engine
            df = pd.read_excel(io.BytesIO(file_content), engine="openpyxl")
        except Exception as e:
            raise ValueError(f"Invalid Excel format: {str(e)}")

        # Normalise headers to lower case for case-insensitivity
        original_cols = list(df.columns)
        df.columns = [str(col).strip().lower() for col in df.columns]

        # Column mappings (to support original columns and the new master tender spreadsheet format)
        # 1. Tender Number Mapping
        col_tender = None
        for c in ["tender_number", "tender no.", "tender no", "tender_no"]:
            if c in df.columns:
                col_tender = c
                break
        
        # 2. Source URL Mapping
        col_url = None
        for c in ["source_url", "tender link", "tender_link", "tender link"]:
            if c in df.columns:
                col_url = c
                break
        # Fallback: find any column containing 'link' or 'url' in its name
        if not col_url:
            for c in df.columns:
                if "link" in c or "url" in c:
                    col_url = c
                    break

        # 3. Department / Division Mapping
        col_dept = None
        for c in ["department", "division", "location"]:
            if c in df.columns:
                col_dept = c
                break

        # 4. Tender Value Mapping
        col_value = None
        for c in ["tender_value", "value", "loa amount", "amount"]:
            if c in df.columns:
                col_value = c
                break

        # 5. Closing Date Mapping
        col_date = None
        for c in ["closing_date", "date"]:
            if c in df.columns:
                col_date = c
                break

        # 6. EMD Mapping
        col_emd = None
        for c in ["emd", "emd amount"]:
            if c in df.columns:
                col_emd = c
                break

        # 7. Similar Work (Technical Experience) Mapping
        col_similar = None
        for c in ["similar work", "similar_work", "eligibility", "technical requirement"]:
            if c in df.columns:
                col_similar = c
                break

        # Check for required fields
        if not col_tender:
            raise ValueError("Missing required column for Tender Number (e.g. 'TENDER NO.' or 'tender_number')")
        if not col_url:
            raise ValueError("Missing required column for Tender PDF Link (e.g. 'TENDER LINK' or 'source_url')")
        if not col_dept:
            raise ValueError("Missing required column for Department or Division (e.g. 'DIVISION' or 'department')")

        total_rows = 0
        inserted = 0
        duplicates = 0
        failed = 0
        errors = []
        tenders_to_insert = []
        extras_to_insert = []
        seen_numbers = set()
        seen_urls = set()

        # Iterate rows
        for index, row in df.iterrows():
            total_rows += 1
            row_num = int(index) + 2  # Excel row is 1-indexed + header row = index + 2

            # Extract fields
            tender_num_val = row.get(col_tender)
            dept_val = row.get(col_dept)
            url_val = row.get(col_url)
            value_val = row.get(col_value) if col_value else None
            closing_date_val = row.get(col_date) if col_date else None
            emd_val = row.get(col_emd) if col_emd else None
            similar_work_val = row.get(col_similar) if col_similar else None

            # Check required fields are non-empty
            if pd.isna(tender_num_val) or str(tender_num_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": "UNKNOWN", "error": "Missing tender_number"})
                continue
            tender_number = str(tender_num_val).strip()

            if pd.isna(dept_val) or str(dept_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": "Missing department/division"})
                continue
            department = str(dept_val).strip()

            if pd.isna(url_val) or str(url_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": "Missing source_url/tender_link"})
                continue
            source_url = str(url_val).strip()

            # Validate source url structure
            if not is_valid_url(source_url):
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Invalid source_url format: {source_url}"})
                continue

            # Validate tender value
            tender_value = None
            if value_val is not None and not pd.isna(value_val) and str(value_val).strip() != "":
                try:
                    clean_val = str(value_val).replace(",", "").replace("$", "").replace("/-", "").strip()
                    clean_val = re.sub(r'[^\d.]', '', clean_val)
                    if clean_val:
                        tender_value = Decimal(clean_val)
                        if tender_value < 0:
                            raise ValueError("Tender value cannot be negative")
                except Exception as e:
                    failed += 1
                    errors.append({"row": row_num, "tender_number": tender_number, "error": f"Invalid tender_value: {str(e)}"})
                    continue

            # Validate EMD
            emd = None
            if emd_val is not None and not pd.isna(emd_val) and str(emd_val).strip() != "":
                try:
                    clean_val = str(emd_val).replace(",", "").replace("/-", "").strip()
                    clean_val = re.sub(r'[^\d.]', '', clean_val)
                    if clean_val:
                        emd = Decimal(clean_val)
                except Exception:
                    pass

            # Validate closing date
            closing_date = None
            if closing_date_val is not None and not pd.isna(closing_date_val) and str(closing_date_val).strip() != "":
                if isinstance(closing_date_val, datetime):
                    closing_date = closing_date_val.date()
                elif isinstance(closing_date_val, date):
                    closing_date = closing_date_val
                else:
                    try:
                        parsed_dt = datetime.fromisoformat(str(closing_date_val).replace("Z", "+00:00"))
                        closing_date = parsed_dt.date()
                    except Exception:
                        parsed_date = None
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y"):
                            try:
                                parsed_date = datetime.strptime(str(closing_date_val).strip(), fmt).date()
                                break
                            except Exception:
                                continue
                        if parsed_date:
                            closing_date = parsed_date
                        else:
                            failed += 1
                            errors.append({"row": row_num, "tender_number": tender_number, "error": f"Invalid closing_date format: {closing_date_val}"})
                            continue

            # Duplicate Check: Spreadsheet level
            if tender_number in seen_numbers:
                duplicates += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Duplicate tender_number '{tender_number}' inside Excel sheet"})
                continue
            seen_numbers.add(tender_number)

            if source_url in seen_urls:
                duplicates += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Duplicate source_url '{source_url}' inside Excel sheet"})
                continue
            seen_urls.add(source_url)

            # Duplicate Check: Database level
            existing_num = await self.tender_repo.get_by_tender_number(tender_number)
            if existing_num:
                duplicates += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Tender number '{tender_number}' already exists in database"})
                continue

            existing_url = await self.tender_repo.get_by_source_url(source_url)
            if existing_url:
                duplicates += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Source URL '{source_url}' already exists in database"})
                continue

            # Construct Tender model (Set status directly to PARSED so they can work on it immediately!)
            now = datetime.now(timezone.utc)
            tender = Tender(
                id=uuid4(),
                tender_number=tender_number,
                department=department,
                source_url=source_url,
                tender_value=tender_value,
                closing_date=closing_date,
                status=TenderStatus.PARSED,  # Unlock immediately!
                created_at=now,
                updated_at=now
            )
            tenders_to_insert.append(tender)
            
            # Keep track of similar work and EMD for metadata record
            extras_to_insert.append({
                "emd": emd,
                "similar_work": str(similar_work_val).strip() if similar_work_val is not None and not pd.isna(similar_work_val) else None
            })
            inserted += 1

        # Bulk save and metadata initialization
        if tenders_to_insert:
            await self.tender_repo.bulk_add(tenders_to_insert)
            docs_to_insert = []
            metadata_to_insert = []
            
            for t, extra in zip(tenders_to_insert, extras_to_insert):
                doc_id = uuid4()
                # Create doc
                doc = TenderDocument(
                    id=doc_id,
                    tender_id=t.id,
                    file_name=f"{t.tender_number}.pdf",
                    file_size=0,
                    status=TenderDocumentStatus.PENDING,
                    attempts=0,
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                docs_to_insert.append(doc)
                
                # Create metadata
                meta = TenderMetadata(
                    id=uuid4(),
                    tender_id=t.id,
                    document_id=doc_id,
                    tender_number=t.tender_number,
                    tender_number_confidence=1.0,
                    department=t.department,
                    department_confidence=1.0,
                    tender_value=t.tender_value,
                    tender_value_confidence=1.0 if t.tender_value is not None else 0.0,
                    emd=extra["emd"],
                    emd_confidence=1.0 if extra["emd"] is not None else 0.0,
                    closing_date=t.closing_date,
                    closing_date_confidence=1.0 if t.closing_date is not None else 0.0,
                    completion_period="UNKNOWN",
                    completion_period_confidence=0.0,
                    tender_type="UNKNOWN",
                    tender_type_confidence=0.0,
                    zone="UNKNOWN",
                    zone_confidence=0.0,
                    bid_system="UNKNOWN",
                    bid_system_confidence=0.0,
                    contract_type="UNKNOWN",
                    contract_type_confidence=0.0,
                    raw_text=extra["similar_work"], # We put similar work here!
                    created_at=t.created_at,
                    updated_at=t.updated_at,
                )
                metadata_to_insert.append(meta)
                
            if docs_to_insert:
                await self.doc_repo.bulk_add(docs_to_insert)
            if metadata_to_insert and self.metadata_repo:
                for m_item in metadata_to_insert:
                    await self.metadata_repo.add(m_item)

        return ExcelImportResponse(
            total_rows=total_rows,
            inserted=inserted,
            duplicates=duplicates,
            failed=failed,
            errors=errors
        )
