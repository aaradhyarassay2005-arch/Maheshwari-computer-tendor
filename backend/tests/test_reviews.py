import pytest
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient

from app.domain.models import TenderStatus
from app.infrastructure.db.models import TenderORM, TenderMetadataORM, TenderReviewORM, AuditLogORM


@pytest.mark.asyncio
async def test_reviews_workflow(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a tender manually
    tender_payload = {
        "tender_number": "TENDER-REV-01",
        "department": "Transport Dept",
        "source_url": "http://example.com/rev.pdf",
        "tender_value": 1000000.0,
        "closing_date": "2026-10-31"
    }
    
    res = await client.post("/api/v1/tenders", json=tender_payload)
    assert res.status_code == 201
    tender_data = res.json()
    tender_id = tender_data["id"]

    # The tender starts with status "NEW"
    assert tender_data["status"] == "NEW"

    # 2. Check the review queue (should be empty as the tender is not in "PARSED" status)
    queue_res = await client.get("/api/v1/reviews/queue")
    assert queue_res.status_code == 200
    assert len(queue_res.json()) == 0

    # Let's manually advance the tender's status to "PARSED" and create a metadata record
    # directly in the database to simulate extraction completion
    stmt = select(TenderORM).where(TenderORM.id == UUID(tender_id))
    result = await db_session.execute(stmt)
    tender_orm = result.scalar_one()
    tender_orm.status = TenderStatus.PARSED
    
    metadata_orm = TenderMetadataORM(
        tender_id=tender_orm.id,
        tender_number="TENDER-REV-01",
        tender_number_confidence=0.85,
        department="Transprt Dpt",  # slightly misspelled
        department_confidence=0.9,
        tender_value=950000.0,  # parsed slightly wrong
        tender_value_confidence=0.75,
        closing_date=tender_orm.closing_date,
        closing_date_confidence=0.95,
        emd=10000.0,
        emd_confidence=0.8
    )
    db_session.add(metadata_orm)
    await db_session.commit()
    db_session.expire_all()

    # 3. Check the review queue again (should contain the tender now)
    queue_res = await client.get("/api/v1/reviews/queue")
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert len(queue_data) == 1
    assert queue_data[0]["id"] == tender_id
    assert queue_data[0]["status"] == "PARSED"

    # 4. Submit review with corrections
    submit_payload = {
        "verdict": "APPROVED",
        "reviewer_id": "rev-999",
        "comments": "Values corrected based on official document",
        "corrections": {
            "tender_number": "TENDER-REV-01-A",  # updated number
            "department": "Transport Department",  # corrected name
            "tender_value": 1200000.0,  # corrected value
            "emd": 15000.0  # corrected EMD
        }
    }

    submit_res = await client.post(f"/api/v1/reviews/{tender_id}/submit", json=submit_payload)
    assert submit_res.status_code == 200
    sub_data = submit_res.json()
    assert sub_data["verdict"] == "APPROVED"
    assert sub_data["reviewer_id"] == "rev-999"
    assert sub_data["original_values"]["department"] == "Transprt Dpt"
    assert sub_data["corrected_values"]["department"] == "Transport Department"

    # 5. Verify database updates
    db_session.expire_all()
    # Verify tender updates
    stmt = select(TenderORM).where(TenderORM.id == UUID(tender_id))
    res_tender = await db_session.execute(stmt)
    updated_tender = res_tender.scalar_one()
    assert updated_tender.status == TenderStatus.APPROVED
    assert updated_tender.tender_number == "TENDER-REV-01-A"
    assert updated_tender.department == "Transport Department"
    assert updated_tender.tender_value == 1200000.0

    # Verify metadata updates
    stmt_meta = select(TenderMetadataORM).where(TenderMetadataORM.tender_id == UUID(tender_id))
    res_meta = await db_session.execute(stmt_meta)
    updated_meta = res_meta.scalar_one()
    assert updated_meta.tender_number == "TENDER-REV-01-A"
    assert updated_meta.tender_number_confidence == 1.0
    assert updated_meta.department == "Transport Department"
    assert updated_meta.department_confidence == 1.0
    assert updated_meta.tender_value == 1200000.0
    assert updated_meta.emd == 15000.0

    # Verify review log record
    stmt_rev = select(TenderReviewORM).where(TenderReviewORM.tender_id == UUID(tender_id))
    res_rev = await db_session.execute(stmt_rev)
    review_row = res_rev.scalar_one()
    assert review_row.verdict == TenderStatus.APPROVED
    assert review_row.reviewer_id == "rev-999"
    assert review_row.comments == "Values corrected based on official document"

    # Verify audit log entry
    stmt_audit = select(AuditLogORM).where(AuditLogORM.action == "SUBMIT_REVIEW")
    res_audit = await db_session.execute(stmt_audit)
    audit_row = res_audit.scalar_one()
    assert audit_row.resource_id == str(tender_id)
    assert audit_row.user_id == "rev-999"

    # 6. Verify history endpoint
    hist_res = await client.get(f"/api/v1/reviews/{tender_id}/history")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert len(hist_data) == 1
    assert hist_data[0]["reviewer_id"] == "rev-999"
    assert hist_data[0]["verdict"] == "APPROVED"
