from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.user import User
from app.core.permissions import Permission, has_permission
from app.api.v1.dependencies.auth import get_current_user

def check_permission(permission: Permission):
    async def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        has_perm = await has_permission(current_user, permission.value)

        if not has_perm:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission denied: {permission.value} required"
            )
        
        return current_user
    
    return permission_dependency

def check_any_permission(*permissions: Permission):
    async def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        for perm in permissions:
            has_perm = await has_permission(current_user, perm.value)
            if has_perm:
                return current_user
        
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission denied: requires one of {[p.value for p in permissions]}"
        )
    return permission_dependency

def check_all_permissions(*permissions: Permission):
    async def permission_dependency(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> User:
        if current_user.is_superuser:
            return current_user
        
        for perm in permissions:
            has_perm = await has_permission(current_user, perm.value)
            if not has_perm:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission denied: {perm.value} required"
                )
        
        return current_user
    
    return permission_dependency


# Alias for backwards compatibility
require_permission = check_permission