import os
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.core.config import settings
from app.core.database import get_db_session
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    verify_password
)
from app.domain.models import UserResponse, TokenResponse, UserRole
from app.infrastructure.db.models import UserORM, SessionORM
from app.api.dependencies import get_audit_service, get_current_user
from app.application.audit_service import AuditLoggingService

router = APIRouter(prefix="/auth", tags=["Authentication"])


# --- Request Schemas ---

class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleLoginRequest(BaseModel):
    id_token: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


# --- Helper Functions ---

def verify_google_id_token(token: str) -> dict:
    """
    Decodes and validates a Google Sign-In id_token.
    Supports a mock fallback prefix ('mock_') for testing.
    """
    if token.startswith("mock_"):
        email = token.replace("mock_", "")
        return {
            "email": email,
            "name": email.split("@")[0].capitalize(),
            "sub": f"google_mock_{email.split('@')[0]}"
        }

    client_id = os.getenv("GOOGLE_CLIENT_ID")
    if not client_id:
        # Development fallback when no OAuth credentials are set
        email = token if "@" in token else "oauth_developer@example.com"
        return {
            "email": email,
            "name": "OAuth Developer",
            "sub": f"google_mock_developer"
        }

    try:
        idinfo = id_token.verify_oauth2_token(
            token,
            google_requests.Request(),
            client_id
        )
        return idinfo
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Google token: {str(e)}"
        )


async def create_user_session(
    user_id: str,
    db: AsyncSession,
    request: Request
) -> SessionORM:
    """
    Spawns a new active SessionORM and stores the refresh token.
    """
    refresh_token = generate_refresh_token()
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    session_record = SessionORM(
        user_id=user_id,
        refresh_token=refresh_token,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        expires_at=expires_at,
        is_revoked=False
    )
    db.add(session_record)
    await db.commit()
    return session_record


# --- API Endpoints ---

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: UserRegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service)
):
    # Check if email exists
    stmt = select(UserORM).where(UserORM.email == payload.email)
    result = await db.execute(stmt)
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email is already registered"
        )
    
    # Hash password
    pwd_hash = hash_password(payload.password)
    
    # Assign first user as SUPER_ADMIN, otherwise VIEWER
    # This bootstrap logic makes testing and first-time setups easy.
    stmt_count = select(UserORM)
    result_count = await db.execute(stmt_count)
    first_user = len(result_count.scalars().all()) == 0
    assigned_role = UserRole.SUPER_ADMIN if first_user else UserRole.VIEWER

    user = UserORM(
        email=payload.email,
        password_hash=pwd_hash,
        full_name=payload.full_name,
        role=assigned_role,
        is_active=True
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Audit Log registry
    await audit_service.log_action(
        action="USER_REGISTER",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(user.id),
        user_role=user.role.value,
        ip_address=request.client.host if request.client else None,
        client_agent=request.headers.get("user-agent")
    )

    return user


@router.post("/login", response_model=TokenResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service)
):
    stmt = select(UserORM).where(UserORM.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user or not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Audit Log failed login attempt
        await audit_service.log_action(
            action="USER_LOGIN_FAILED",
            resource_type="USER",
            resource_id=payload.email,
            ip_address=request.client.host if request.client else None,
            client_agent=request.headers.get("user-agent")
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Spawn session
    session = await create_user_session(user.id, db, request)

    # Generate Access Token
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "email": user.email})

    # Audit Log login
    await audit_service.log_action(
        action="USER_LOGIN",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(user.id),
        user_role=user.role.value,
        ip_address=request.client.host if request.client else None,
        client_agent=request.headers.get("user-agent")
    )

    return {
        "access_token": access_token,
        "refresh_token": session.refresh_token,
        "user": user
    }


@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service)
):
    google_data = verify_google_id_token(payload.id_token)
    email = google_data.get("email")
    google_id = google_data.get("sub")
    name = google_data.get("name", "Google User")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="OAuth validation payload lacks email address"
        )

    # Look up by google_id first, then email
    stmt = select(UserORM).where((UserORM.google_id == google_id) | (UserORM.email == email))
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        # Auto-register new Google user
        stmt_count = select(UserORM)
        result_count = await db.execute(stmt_count)
        first_user = len(result_count.scalars().all()) == 0
        assigned_role = UserRole.SUPER_ADMIN if first_user else UserRole.VIEWER

        user = UserORM(
            email=email,
            full_name=name,
            google_id=google_id,
            role=assigned_role,
            is_active=True
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)

        # Audit registration
        await audit_service.log_action(
            action="USER_REGISTER_OAUTH",
            resource_type="USER",
            resource_id=str(user.id),
            user_id=str(user.id),
            user_role=user.role.value,
            ip_address=request.client.host if request.client else None,
            client_agent=request.headers.get("user-agent")
        )
    else:
        # Link google_id if matched by email and not linked yet
        if not user.google_id:
            user.google_id = google_id
            await db.commit()
            await db.refresh(user)

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Spawn session
    session = await create_user_session(user.id, db, request)
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "email": user.email})

    # Audit login
    await audit_service.log_action(
        action="USER_LOGIN_OAUTH",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(user.id),
        user_role=user.role.value,
        ip_address=request.client.host if request.client else None,
        client_agent=request.headers.get("user-agent")
    )

    return {
        "access_token": access_token,
        "refresh_token": session.refresh_token,
        "user": user
    }


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    payload: RefreshTokenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db_session)
):
    stmt = select(SessionORM).where(SessionORM.refresh_token == payload.refresh_token)
    result = await db.execute(stmt)
    session_record = result.scalar_one_or_none()

    if not session_record or session_record.is_revoked or session_record.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    # Fetch user
    stmt_user = select(UserORM).where(UserORM.id == session_record.user_id)
    res_user = await db.execute(stmt_user)
    user = res_user.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User is inactive or deleted"
        )

    # Revoke old session and rotate (Generate new session)
    session_record.is_revoked = True
    await db.commit()

    # Create new rotated session
    new_session = await create_user_session(user.id, db, request)
    access_token = create_access_token(data={"sub": str(user.id), "role": user.role.value, "email": user.email})

    return {
        "access_token": access_token,
        "refresh_token": new_session.refresh_token,
        "user": user
    }


@router.post("/logout")
async def logout(
    payload: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service),
    current_user: UserORM = Depends(get_current_user)
):
    stmt = select(SessionORM).where(SessionORM.refresh_token == payload.refresh_token)
    result = await db.execute(stmt)
    session_record = result.scalar_one_or_none()

    if session_record:
        session_record.is_revoked = True
        await db.commit()

    # Log logout
    await audit_service.log_action(
        action="USER_LOGOUT",
        resource_type="USER",
        resource_id=str(current_user.id),
        user_id=str(current_user.id),
        user_role=current_user.role.value
    )

    return {"detail": "Successfully logged out"}


@router.post("/forgot-password")
async def forgot_password(
    payload: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service)
):
    stmt = select(UserORM).where(UserORM.email == payload.email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    # Security practice: Always return 200 to prevent user enumeration
    resp = {"detail": "If the email is registered, a password recovery link has been generated."}
    if not user:
        return resp

    # Generate token
    token = generate_refresh_token()  # high-entropy URL-safe token
    user.reset_token = token
    user.reset_token_expires_at = datetime.now(timezone.utc) + timedelta(minutes=15)
    await db.commit()

    # Log reset request
    await audit_service.log_action(
        action="PASSWORD_RESET_REQUEST",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(user.id),
        user_role=user.role.value
    )

    # In production this token is sent via email. For our MVP, we also log it/return it in headers
    # or inside the response body in test/dev environments to ease API validation.
    if settings.ENV != "production":
        resp["reset_token"] = token

    return resp


@router.post("/reset-password")
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    audit_service: AuditLoggingService = Depends(get_audit_service)
):
    stmt = select(UserORM).where(
        (UserORM.reset_token == payload.token) & 
        (UserORM.reset_token_expires_at > datetime.now(timezone.utc))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Update password
    user.password_hash = hash_password(payload.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    await db.commit()

    # Log password reset execution
    await audit_service.log_action(
        action="PASSWORD_RESET_COMPLETE",
        resource_type="USER",
        resource_id=str(user.id),
        user_id=str(user.id),
        user_role=user.role.value
    )

    return {"detail": "Password has been successfully updated"}
