import io
import pandas as pd
import pytest
from httpx import AsyncClient
from decimal import Decimal
from datetime import date

from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.application.services import TenderService


def create_excel_bytes(rows, columns) -> bytes:
    df = pd.DataFrame(rows, columns=columns)
    out = io.BytesIO()
    df.to_excel(out, index=False, engine="openpyxl")
    return out.getvalue()


@pytest.fixture
def service(db_session) -> TenderService:
    repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    return TenderService(repo, doc_repo)


@pytest.mark.asyncio
async def test_import_tenders_success(service: TenderService):
    columns = ["tender_number", "department", "source_url", "tender_value", "closing_date"]
    rows = [
        ["TND-E1", "Railways", "https://example.com/pdf1.pdf", 150000.00, "2026-12-01"],
        ["TND-E2", "Metro Corp", "https://example.com/pdf2.pdf", 5000.50, "2026-11-20"],
    ]
    excel_bytes = create_excel_bytes(rows, columns)
    summary = await service.import_tenders_from_excel(excel_bytes)

    assert summary.total_rows == 2
    assert summary.inserted == 2
    assert summary.duplicates == 0
    assert summary.failed == 0
    assert len(summary.errors) == 0

    # Verify db lookup
    t1 = await service.tender_repo.get_by_tender_number("TND-E1")
    assert t1 is not None
    assert t1.department == "Railways"
    assert t1.tender_value == Decimal("150000.00")
    assert t1.closing_date == date(2026, 12, 1)


@pytest.mark.asyncio
async def test_import_tenders_missing_columns(service: TenderService):
    # Missing required column 'source_url'
    columns = ["tender_number", "department", "tender_value"]
    rows = [
        ["TND-E1", "Railways", 150000.00]
    ]
    excel_bytes = create_excel_bytes(rows, columns)
    with pytest.raises(ValueError) as exc:
        await service.import_tenders_from_excel(excel_bytes)
    assert "Missing required column(s)" in str(exc.value)


@pytest.mark.asyncio
async def test_import_tenders_validation_and_duplicates(service: TenderService):
    # Setup database pre-existing duplicate (both number and URL)
    await service.create_tender(
        tender_number="TND-DUP",
        department="D1",
        source_url="https://example.com/dup.pdf"
    )

    columns = ["tender_number", "department", "source_url", "tender_value", "closing_date"]
    rows = [
        ["TND-E1", "Railways", "https://example.com/e1.pdf", -10.00, "2026-12-01"],  # Negative value failure
        ["TND-E2", "Metro Corp", "https://example.com/e2.pdf", 5000.50, "invalid-date"],  # Date parse failure
        ["TND-E3", "Defense", "invalid-url", 10.00, "2026-10-10"],  # URL validation failure
        ["TND-DUP", "Metro Corp", "https://example.com/dup.pdf", 200.00, "2026-09-09"],  # DB duplicate failure
        ["TND-INTERNAL", "Forestry", "https://example.com/ok1.pdf", 100.00, "2026-09-09"],  # First occurrence ok
        ["TND-INTERNAL", "Forestry", "https://example.com/ok2.pdf", 200.00, "2026-09-09"],  # Spreadsheet duplicate number failure
        ["TND-INTERNAL-2", "Forestry", "https://example.com/ok1.pdf", 200.00, "2026-09-09"],  # Spreadsheet duplicate URL failure
    ]
    excel_bytes = create_excel_bytes(rows, columns)
    summary = await service.import_tenders_from_excel(excel_bytes)

    assert summary.total_rows == 7
    assert summary.inserted == 1  # Only TND-INTERNAL (first occurrence) succeeds
    assert summary.duplicates == 3  # TND-DUP (DB), TND-INTERNAL (sheet number duplicate), and TND-INTERNAL-2 (sheet URL duplicate)
    assert summary.failed == 3  # Negative value, invalid date, invalid URL
    assert len(summary.errors) == 6


@pytest.mark.asyncio
async def test_import_endpoint_api(client: AsyncClient):
    columns = ["tender_number", "department", "source_url", "tender_value", "closing_date"]
    rows = [
        ["TND-API-E1", "Railways", "https://example.com/api1.pdf", 250.00, "2026-12-01"]
    ]
    excel_bytes = create_excel_bytes(rows, columns)
    files = {"file": ("tenders.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    
    response = await client.post("/api/v1/imports/excel", files=files)
    assert response.status_code == 201
    summary = response.json()
    assert summary["inserted"] == 1
    assert summary["total_rows"] == 1
