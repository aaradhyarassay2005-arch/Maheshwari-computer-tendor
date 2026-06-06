import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.db.models import UserORM
from app.domain.models import UserRole


async def get_auth_headers(client: AsyncClient, email: str, role: UserRole, db_session: AsyncSession) -> dict:
    """
    Helper to seed a user with a specific role, log in, and return headers.
    """
    from app.core.security import hash_password
    user = UserORM(
        email=email,
        password_hash=hash_password("password123"),
        full_name=f"Test {role.value}",
        role=role,
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": "password123"
    })
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_admin_endpoints_protection(client: AsyncClient, db_session: AsyncSession):
    # Try accessing admin users as guest (unauthenticated)
    res_guest = await client.get("/api/v1/admin/users")
    assert res_guest.status_code == 418 or res_guest.status_code == 401

    # Seed a VIEWER user
    headers_viewer = await get_auth_headers(client, "viewer_test@example.com", UserRole.VIEWER, db_session)
    
    # Try accessing admin endpoints as VIEWER (should get 403 Forbidden)
    res_viewer = await client.get("/api/v1/admin/users", headers=headers_viewer)
    assert res_viewer.status_code == 403

    # Try accessing admin health as VIEWER
    res_health = await client.get("/api/v1/admin/health", headers=headers_viewer)
    assert res_health.status_code == 403


@pytest.mark.asyncio
async def test_admin_list_users_and_detail(client: AsyncClient, db_session: AsyncSession):
    # Seed an ADMIN user
    headers_admin = await get_auth_headers(client, "admin_test@example.com", UserRole.ADMIN, db_session)

    # List users
    res_list = await client.get("/api/v1/admin/users", headers=headers_admin)
    assert res_list.status_code == 200
    users_data = res_list.json()
    assert len(users_data) >= 1

    # Fetch user detail
    target_user_id = users_data[0]["id"]
    res_detail = await client.get(f"/api/v1/admin/users/{target_user_id}", headers=headers_admin)
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["id"] == target_user_id
    assert "session_count" in detail_data
    assert "action_count" in detail_data


@pytest.mark.asyncio
async def test_admin_update_role_restrictions(client: AsyncClient, db_session: AsyncSession):
    # Seed an ADMIN
    headers_admin = await get_auth_headers(client, "role_admin@example.com", UserRole.ADMIN, db_session)
    
    # Seed a target user (VIEWER)
    target_viewer = UserORM(
        email="target_viewer@example.com",
        full_name="Target Viewer",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(target_viewer)
    await db_session.commit()
    await db_session.refresh(target_viewer)

    # 1. ADMIN promotes VIEWER to MANAGER (Success)
    res_promote = await client.put(
        f"/api/v1/admin/users/{target_viewer.id}/role",
        json={"role": "MANAGER"},
        headers=headers_admin
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["role"] == "MANAGER"

    # 2. ADMIN tries to promote to SUPER_ADMIN (403 Forbidden)
    res_super_fail = await client.put(
        f"/api/v1/admin/users/{target_viewer.id}/role",
        json={"role": "SUPER_ADMIN"},
        headers=headers_admin
    )
    assert res_super_fail.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_role_promotion(client: AsyncClient, db_session: AsyncSession):
    # Seed a SUPER_ADMIN
    headers_super = await get_auth_headers(client, "role_super@example.com", UserRole.SUPER_ADMIN, db_session)
    
    # Seed an ADMIN
    target_admin = UserORM(
        email="target_admin@example.com",
        full_name="Target Admin",
        role=UserRole.ADMIN,
        is_active=True
    )
    db_session.add(target_admin)
    await db_session.commit()
    await db_session.refresh(target_admin)

    # SUPER_ADMIN promotes ADMIN to SUPER_ADMIN (Success)
    res_promote = await client.put(
        f"/api/v1/admin/users/{target_admin.id}/role",
        json={"role": "SUPER_ADMIN"},
        headers=headers_super
    )
    assert res_promote.status_code == 200
    assert res_promote.json()["role"] == "SUPER_ADMIN"


@pytest.mark.asyncio
async def test_admin_update_status_and_delete(client: AsyncClient, db_session: AsyncSession):
    # Seed an ADMIN
    headers_admin = await get_auth_headers(client, "status_admin@example.com", UserRole.ADMIN, db_session)

    # Seed a target user (VIEWER)
    target_user = UserORM(
        email="suspend_target@example.com",
        full_name="Suspend Target",
        role=UserRole.VIEWER,
        is_active=True
    )
    db_session.add(target_user)
    await db_session.commit()
    await db_session.refresh(target_user)

    # Deactivate account (suspend)
    res_suspend = await client.put(
        f"/api/v1/admin/users/{target_user.id}/status",
        json={"is_active": False},
        headers=headers_admin
    )
    assert res_suspend.status_code == 200
    assert res_suspend.json()["is_active"] is False

    # Check database status
    stmt = select(UserORM).where(UserORM.id == target_user.id)
    result = await db_session.execute(stmt)
    u_db = result.scalar_one()
    assert u_db.is_active is False

    # Delete user
    res_delete = await client.delete(
        f"/api/v1/admin/users/{target_user.id}",
        headers=headers_admin
    )
    assert res_delete.status_code == 200

    # Verify deleted from DB
    res_find = await db_session.execute(select(UserORM).where(UserORM.id == target_user.id))
    assert res_find.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_admin_system_diagnostics_and_stats(client: AsyncClient, db_session: AsyncSession):
    # Seed an ADMIN
    headers_admin = await get_auth_headers(client, "telemetry_admin@example.com", UserRole.ADMIN, db_session)

    # Query health diagnostics ping
    res_health = await client.get("/api/v1/admin/health", headers=headers_admin)
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert "status" in health_data
    assert "cpu_percent" in health_data
    assert "postgres_status" in health_data
    assert "qdrant_status" in health_data

    # Query platform stats
    res_stats = await client.get("/api/v1/admin/stats", headers=headers_admin)
    assert res_stats.status_code == 200
    stats_data = res_stats.json()
    assert "total_users" in stats_data
    assert "active_sessions" in stats_data
    assert "total_tenders" in stats_data
