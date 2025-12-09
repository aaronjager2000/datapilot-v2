from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.services.auth.jwt import get_jwt_service, JWTService
from app.models.user import User
from app.models.organization import Organization

security = HTTPBearer()

async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    jwt_svc: JWTService = Depends(get_jwt_service),
) -> dict:
    token = credentials.credentials

    token_data = await jwt_svc.validate_token(token, token_type="access")

    if not token_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return token_data

async def get_current_user(
    token_data: dict = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db)
) -> User:
    user_id = token_data["user_id"]

    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return current_user

async def get_current_superuser(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not a superuser",
        )
    return current_user

async def get_current_organization(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Organization:
    result = await db.execute(
        select(Organization).where(Organization.id == current_user.organization_id)
    )
    organization = result.scalar_one_or_none()
    
    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )
    
    if not organization.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organization is inactive"
        )
    
    return organization


def require_permission(permission: str):
    async def permission_checker(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        has_permission = await check_user_permission(
            db, current_user.id, permission
        )
        
        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission} required"
            )
        
        return current_user
    
    return permission_checker


async def check_user_permission(
    #TODO: Implement this once RBAC is in place
    db: AsyncSession,
    user_id: UUID,
    permission: str
) -> bool:
    # Query user's permissions through roles
    # SELECT 1 FROM permissions p
    # JOIN role_permissions rp ON p.id = rp.permission_id
    # JOIN user_roles ur ON rp.role_id = ur.role_id
    # WHERE ur.user_id = user_id AND p.name = permission
    
    return True


async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    jwt_svc: JWTService = Depends(get_jwt_service),
    db: AsyncSession = Depends(get_db)
) -> Optional[User]:
    if not credentials:
        return None
    
    try:
        token = credentials.credentials
        token_data = await jwt_svc.validate_token(token, token_type="access")
        
        if not token_data:
            return None
        
        result = await db.execute(
            select(User).where(User.id == token_data["user_id"])
        )
        user = result.scalar_one_or_none()
        
        if user and user.is_active:
            return user
        
        return None
    except Exception:
        return None

class PaginationParams:
    def __init__(self, skip: int = 0, limit: int = 100):
        self.skip = max(0, skip)
        self.limit = min(1000, max(1, limit))


async def get_pagination(
    skip: int = 0,
    limit: int = 100
) -> PaginationParams:
    return PaginationParams(skip=skip, limit=limit)