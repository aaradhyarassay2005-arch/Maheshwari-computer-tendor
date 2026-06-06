import pytest
from uuid import uuid4
from decimal import Decimal
from datetime import datetime, timezone

from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.repositories.boq import SQLAlchemyBOQItemRepository
from app.infrastructure.extractors.camelot_boq import CamelotBOQExtractor
from app.infrastructure.extractors.pdfplumber_boq import PdfPlumberBOQExtractor
from app.application.boq_service import TenderBOQExtractionService

TEST_PDF_PATH = "tests/test_files/test_boq_replica.pdf"


@pytest.fixture
def boq_setup(db_session):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    boq_repo = SQLAlchemyBOQItemRepository(db_session)
    return tender_repo, doc_repo, boq_repo


@pytest.mark.asyncio
async def test_boq_extraction_service_success(boq_setup):
    tender_repo, doc_repo, boq_repo = boq_setup

    # Insert Tender
    tender = Tender(
        id=uuid4(),
        tender_number="TND-BOQ-SERV",
        department="Engineering Division",
        source_url="https://example.com/boq.pdf",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Insert Document referencing our real generated test PDF file
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="boq_replica.pdf",
        file_path=TEST_PDF_PATH,
        status=TenderDocumentStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    primary_extractor = CamelotBOQExtractor()
    fallback_extractor = PdfPlumberBOQExtractor()

    service = TenderBOQExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        boq_repo=boq_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
    )

    extracted_items = await service.extract_boq(tender.id)
    assert len(extracted_items) == 5

    # Fetch from repository directly
    db_items = await boq_repo.get_by_tender_id(tender.id)
    assert len(db_items) == 5

    # Verify normalization and types
    item_1 = db_items[0]
    assert item_1.item_code == "1"
    assert item_1.quantity == Decimal("150.00")
    assert item_1.unit == "Cum"
    assert item_1.unit_rate == Decimal("320.00")
    assert item_1.amount == Decimal("48000.00")
    assert item_1.confidence == 1.0
    assert "SCHEDULE - A" in item_1.schedule_name

    # Verify Unit Normalization of "Nos." to "Nos" on item 5
    item_5 = db_items[4]
    assert item_5.item_code == "5"
    assert item_5.unit == "Nos"  # Mapped from Nos. to Nos
    assert item_5.quantity == Decimal("25.00")
    assert item_5.unit_rate == Decimal("1800.00")
    assert item_5.amount == Decimal("45000.00")
    assert item_5.confidence == 1.0


@pytest.mark.asyncio
async def test_boq_extraction_service_missing_document(boq_setup):
    tender_repo, doc_repo, boq_repo = boq_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-BOQ-NODOC",
        department="Engineering",
        source_url="https://example.com/nodoc.pdf",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    service = TenderBOQExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        boq_repo=boq_repo,
        primary_extractor=CamelotBOQExtractor(),
        fallback_extractor=PdfPlumberBOQExtractor(),
    )

    extracted_items = await service.extract_boq(tender.id)
    assert len(extracted_items) == 0
