import pytest
from datetime import date
from decimal import Decimal
from uuid import uuid4

from app.infrastructure.repositories.tenders import SQLAlchemyTenderRepository
from app.infrastructure.repositories.documents import SQLAlchemyTenderDocumentRepository
from app.application.services import TenderService
from app.domain.models import TenderStatus
from app.domain.exceptions import TenderNotFoundException, TenderAlreadyExistsException


@pytest.fixture
def service(db_session) -> TenderService:
    repo = SQLAlchemyTenderRepository(db_session)
    doc_repo = SQLAlchemyTenderDocumentRepository(db_session)
    return TenderService(repo, doc_repo)


@pytest.mark.asyncio
async def test_create_tender_success(service: TenderService):
    tender = await service.create_tender(
        tender_number="TND-100",
        department="Engineering",
        source_url="http://example.com/pdf.pdf",
        tender_value=Decimal("5000.00"),
        closing_date=date(2026, 12, 31),
    )
    assert tender.id is not None
    assert tender.tender_number == "TND-100"
    assert tender.department == "Engineering"
    assert tender.source_url == "http://example.com/pdf.pdf"
    assert tender.tender_value == Decimal("5000.00")
    assert tender.closing_date == date(2026, 12, 31)
    assert tender.status == TenderStatus.NEW

    # Retrieve
    retrieved = await service.get_tender(tender.id)
    assert retrieved is not None
    assert retrieved.tender_number == "TND-100"


@pytest.mark.asyncio
async def test_create_tender_duplicate(service: TenderService):
    await service.create_tender(
        tender_number="TND-DUP",
        department="Civil",
        source_url="http://example.com/civil.pdf",
    )
    with pytest.raises(TenderAlreadyExistsException):
        await service.create_tender(
            tender_number="TND-DUP",
            department="Electrical",
            source_url="http://example.com/elec.pdf",
        )


@pytest.mark.asyncio
async def test_get_tender_not_found(service: TenderService):
    retrieved = await service.get_tender(uuid4())
    assert retrieved is None


@pytest.mark.asyncio
async def test_list_tenders(service: TenderService):
    await service.create_tender("T1", "Civil", "http://x")
    await service.create_tender("T2", "Electrical", "http://x")
    await service.create_tender("T3", "Water", "http://x")

    items, total = await service.list_tenders(skip=0, limit=10)
    assert total == 3
    assert len(items) == 3

    # search
    items, total = await service.list_tenders(search="Civil")
    assert total == 1
    assert items[0].tender_number == "T1"


@pytest.mark.asyncio
async def test_update_tender_patch(service: TenderService):
    tender = await service.create_tender(
        tender_number="TND-UPDATE",
        department="Mechanical",
        source_url="http://x",
        tender_value=Decimal("100.00"),
    )

    updated = await service.update_tender(
        id=tender.id,
        department="IT Department",
        status=TenderStatus.DOWNLOADED,
    )
    assert updated.id == tender.id
    assert updated.department == "IT Department"
    assert updated.status == TenderStatus.DOWNLOADED
    assert updated.tender_value == Decimal("100.00")  # Kept original


@pytest.mark.asyncio
async def test_delete_tender(service: TenderService):
    tender = await service.create_tender("TND-DEL", "D", "http://x")
    assert await service.get_tender(tender.id) is not None

    deleted = await service.delete_tender(tender.id)
    assert deleted is True

    assert await service.get_tender(tender.id) is None
