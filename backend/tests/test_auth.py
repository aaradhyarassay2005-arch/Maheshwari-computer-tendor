import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.infrastructure.db.models import UserORM, SessionORM
from app.core.security import verify_password


@pytest.mark.asyncio
async def test_user_registration_success(client: AsyncClient, db_session: AsyncSession):
    # Register first user (automatically assigned SUPER_ADMIN)
    payload = {
        "email": "superadmin@example.com",
        "password": "securepassword123",
        "full_name": "Super Admin User"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == payload["email"]
    assert data["full_name"] == payload["full_name"]
    assert "id" in data

    # Verify database entry and password hashing
    stmt = select(UserORM).where(UserORM.email == payload["email"])
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.role.value == "SUPER_ADMIN"
    assert verify_password(payload["password"], user.password_hash) is True

    # Register second user (assigned VIEWER)
    payload_viewer = {
        "email": "viewer@example.com",
        "password": "anotherpassword123",
        "full_name": "Viewer User"
    }
    response_viewer = await client.post("/api/v1/auth/register", json=payload_viewer)
    assert response_viewer.status_code == 201
    data_viewer = response_viewer.json()
    assert data_viewer["email"] == payload_viewer["email"]
    
    stmt_viewer = select(UserORM).where(UserORM.email == payload_viewer["email"])
    res_viewer = await db_session.execute(stmt_viewer)
    user_viewer = res_viewer.scalar_one_or_none()
    assert user_viewer.role.value == "VIEWER"


@pytest.mark.asyncio
async def test_user_registration_duplicate_email(client: AsyncClient, db_session: AsyncSession):
    # Register once
    payload = {
        "email": "duplicate@example.com",
        "password": "securepassword123",
        "full_name": "User One"
    }
    res1 = await client.post("/api/v1/auth/register", json=payload)
    assert res1.status_code == 201

    # Try registering with the same email
    res2 = await client.post("/api/v1/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"]


@pytest.mark.asyncio
async def test_user_login_flow(client: AsyncClient, db_session: AsyncSession):
    # Setup user
    register_payload = {
        "email": "login_user@example.com",
        "password": "mypassword123",
        "full_name": "Login User"
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    # Failed login (wrong password)
    login_payload_fail = {
        "email": "login_user@example.com",
        "password": "wrongpassword"
    }
    res_fail = await client.post("/api/v1/auth/login", json=login_payload_fail)
    assert res_fail.status_code == 401

    # Success login
    login_payload_success = {
        "email": "login_user@example.com",
        "password": "mypassword123"
    }
    res_success = await client.post("/api/v1/auth/login", json=login_payload_success)
    assert res_success.status_code == 200
    data = res_success.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == register_payload["email"]

    # Verify session record created in DB
    stmt = select(SessionORM).where(SessionORM.refresh_token == data["refresh_token"])
    result = await db_session.execute(stmt)
    session = result.scalar_one_or_none()
    assert session is not None
    assert session.is_revoked is False


@pytest.mark.asyncio
async def test_google_oauth_mock_login(client: AsyncClient, db_session: AsyncSession):
    # Test Google OAuth login using dev prefix "mock_"
    payload = {
        "id_token": "mock_google_user@example.com"
    }
    response = await client.post("/api/v1/auth/google", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["user"]["email"] == "google_user@example.com"

    # Confirm user created with google_id
    stmt = select(UserORM).where(UserORM.email == "google_user@example.com")
    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()
    assert user is not None
    assert user.google_id == "google_mock_google_user"


@pytest.mark.asyncio
async def test_token_refresh_rotation(client: AsyncClient, db_session: AsyncSession):
    # Register and Login
    register_payload = {
        "email": "refresh_user@example.com",
        "password": "password123",
        "full_name": "Refresh User"
    }
    await client.post("/api/v1/auth/register", json=register_payload)
    
    login_res = await client.post("/api/v1/auth/login", json={
        "email": "refresh_user@example.com",
        "password": "password123"
    })
    tokens = login_res.json()
    refresh_token = tokens["refresh_token"]

    # Perform refresh
    refresh_res = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert new_tokens["access_token"] != tokens["access_token"]
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # Verify old session was revoked in DB
    stmt_old = select(SessionORM).where(SessionORM.refresh_token == refresh_token)
    res_old = await db_session.execute(stmt_old)
    session_old = res_old.scalar_one_or_none()
    assert session_old.is_revoked is True

    # Verify new session is active
    stmt_new = select(SessionORM).where(SessionORM.refresh_token == new_tokens["refresh_token"])
    res_new = await db_session.execute(stmt_new)
    session_new = res_new.scalar_one_or_none()
    assert session_new is not None
    assert session_new.is_revoked is False


@pytest.mark.asyncio
async def test_forgot_and_reset_password_flow(client: AsyncClient, db_session: AsyncSession):
    # Register user
    email = "forgot_user@example.com"
    register_payload = {
        "email": email,
        "password": "originalpassword123",
        "full_name": "Forgot Password User"
    }
    await client.post("/api/v1/auth/register", json=register_payload)

    # Request reset token (returned directly in dev/test environment mode)
    forgot_res = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert forgot_res.status_code == 200
    data = forgot_res.json()
    assert "reset_token" in data
    token = data["reset_token"]

    # Execute password reset
    new_pwd = "newsecurepassword123"
    reset_res = await client.post("/api/v1/auth/reset-password", json={
        "token": token,
        "new_password": new_pwd
    })
    assert reset_res.status_code == 200

    # Verify new password works
    login_res = await client.post("/api/v1/auth/login", json={
        "email": email,
        "password": new_pwd
    })
    assert login_res.status_code == 200
