from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization
from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    TokenRefreshRequest,
    TokenResponse,
)
from app.schemas.user import UserResponse, UserCreate
from app.core.security import verify_password, hash_password
from app.services.auth.jwt import get_jwt_service, JWTService
from app.api.v1.dependencies.auth import get_current_user


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service),
):
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create organization if provided
    if user_data.organization_name and user_data.organization_slug:
        # Check if organization slug is taken
        org_result = await db.execute(
            select(Organization).where(Organization.slug == user_data.organization_slug)
        )
        existing_org = org_result.scalar_one_or_none()

        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization slug already taken"
            )

        # Create organization
        organization = Organization(
            name=user_data.organization_name,
            slug=user_data.organization_slug,
            is_active=True
        )
        db.add(organization)
        await db.flush()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name and slug required"
        )

    # Create user
    user = User(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=hash_password(user_data.password),
        organization_id=organization.id,
        is_active=True,
        is_superuser=False,
        email_verified=False
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Create tokens
    tokens = await jwt_svc.create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        is_superuser=user.is_superuser
    )

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=LoginResponse)
async def login(
    credentials: LoginRequest,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service),
):
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
            detail="Account is inactive"
        )

    # Create tokens
    tokens = await jwt_svc.create_token_pair(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        is_superuser=user.is_superuser
    )

    return LoginResponse(
        access_token=tokens.access_token,
        refresh_token=tokens.refresh_token,
        token_type=tokens.token_type,
        expires_in=tokens.expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
    jwt_svc: JWTService = Depends(get_jwt_service),
):
    # Verify refresh token and get user
    from app.core.security import verify_token

    token_data = verify_token(request.refresh_token, token_type="refresh")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )

    # Get user from database
    result = await db.execute(
        select(User).where(User.id == token_data.sub)
    )
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )

    # Refresh tokens
    new_tokens = await jwt_svc.refresh_access_token(
        refresh_token=request.refresh_token,
        user_email=user.email,
        is_superuser=user.is_superuser
    )

    if not new_tokens:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )

    return new_tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    current_user: User = Depends(get_current_user),
    jwt_svc: JWTService = Depends(get_jwt_service),
):
    # Revoke all user tokens (force logout from all devices)
    await jwt_svc.revoke_all_user_tokens(current_user.id)

    return None


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    return UserResponse.model_validate(current_user)
