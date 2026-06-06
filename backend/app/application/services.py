import io
from datetime import datetime, timezone, date
from decimal import Decimal
from typing import List, Optional, Tuple
from uuid import uuid4
import structlog
import pandas as pd
from pydantic import UUID4

from app.domain.models import Tender, TenderStatus, TenderDocument, TenderDocumentStatus
from app.domain.repositories import ITenderRepository, ITenderDocumentRepository
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
    def __init__(self, tender_repo: ITenderRepository, doc_repo: ITenderDocumentRepository):
        self.tender_repo = tender_repo
        self.doc_repo = doc_repo

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

        required_cols = {"tender_number", "department", "source_url"}
        missing = required_cols - set(df.columns)
        if missing:
            raise ValueError(f"Missing required column(s): {', '.join(missing)}")

        total_rows = 0
        inserted = 0
        duplicates = 0
        failed = 0
        errors = []
        tenders_to_insert = []
        seen_numbers = set()
        seen_urls = set()

        # Iterate rows
        for index, row in df.iterrows():
            total_rows += 1
            row_num = int(index) + 2  # Excel row is 1-indexed + header row = index + 2

            # Extract fields
            tender_num_val = row.get("tender_number")
            dept_val = row.get("department")
            url_val = row.get("source_url")
            value_val = row.get("tender_value")
            closing_date_val = row.get("closing_date")

            # Check required fields are non-empty
            if pd.isna(tender_num_val) or str(tender_num_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": "UNKNOWN", "error": "Missing tender_number"})
                continue
            tender_number = str(tender_num_val).strip()

            if pd.isna(dept_val) or str(dept_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": "Missing department"})
                continue
            department = str(dept_val).strip()

            if pd.isna(url_val) or str(url_val).strip() == "":
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": "Missing source_url"})
                continue
            source_url = str(url_val).strip()

            # Validate source url structure
            if not is_valid_url(source_url):
                failed += 1
                errors.append({"row": row_num, "tender_number": tender_number, "error": f"Invalid source_url format: {source_url}"})
                continue

            # Validate tender value
            tender_value = None
            if not pd.isna(value_val) and str(value_val).strip() != "":
                try:
                    clean_val = str(value_val).replace(",", "").replace("$", "").strip()
                    tender_value = Decimal(clean_val)
                    if tender_value < 0:
                        raise ValueError("Tender value cannot be negative")
                except Exception as e:
                    failed += 1
                    errors.append({"row": row_num, "tender_number": tender_number, "error": f"Invalid tender_value: {str(e)}"})
                    continue

            # Validate closing date
            closing_date = None
            if not pd.isna(closing_date_val) and str(closing_date_val).strip() != "":
                if isinstance(closing_date_val, datetime):
                    closing_date = closing_date_val.date()
                elif isinstance(closing_date_val, date):
                    closing_date = closing_date_val
                else:
                    try:
                        # Try parsing string ISO format
                        parsed_dt = datetime.fromisoformat(str(closing_date_val).replace("Z", "+00:00"))
                        closing_date = parsed_dt.date()
                    except Exception:
                        parsed_date = None
                        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y"):
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

            # Construct Tender model
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
                updated_at=now
            )
            tenders_to_insert.append(tender)
            inserted += 1

        # Bulk save
        if tenders_to_insert:
            await self.tender_repo.bulk_add(tenders_to_insert)
            docs_to_insert = []
            for t in tenders_to_insert:
                if t.source_url:
                    doc = TenderDocument(
                        id=uuid4(),
                        tender_id=t.id,
                        file_size=0,
                        status=TenderDocumentStatus.PENDING,
                        attempts=0,
                        created_at=t.created_at,
                        updated_at=t.updated_at,
                    )
                    docs_to_insert.append(doc)
            if docs_to_insert:
                await self.doc_repo.bulk_add(docs_to_insert)

        return ExcelImportResponse(
            total_rows=total_rows,
            inserted=inserted,
            duplicates=duplicates,
            failed=failed,
            errors=errors
        )
