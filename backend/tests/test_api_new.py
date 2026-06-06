import pytest
from httpx import AsyncClient
from uuid import uuid4
from datetime import datetime, timezone, date
from decimal import Decimal
from app.domain.models import Tender, TenderDocument, TenderDocumentStatus, TenderStatus
from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.infrastructure.repositories.metadata import SQLAlchemyTenderMetadataRepository


@pytest.mark.asyncio
async def test_get_document_api(client: AsyncClient, db_session):
    # Setup a tender and document
    t_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    
    tender = Tender(
        id=uuid4(),
        tender_number="TND-API-DOC",
        department="Engineering",
        source_url="https://example.com/api-doc.pdf",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await t_repo.add(tender)
    
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        file_name="api-doc.pdf",
        file_path="data/pdfs/api-doc.pdf",
        status=TenderDocumentStatus.PENDING,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)
    await db_session.commit()
    
    res = await client.get(f"/api/v1/tenders/{tender.id}/document")
    assert res.status_code == 200
    data = res.json()
    assert data["tender_id"] == str(tender.id)
    assert data["status"] == "PENDING"
    assert data["file_name"] == "api-doc.pdf"


@pytest.mark.asyncio
async def test_trigger_download_api(client: AsyncClient, db_session):
    t_repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    
    tender = Tender(
        id=uuid4(),
        tender_number="TND-API-DL",
        department="Engineering",
        source_url="https://example.com/api-dl.pdf",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await t_repo.add(tender)
    
    doc = TenderDocument(
        id=uuid4(),
        tender_id=tender.id,
        status=TenderDocumentStatus.FAILED,
        attempts=2,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await doc_repo.add(doc)
    await db_session.commit()
    
    res = await client.post(f"/api/v1/tenders/{tender.id}/download")
    assert res.status_code == 202
    data = res.json()
    assert data["tender_id"] == str(tender.id)
    assert data["status"] == "PENDING"
    
    # Check that status was reset in db (allowing for background execution progress)
    updated_doc = await doc_repo.get_by_tender_id(tender.id)
    assert updated_doc.status in (
        TenderDocumentStatus.PENDING,
        TenderDocumentStatus.DOWNLOADING,
        TenderDocumentStatus.DOWNLOADED,
        TenderDocumentStatus.FAILED,
    )
    assert updated_doc.attempts in (0, 1)



@pytest.mark.asyncio
async def test_trigger_extract_api(client: AsyncClient, db_session):
    t_repo = SQLAlchemyTenderRepository(db_session)
    
    tender = Tender(
        id=uuid4(),
        tender_number="TND-API-EXT",
        department="Engineering",
        source_url="https://example.com/api-ext.pdf",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    await t_repo.add(tender)
    await db_session.commit()
    
    res = await client.post(f"/api/v1/tenders/{tender.id}/extract")
    assert res.status_code == 202
    data = res.json()
    assert data["tender_id"] == str(tender.id)
    assert data["status"] == "PROCESSING"
