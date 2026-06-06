from datetime import datetime, timezone
import json
from typing import Optional, Dict, Any, List, Tuple
from uuid import uuid4
import structlog

from app.domain.models import AuditLog
from app.domain.repositories import IAuditLogRepository

logger = structlog.get_logger("app.application.audit")


class AuditLoggingService:
    def __init__(self, repository: IAuditLogRepository):
        self.repository = repository

    async def log_action(
        self,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None,
        ip_address: Optional[str] = None,
        client_agent: Optional[str] = None,
        change_diff: Optional[Dict[str, Any]] = None,
    ) -> AuditLog:
        diff_str = json.dumps(change_diff) if change_diff else None
        
        audit_log = AuditLog(
            id=uuid4(),
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            user_role=user_role,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            ip_address=ip_address,
            client_agent=client_agent,
            change_diff=diff_str,
        )

        try:
            saved = await self.repository.add(audit_log)
            logger.info(
                "Audit log entry saved",
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                user_id=user_id,
            )
            return saved
        except Exception as e:
            logger.exception("Failed to write audit log entry", error=str(e))
            raise e

    async def list_logs(self, skip: int = 0, limit: int = 100) -> Tuple[List[AuditLog], int]:
        return await self.repository.list(skip=skip, limit=limit)
