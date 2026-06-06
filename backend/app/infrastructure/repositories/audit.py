from typing import List, Tuple
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import AuditLog
from app.domain.repositories import IAuditLogRepository
from app.infrastructure.db.models import AuditLogORM


def to_domain_audit_log(orm: AuditLogORM) -> AuditLog:
    return AuditLog(
        id=orm.id,
        timestamp=orm.timestamp,
        user_id=orm.user_id,
        user_role=orm.user_role,
        action=orm.action,
        resource_type=orm.resource_type,
        resource_id=orm.resource_id,
        ip_address=orm.ip_address,
        client_agent=orm.client_agent,
        change_diff=orm.change_diff
    )


class SQLAlchemyAuditLogRepository(IAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add(self, audit_log: AuditLog) -> AuditLog:
        orm = AuditLogORM(
            id=audit_log.id,
            timestamp=audit_log.timestamp,
            user_id=audit_log.user_id,
            user_role=audit_log.user_role,
            action=audit_log.action,
            resource_type=audit_log.resource_type,
            resource_id=audit_log.resource_id,
            ip_address=audit_log.ip_address,
            client_agent=audit_log.client_agent,
            change_diff=audit_log.change_diff
        )
        self.session.add(orm)
        await self.session.flush()
        return to_domain_audit_log(orm)

    async def list(self, skip: int = 0, limit: int = 100) -> Tuple[List[AuditLog], int]:
        stmt = select(AuditLogORM).order_by(AuditLogORM.timestamp.desc())
        count_stmt = select(func.count()).select_from(AuditLogORM)

        total_result = await self.session.execute(count_stmt)
        total = total_result.scalar_one()

        stmt = stmt.offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        orms = result.scalars().all()

        audit_logs = [to_domain_audit_log(orm) for orm in orms]
        return audit_logs, total
