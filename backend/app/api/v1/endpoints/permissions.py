"""
Permission API endpoints.

Permissions are system-wide and can only be viewed (not created/modified).
Permissions are seeded during database initialization.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Permission
from app.schemas.permission import (
    PermissionResponse,
    PermissionListResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "",
    response_model=PermissionListResponse,
    dependencies=[Depends(require_permission("role:view"))]
)
async def list_permissions(
    category: Optional[str] = Query(None, description="Filter by category"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all system permissions.
    
    Permissions are global and defined at system level.
    Requires `role:view` permission.
    """
    # Build query
    query = select(Permission)
    
    if category:
        query = query.where(Permission.category == category)
    
    query = query.order_by(Permission.category, Permission.code)
    
    # Get total count
    count_query = select(func.count()).select_from(Permission)
    if category:
        count_query = count_query.where(Permission.category == category)
    
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get permissions
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    permissions = result.scalars().all()
    
    return PermissionListResponse(
        permissions=[PermissionResponse.from_orm(p) for p in permissions],
        total=total
    )


@router.get(
    "/categories",
    response_model=list[str],
    dependencies=[Depends(require_permission("role:view"))]
)
async def list_permission_categories(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    List all permission categories.
    
    Returns unique list of categories (data, org, user, dashboard, etc.)
    """
    result = await db.execute(
        select(Permission.category).distinct().order_by(Permission.category)
    )
    categories = [row[0] for row in result.all()]
    
    return categories


@router.get(
    "/{permission_id}",
    response_model=PermissionResponse,
    dependencies=[Depends(require_permission("role:view"))]
)
async def get_permission(
    permission_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get a specific permission by ID.
    """
    result = await db.execute(
        select(Permission).where(Permission.id == permission_id)
    )
    permission = result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission {permission_id} not found"
        )
    
    return PermissionResponse.from_orm(permission)
