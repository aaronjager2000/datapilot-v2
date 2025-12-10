from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user, get_jwt_service
from app.core.security import verify_password, get_password_hash
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenResponse
)
from app.schemas.user import UserCreate, UserResponse
from app.schemas.organization import OrganizationCreate
from app.services.auth.jwt import JWTService

router = APIRouter()


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> Any:
    # Check if user already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization for the user
    org = Organization(
        name=user_data.organization_name,
        slug=user_data.organization_name.lower().replace(" ", "-"),
        settings={}
    )
    db.add(org)
    await db.flush()

    # Create user with hashed password
    hashed_password = get_password_hash(user_data.password)

    user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        organization_id=org.id,
        is_active=True,
        is_superuser=False
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)
    await db.refresh(org)

    # Generate JWT token pair
    tokens = await jwt_svc.create_token_pair(
        user_id=user.id,
        organization_id=org.id,
        email=user.email,
        is_superuser=user.is_superuser
    )

    # Create UserResponse without trying to load the organization relationship
    # (the relationship is commented out in the User model)
    user_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.organization_id,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "email_verified": user.email_verified,
        "last_login": user.last_login,
        "oauth_provider": user.oauth_provider,
        "oauth_id": user.oauth_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserResponse.model_validate(user_data)
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> Any:
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == credentials.email)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Verify password
    if not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is inactive"
        )

    # Update last login timestamp
    user.last_login = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(user)  # Refresh to load all attributes after commit

    # Generate JWT token pair
    tokens = await jwt_svc.create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        is_superuser=user.is_superuser
    )

    # Create UserResponse without trying to load the organization relationship
    # (the relationship is commented out in the User model)
    user_data = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "organization_id": user.organization_id,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "email_verified": user.email_verified,
        "last_login": user.last_login,
        "oauth_provider": user.oauth_provider,
        "oauth_id": user.oauth_id,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserResponse.model_validate(user_data)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> Any:
    # Verify refresh token and get new token pair
    tokens = await jwt_svc.refresh_access_token(
        refresh_token=refresh_data.refresh_token,
        user_email="",  # Email is extracted from token
        is_superuser=False  # Will be extracted from token
    )

    if not tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    jwt_svc: JWTService = Depends(get_jwt_service)
) -> None:
    # Revoke all user tokens (force logout from all devices)
    success = await jwt_svc.revoke_all_user_tokens(current_user.id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Logout failed - Redis not available"
        )

    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
) -> Any:
    # Create UserResponse without trying to load the organization relationship
    # (the relationship is commented out in the User model)
    user_data = {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "organization_id": current_user.organization_id,
        "is_active": current_user.is_active,
        "is_superuser": current_user.is_superuser,
        "email_verified": current_user.email_verified,
        "last_login": current_user.last_login,
        "oauth_provider": current_user.oauth_provider,
        "oauth_id": current_user.oauth_id,
        "created_at": current_user.created_at,
        "updated_at": current_user.updated_at,
    }
    return UserResponse.model_validate(user_data)
