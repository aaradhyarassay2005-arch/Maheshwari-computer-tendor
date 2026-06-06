import logging
from datetime import datetime, timezone
from typing import Optional, List
from uuid import UUID
import psutil
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy import select, func, desc, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.domain.models import UserRole, UserResponse
from app.infrastructure.db.models import UserORM, SessionORM, AuditLogORM, TenderORM
from app.api.dependencies import require_role, get_current_user, get_vector_search_provider, get_audit_service
from app.application.audit_service import AuditLoggingService
from app.infrastructure.vector_search.qdrant import QdrantVectorSearchProvider

router = APIRouter(prefix="/admin", tags=["Super Admin Panel"])
logger = logging.getLogger(__name__)


# --- Response/Request Schemas ---

class UserDetailResponse(BaseModel):
    id: UUID
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    google_id: Optional[str]
    created_at: datetime
    updated_at: datetime
    session_count: int
    action_count: int


class RoleUpdateRequest(BaseModel):
    role: UserRole


class StatusUpdateRequest(BaseModel):
    is_active: bool


class AuditLogResponse(BaseModel):
    id: UUID
    timestamp: datetime
    user_id: Optional[str]
    user_role: Optional[str]
    action: str
    resource_type: str
    resource_id: Optional[str]
    ip_address: Optional[str]
    client_agent: Optional[str]
    change_diff: Optional[str]


class SystemHealthResponse(BaseModel):
    status: str
    cpu_percent: float
    ram_percent: float
    ram_used_gb: float
    ram_total_gb: float
    postgres_status: str
    qdrant_status: str
    timestamp: datetime


class PlatformStatsResponse(BaseModel):
    total_users: int
    active_sessions: int
    total_audit_logs: int
    total_tenders: int
    timestamp: datetime


# --- API Routes ---

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    search: Optional[str] = Query(None),
    role: Optional[UserRole] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    List all users in the directory. (Restricted to ADMIN or higher)
    """
    stmt = select(UserORM)
    
    if search:
        stmt = stmt.where(
            (UserORM.email.icontains(search)) | 
            (UserORM.full_name.icontains(search))
        )
    if role:
        stmt = stmt.where(UserORM.role == role)
        
    stmt = stmt.order_by(desc(UserORM.created_at)).offset(skip).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/users/{id}", response_model=UserDetailResponse)
async def get_user_detail(
    id: UUID,
    db: AsyncSession = Depends(get_db_session),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Detailed profile view of a specific user. (Restricted to ADMIN or higher)
    """
    stmt = select(UserORM).where(UserORM.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        
    # Count sessions
    stmt_sessions = select(func.count(SessionORM.id)).where(SessionORM.user_id == id)
    res_sessions = await db.execute(stmt_sessions)
    session_count = res_sessions.scalar() or 0
    
    # Count audit actions
    stmt_audits = select(func.count(AuditLogORM.id)).where(AuditLogORM.user_id == str(id))
    res_audits = await db.execute(stmt_audits)
    action_count = res_audits.scalar() or 0
    
    return {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role,
        "is_active": user.is_active,
        "google_id": user.google_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
        "session_count": session_count,
        "action_count": action_count
    }


@router.put("/users/{id}/role", response_model=UserResponse)
async def update_user_role(
    id: UUID,
    payload: RoleUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Promote or update a user's authorization role. (Restricted to ADMIN or higher)
    An ADMIN cannot promote someone to SUPER_ADMIN.
    """
    stmt = select(UserORM).where(UserORM.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Constraint: Only SUPER_ADMIN can assign SUPER_ADMIN role
    if payload.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can assign the SUPER_ADMIN role"
        )

    # Log old and new role values
    old_role = user.role.value
    user.role = payload.role
    await db.commit()
    await db.refresh(user)

    await audit_service.log_action(
        action="USER_ROLE_UPDATE",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        change_diff={"old_role": old_role, "new_role": user.role.value}
    )

    return user


@router.put("/users/{id}/status", response_model=UserResponse)
async def update_user_status(
    id: UUID,
    payload: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Suspend or activate user accounts. (Restricted to ADMIN or higher)
    An admin cannot suspend a SUPER_ADMIN.
    """
    stmt = select(UserORM).where(UserORM.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role == UserRole.SUPER_ADMIN and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot suspend a SUPER_ADMIN account"
        )

    old_status = user.is_active
    user.is_active = payload.is_active
    await db.commit()
    await db.refresh(user)

    await audit_service.log_action(
        action="USER_STATUS_UPDATE",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        change_diff={"old_status": old_status, "new_status": user.is_active}
    )

    return user


@router.delete("/users/{id}")
async def delete_user(
    id: UUID,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Permanently delete a user from the platform database. (Restricted to ADMIN/SUPER_ADMIN)
    Only SUPER_ADMIN can delete other ADMINs or SUPER_ADMINs.
    """
    stmt = select(UserORM).where(UserORM.id == id)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    if user.role.level >= current_user.role.level and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions to delete this account level"
        )

    await db.delete(user)
    await db.commit()

    await audit_service.log_action(
        action="USER_DELETED",
        resource_type="USER",
        resource_id=str(id),
        user_id=str(current_user.id),
        user_role=current_user.role.value,
        change_diff={"deleted_email": user.email}
    )

    return {"detail": "User has been permanently deleted"}


@router.get("/audit-logs", response_model=List[AuditLogResponse])
async def list_audit_logs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    action: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db_session),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Query system security audit logs. (Restricted to ADMIN or higher)
    """
    stmt = select(AuditLogORM)
    
    if action:
        stmt = stmt.where(AuditLogORM.action == action)
    if user_id:
        stmt = stmt.where(AuditLogORM.user_id == user_id)
    if resource_type:
        stmt = stmt.where(AuditLogORM.resource_type == resource_type)
        
    stmt = stmt.order_by(desc(AuditLogORM.timestamp)).offset(skip).limit(limit)
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/health", response_model=SystemHealthResponse)
async def system_health(
    db: AsyncSession = Depends(get_db_session),
    qdrant: QdrantVectorSearchProvider = Depends(get_vector_search_provider),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Collect system diagnostics across database connections, CPU/RAM telemetry, and Qdrant.
    """
    # 1. Check PostgreSQL
    pg_status = "HEALTHY"
    try:
        await db.execute(select(1))
    except Exception as e:
        logger.error(f"PostgreSQL health check failed: {str(e)}")
        pg_status = f"UNHEALTHY: {str(e)}"
        
    # 2. Check Qdrant Vector DB
    qdrant_status = "HEALTHY"
    try:
        qdrant._get_client().get_collections()
    except Exception as e:
        logger.error(f"Qdrant health check failed: {str(e)}")
        qdrant_status = f"UNHEALTHY: {str(e)}"

    # 3. CPU/Memory diagnostics
    cpu = psutil.cpu_percent(interval=None)
    mem = psutil.virtual_memory()
    
    overall_status = "HEALTHY"
    if pg_status != "HEALTHY" or qdrant_status != "HEALTHY":
        overall_status = "DEGRADED"

    return {
        "status": overall_status,
        "cpu_percent": cpu,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "postgres_status": pg_status,
        "qdrant_status": qdrant_status,
        "timestamp": datetime.now(timezone.utc)
    }


@router.get("/stats", response_model=PlatformStatsResponse)
async def platform_stats(
    db: AsyncSession = Depends(get_db_session),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Fetch platform-wide statistics. (Restricted to ADMIN or higher)
    """
    # Total Users
    res_users = await db.execute(select(func.count(UserORM.id)))
    total_users = res_users.scalar() or 0

    # Active Sessions
    res_sessions = await db.execute(select(func.count(SessionORM.id)).where(SessionORM.is_revoked == False))
    active_sessions = res_sessions.scalar() or 0

    # Total Audit Logs
    res_audits = await db.execute(select(func.count(AuditLogORM.id)))
    total_audit_logs = res_audits.scalar() or 0

    # Total Ingested Tenders
    res_tenders = await db.execute(select(func.count(TenderORM.id)))
    total_tenders = res_tenders.scalar() or 0

    return {
        "total_users": total_users,
        "active_sessions": active_sessions,
        "total_audit_logs": total_audit_logs,
        "total_tenders": total_tenders,
        "timestamp": datetime.now(timezone.utc)
    }


@router.get("/api-usage")
async def api_usage_telemetry(
    db: AsyncSession = Depends(get_db_session),
    current_user: UserORM = Depends(require_role(UserRole.ADMIN))
):
    """
    Aggregate request frequencies and path distributions from the AuditLogORM table.
    This provides client-side dashboard graphs with actual backend usage metrics.
    """
    # Count requests group by action (e.g. USER_LOGIN, PROJECT_MATCH, etc.)
    stmt = (
        select(AuditLogORM.action, func.count(AuditLogORM.id).label("hits"))
        .group_by(AuditLogORM.action)
        .order_by(desc(text("hits")))
        .limit(10)
    )
    result = await db.execute(stmt)
    actions = [{"action": row[0], "hits": row[1]} for row in result.all()]
    
    # Ingest activity distribution over time (recent 7 days)
    stmt_timeline = (
        select(
            func.date_trunc('day', AuditLogORM.timestamp).label('day'),
            func.count(AuditLogORM.id).label('hits')
        )
        .group_by('day')
        .order_by('day')
        .limit(7)
    )
    result_timeline = await db.execute(stmt_timeline)
    timeline = [
        {"date": row[0].strftime("%Y-%m-%d") if row[0] else "", "hits": row[1]}
        for row in result_timeline.all()
    ]

    return {
        "most_active_actions": actions,
        "timeline_hits": timeline
    }
