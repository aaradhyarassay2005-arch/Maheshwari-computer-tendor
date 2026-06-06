import pytest
import os
import shutil
import hashlib
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal

from app.domain.repositories import IPDFDownloader
from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.storage.local import LocalStorageProvider
from app.application.downloader import TenderDownloaderService


class MockPDFDownloader(IPDFDownloader):
    def __init__(self, content: bytes = b"%PDF-1.4 mock file", should_fail: bool = False, bad_mimetype: bool = False):
        self.content = content
        self.should_fail = should_fail
        self.bad_mimetype = bad_mimetype

    async def download(self, url: str) -> bytes:
        if self.should_fail:
            raise Exception("Mock download timeout connection error")
        if self.bad_mimetype:
            raise ValueError("Invalid Content-Type: text/html. Expected application/pdf")
        return self.content


@pytest.fixture
def clean_storage_dir():
    storage_dir = "tests/test_downloader_pdfs"
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)
    os.makedirs(storage_dir, exist_ok=True)
    yield storage_dir
    if os.path.exists(storage_dir):
        shutil.rmtree(storage_dir)


@pytest.fixture
def downloader_setup(db_session, clean_storage_dir):
    tender_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    storage = LocalStorageProvider(clean_storage_dir)
    return tender_repo, doc_repo, storage


@pytest.mark.asyncio
async def test_download_success(downloader_setup):
    tender_repo, doc_repo, storage = downloader_setup

    # Create a tender
    tender = Tender(
        id=uuid4(),
        tender_number="TND-DL-100",
        department="Engineering",
        source_url="https://example.com/file.pdf",
        tender_value=Decimal("1000.00"),
        closing_date=date(2026, 12, 12),
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    # Ingestion hook: Create PENDING document
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    mock_downloader = MockPDFDownloader()
    service = TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=mock_downloader,
        storage=storage,
    )

    downloaded = await service.download_document(tender.id)
    assert downloaded is not None
    assert downloaded.tender_id == tender.id
    assert downloaded.mime_type == "application/pdf"
    assert downloaded.file_size == len(b"%PDF-1.4 mock file")
    assert downloaded.sha256 == hashlib.sha256(b"%PDF-1.4 mock file").hexdigest()
    assert downloaded.status == TenderDocumentStatus.DOWNLOADED
    assert downloaded.attempts == 1
    assert downloaded.error_message is None

    # Check database tender status
    updated_tender = await tender_repo.get_by_id(tender.id)
    assert updated_tender.status == TenderStatus.DOWNLOADED


@pytest.mark.asyncio
async def test_download_timeout_failure(downloader_setup):
    tender_repo, doc_repo, storage = downloader_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-DL-ERR",
        department="Engineering",
        source_url="https://example.com/file.pdf",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    # Mock timeout
    mock_downloader = MockPDFDownloader(should_fail=True)
    service = TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=mock_downloader,
        storage=storage,
    )

    downloaded = await service.download_document(tender.id)
    assert downloaded is None

    # Check document status
    updated_doc = await doc_repo.get_by_tender_id(tender.id)
    assert updated_doc.status == TenderDocumentStatus.FAILED
    assert updated_doc.attempts == 1
    assert "timeout" in updated_doc.error_message.lower()

    # Check database status
    updated_tender = await tender_repo.get_by_id(tender.id)
    assert updated_tender.status == TenderStatus.FAILED


@pytest.mark.asyncio
async def test_download_invalid_content_type(downloader_setup):
    tender_repo, doc_repo, storage = downloader_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-DL-MIME",
        department="Engineering",
        source_url="https://example.com/file.html",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    # Mock bad mimetype
    mock_downloader = MockPDFDownloader(bad_mimetype=True)
    service = TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=mock_downloader,
        storage=storage,
    )

    downloaded = await service.download_document(tender.id)
    assert downloaded is None

    # Check status
    updated_doc = await doc_repo.get_by_tender_id(tender.id)
    assert updated_doc.status == TenderDocumentStatus.FAILED
    assert "Content-Type" in updated_doc.error_message

    updated_tender = await tender_repo.get_by_id(tender.id)
    assert updated_tender.status == TenderStatus.FAILED


@pytest.mark.asyncio
async def test_download_duplicate_prevention(downloader_setup):
    tender_repo, doc_repo, storage = downloader_setup

    t1 = Tender(
        id=uuid4(),
        tender_number="TND-DL-DUP1",
        department="Eng",
        source_url="https://example.com/1.pdf",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(t1)

    doc1 = TenderDocument(
        id=uuid4(),
        tender_id=t1.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc1)

    t2 = Tender(
        id=uuid4(),
        tender_number="TND-DL-DUP2",
        department="Eng",
        source_url="https://example.com/2.pdf",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(t2)

    doc2 = TenderDocument(
        id=uuid4(),
        tender_id=t2.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc2)

    # Download first document successfully
    service = TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=MockPDFDownloader(),
        storage=storage,
    )

    d1 = await service.download_document(t1.id)
    assert d1 is not None
    assert d1.status == TenderDocumentStatus.DOWNLOADED

    # Attempt second download yielding identical PDF content (same hash)
    d2 = await service.download_document(t2.id)
    assert d2 is None  # Fails due to duplicate hash detection

    # Check second tender is failed with duplicate error
    t2_updated = await tender_repo.get_by_id(t2.id)
    assert t2_updated.status == TenderStatus.FAILED

    doc2_updated = await doc_repo.get_by_tender_id(t2.id)
    assert doc2_updated.status == TenderDocumentStatus.FAILED
    assert "Duplicate" in doc2_updated.error_message


@pytest.mark.asyncio
async def test_run_background_downloads_retry_limits(downloader_setup):
    tender_repo, doc_repo, storage = downloader_setup

    tender = Tender(
        id=uuid4(),
        tender_number="TND-RETRY",
        department="Eng",
        source_url="https://example.com/retry.pdf",
        status=TenderStatus.NEW,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await tender_repo.add(tender)

    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_size=0,
        status=TenderDocumentStatus.PENDING,
        attempts=0,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)

    # Downloader configured to fail continuously
    service = TenderDownloaderService(
        tender_repo=tender_repo,
        doc_repo=doc_repo,
        downloader=MockPDFDownloader(should_fail=True),
        storage=storage,
    )

    # Run polling loop (Attempt 1)
    summary1 = await service.run_background_downloads(max_attempts=3)
    assert summary1["processed"] == 1
    assert summary1["failed"] == 1

    doc_after1 = await doc_repo.get_by_tender_id(tender.id)
    assert doc_after1.attempts == 1

    # Run polling loop (Attempt 2)
    summary2 = await service.run_background_downloads(max_attempts=3)
    assert summary2["processed"] == 1
    assert summary2["failed"] == 1

    doc_after2 = await doc_repo.get_by_tender_id(tender.id)
    assert doc_after2.attempts == 2

    # Run polling loop (Attempt 3)
    summary3 = await service.run_background_downloads(max_attempts=3)
    assert summary3["processed"] == 1
    assert summary3["failed"] == 1

    doc_after3 = await doc_repo.get_by_tender_id(tender.id)
    assert doc_after3.attempts == 3

    # Run polling loop (Attempt 4 - should skip retrying because attempts = 3)
    summary4 = await service.run_background_downloads(max_attempts=3)
    assert summary4["processed"] == 0  # skipped
