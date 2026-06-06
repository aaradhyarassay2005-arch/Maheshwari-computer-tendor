import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from httpx import AsyncClient

from app.domain.models import AuditLog
from app.infrastructure.repositories.audit import SQLAlchemyAuditLogRepository
from app.application.audit_service import AuditLoggingService
from app.infrastructure.db.models import AuditLogORM

@pytest.mark.asyncio
async def test_audit_service_log_action(db_session: AsyncSession):
    repo = SQLAlchemyAuditLogRepository(db_session)
    service = AuditLoggingService(repo)

    log = await service.log_action(
        action="TEST_ACTION",
        resource_type="test_resource",
        resource_id="res-123",
        user_id="user-456",
        user_role="admin",
        ip_address="127.0.0.1",
        client_agent="pytest-client",
        change_diff={"before": "a", "after": "b"}
    )

    assert log.action == "TEST_ACTION"
    assert log.resource_type == "test_resource"
    assert log.resource_id == "res-123"
    assert log.user_id == "user-456"

    # Verify directly in the DB
    stmt = select(AuditLogORM).where(AuditLogORM.id == log.id)
    result = await db_session.execute(stmt)
    db_row = result.scalar_one_or_none()
    assert db_row is not None
    assert db_row.action == "TEST_ACTION"
    assert "before" in db_row.change_diff

    # Verify listing
    logs, total = await service.list_logs(0, 10)
    assert total == 1
    assert len(logs) == 1
    assert logs[0].id == log.id

@pytest.mark.asyncio
async def test_audit_logging_in_api_endpoints(client: AsyncClient, db_session: AsyncSession):
    # 1. Create a tender manually
    tender_payload = {
        "tender_number": "TENDER-AUDIT-99",
        "department": "Security Dept",
        "source_url": "http://example.com/sec.pdf",
        "tender_value": 5000000.0,
        "closing_date": "2026-12-31"
    }
    
    res = await client.post("/api/v1/tenders", json=tender_payload)
    assert res.status_code == 201
    tender_id = res.json()["id"]

    # Check that TENDER_CREATION audit log was written
    stmt = select(AuditLogORM).where(AuditLogORM.action == "TENDER_CREATION")
    result = await db_session.execute(stmt)
    audit_row = result.scalar_one_or_none()
    assert audit_row is not None
    assert audit_row.resource_id == str(tender_id)
    assert "Security Dept" in audit_row.change_diff

    # Clear session to avoid cached queries
    db_session.expire_all()

    # 2. Delete the tender
    del_res = await client.delete(f"/api/v1/tenders/{tender_id}")
    assert del_res.status_code == 204

    # Check that TENDER_DELETION audit log was written
    stmt = select(AuditLogORM).where(AuditLogORM.action == "TENDER_DELETION")
    result = await db_session.execute(stmt)
    audit_del_row = result.scalar_one_or_none()
    assert audit_del_row is not None
    assert audit_del_row.resource_id == str(tender_id)
