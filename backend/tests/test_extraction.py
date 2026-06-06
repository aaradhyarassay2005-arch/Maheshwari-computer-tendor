import pytest
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.domain.repositories import IPDFExtractor
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository
from app.infrastructure.extractors.rule_based import RuleBasedMetadataExtractor
from app.application.extraction_service import TenderMetadataExtractionService


class MockPDFExtractor(IPDFExtractor):
    def __init__(self, text: str, should_fail: bool = False):
        self.text = text
        self.should_fail = should_fail

    async def extract_text(self, file_path: str) -> str:
        if self.should_fail:
            raise Exception("Mock extraction failed")
        return self.text


# Sample text matching a real Indian Railways tender notice
REAL_RAILWAY_TENDER_TEXT = """
GOVERNMENT OF INDIA
NORTHERN RAILWAY
Tender Notice No: DY-CE-C-TND-2026-05
Department: Civil Engineering
Office of the Chief Administrative Officer, Kashmiri Gate, Delhi.
Estimated Cost / Advertised Value: Rs. 15,24,357.89
Earnest Money Deposit (EMD): INR 30,500.00
Tender Type: Open Tender
Zone: Northern Railway
Bidding System: Single Packet System
Type of Work / Contract Type: Works
Closing Date & Time: 24/12/2026 at 15:00 Hrs
Completion Period: 12 Months
"""

INVALID_VALUES_TENDER_TEXT = """
Tender Notice No: TND-NEG-01
Advertised Value: Rs. -500,000.00
EMD: Rs. -10,000.00
Closing Date: 12.12.2026
"""


@pytest.fixture
def extraction_setup(db_session):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    meta_repo = SQLAlchemyTenderMetadataRepository(db_session)
    return tender_repo, doc_repo, meta_repo


@pytest.mark.asyncio
async def test_regex_rule_based_extractor():
    extractor = RuleBasedMetadataExtractor()
    extracted = await extractor.extract(REAL_RAILWAY_TENDER_TEXT)

    assert extracted["tender_number"] == "DY-CE-C-TND-2026-05"
    assert extracted["tender_number_confidence"] == 1.0
    assert extracted["department"] == "Civil Engineering"
    assert extracted["department_confidence"] == 1.0
    assert extracted["tender_value"] == Decimal("1524357.89")
    assert extracted["tender_value_confidence"] == 1.0
    assert extracted["emd"] == Decimal("30500.00")
    assert extracted["emd_confidence"] == 1.0
    assert extracted["closing_date"] == date(2026, 12, 24)
    assert extracted["closing_date_confidence"] == 1.0
    assert extracted["completion_period"] == "12 Months"
    assert extracted["completion_period_confidence"] == 1.0
    assert extracted["tender_type"] == "Open"
    assert extracted["tender_type_confidence"] == 1.0
    assert extracted["zone"] == "Northern Railway"
    assert extracted["zone_confidence"] == 1.0
    assert extracted["bid_system"] == "Single Packet System"
    assert extracted["bid_system_confidence"] == 1.0
    assert extracted["contract_type"] == "Works"
    assert extracted["contract_type_confidence"] == 1.0


@pytest.mark.asyncio
async def test_extraction_service_success(extraction_setup):
    tender_repo, doc_repo, meta_repo = extraction_setup

    # Insert Tender
    tender = Tender(
        id=uuid4(),
        tender_number="DY-CE-C-TND-2026-05",
        department="Before Extraction",
        source_url="https://example.com/tnd.pdf",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Insert Document
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="tnd.pdf",
        file_path="data/pdfs/mock.pdf",
        status=TenderDocumentStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    primary_extractor = MockPDFExtractor(REAL_RAILWAY_TENDER_TEXT)
    fallback_extractor = MockPDFExtractor("", should_fail=True)
    provider = RuleBasedMetadataExtractor()

    service = TenderMetadataExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        metadata_repo=meta_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
        extraction_provider=provider,
    )

    meta = await service.extract_metadata(tender.id)
    assert meta is not None
    assert meta.tender_id == tender.id
    assert meta.tender_number == "DY-CE-C-TND-2026-05"
    assert meta.tender_value == Decimal("1524357.89")
    assert meta.emd == Decimal("30500.00")
    assert meta.closing_date == date(2026, 12, 24)

    # Check that parent Tender was automatically updated
    updated_tender = await tender_repo.get_by_id(tender.id)
    assert updated_tender.status == TenderStatus.PARSED
    assert updated_tender.tender_value == Decimal("1524357.89")
    assert updated_tender.closing_date == date(2026, 12, 24)


@pytest.mark.asyncio
async def test_extraction_service_fallback(extraction_setup):
    tender_repo, doc_repo, meta_repo = extraction_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-FALLBACK",
        department="Before",
        source_url="http://x",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="tnd.pdf",
        file_path="data/pdfs/mock.pdf",
        status=TenderDocumentStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    # Primary fails, fallback succeeds
    primary_extractor = MockPDFExtractor("", should_fail=True)
    fallback_extractor = MockPDFExtractor(REAL_RAILWAY_TENDER_TEXT)
    provider = RuleBasedMetadataExtractor()

    service = TenderMetadataExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        metadata_repo=meta_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
        extraction_provider=provider,
    )

    meta = await service.extract_metadata(tender.id)
    assert meta is not None
    assert meta.tender_number == "DY-CE-C-TND-2026-05"

    updated_tender = await tender_repo.get_by_id(tender.id)
    assert updated_tender.status == TenderStatus.PARSED


@pytest.mark.asyncio
async def test_extraction_validation_constraints(extraction_setup):
    tender_repo, doc_repo, meta_repo = extraction_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-NEG-VAL",
        department="Before",
        source_url="http://x",
        status=TenderStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="tnd.pdf",
        file_path="data/pdfs/mock.pdf",
        status=TenderDocumentStatus.DOWNLOADED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    primary_extractor = MockPDFExtractor(INVALID_VALUES_TENDER_TEXT)
    fallback_extractor = MockPDFExtractor("", should_fail=True)
    provider = RuleBasedMetadataExtractor()

    service = TenderMetadataExtractionService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        metadata_repo=meta_repo,
        primary_extractor=primary_extractor,
        fallback_extractor=fallback_extractor,
        extraction_provider=provider,
    )

    meta = await service.extract_metadata(tender.id)
    assert meta is not None
    # Negative values must be validation-reset to None
    assert meta.tender_value is None
    assert meta.tender_value_confidence == 0.0
    assert meta.emd is None
    assert meta.emd_confidence == 0.0
