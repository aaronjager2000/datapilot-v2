"""
Role API endpoints.

Handles role CRUD operations, permission assignments, and user role management
within organizations.
"""

import logging
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.db.session import get_db
from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.tenant import get_current_organization_id
from app.api.v1.dependencies.permissions import require_permission
from app.models import User, Role, Permission
from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
    RoleResponse,
    RoleWithPermissions,
    RoleListResponse,
    AssignPermissionRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_permission("role:manage"))]
)
async def create_role(
    role_data: RoleCreate,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new role for the organization.
    
    Requires `role:manage` permission.
    """
    # Check if role name already exists in this organization
    existing = await db.execute(
        select(Role).where(
            and_(
                Role.organization_id == organization_id,
                Role.name == role_data.name
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role '{role_data.name}' already exists in this organization"
        )
    
    # Create role
    role = Role(
        organization_id=organization_id,
        name=role_data.name,
        description=role_data.description,
        is_default=role_data.is_default,
        is_system=False  # User-created roles are never system roles
    )
    
    db.add(role)
    await db.flush()
    
    # Assign permissions
    if role_data.permission_codes:
        for perm_code in role_data.permission_codes:
            perm_result = await db.execute(
                select(Permission).where(Permission.code == perm_code)
            )
            permission = perm_result.scalar_one_or_none()
            if permission:
                role.add_permission(permission)
            else:
                logger.warning(f"Permission {perm_code} not found, skipping")
    
    await db.commit()
    await db.refresh(role)
    
    logger.info(f"Created role {role.id} '{role.name}' in org {organization_id}")
    
    return RoleResponse.from_orm(role)


@router.get(
    "",
    response_model=RoleListResponse,
    dependencies=[Depends(require_permission("role:view"))]
)
async def list_roles(
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000)
):
    """
    List all roles in the organization.
    """
    # Build query
    query = select(Role).where(Role.organization_id == organization_id)
    query = query.order_by(Role.is_system.desc(), Role.name)
    
    # Get total count
    count_query = select(func.count()).select_from(Role).where(
        Role.organization_id == organization_id
    )
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Get roles
    query = query.offset(skip).limit(limit)
    result = await db.execute(query)
    roles = result.scalars().all()
    
    return RoleListResponse(
        roles=[RoleResponse.from_orm(r) for r in roles],
        total=total
    )


@router.get(
    "/{role_id}",
    response_model=RoleWithPermissions,
    dependencies=[Depends(require_permission("role:view"))]
)
async def get_role(
    role_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a role by ID with its permissions.
    """
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == role_id,
                Role.organization_id == organization_id
            )
        )
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    
    return RoleWithPermissions.from_orm(role)


@router.put(
    "/{role_id}",
    response_model=RoleResponse,
    dependencies=[Depends(require_permission("role:manage"))]
)
async def update_role(
    role_id: UUID,
    role_data: RoleUpdate,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a role.
    
    System roles cannot be modified.
    """
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == role_id,
                Role.organization_id == organization_id
            )
        )
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be modified"
        )
    
    # Update fields
    update_data = role_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(role, field, value)
    
    await db.commit()
    await db.refresh(role)
    
    logger.info(f"Updated role {role_id} in org {organization_id}")
    
    return RoleResponse.from_orm(role)


@router.delete(
    "/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_permission("role:manage"))]
)
async def delete_role(
    role_id: UUID,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a role.
    
    System roles and roles with assigned users cannot be deleted.
    """
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == role_id,
                Role.organization_id == organization_id
            )
        )
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be deleted"
        )
    
    if role.users:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete role with {len(role.users)} assigned users"
        )
    
    await db.delete(role)
    await db.commit()
    
    logger.info(f"Deleted role {role_id} from org {organization_id}")


@router.post(
    "/{role_id}/permissions",
    response_model=RoleWithPermissions,
    dependencies=[Depends(require_permission("role:manage"))]
)
async def add_permission_to_role(
    role_id: UUID,
    permission_data: AssignPermissionRequest,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Add a permission to a role.
    """
    # Get role
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == role_id,
                Role.organization_id == organization_id
            )
        )
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be modified"
        )
    
    # Get permission
    perm_result = await db.execute(
        select(Permission).where(Permission.code == permission_data.permission_code)
    )
    permission = perm_result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission '{permission_data.permission_code}' not found"
        )
    
    # Add permission to role
    if not role.has_permission(permission_data.permission_code):
        role.add_permission(permission)
        await db.commit()
        await db.refresh(role)
        logger.info(f"Added permission {permission_data.permission_code} to role {role_id}")
    
    return RoleWithPermissions.from_orm(role)


@router.delete(
    "/{role_id}/permissions/{permission_code}",
    response_model=RoleWithPermissions,
    dependencies=[Depends(require_permission("role:manage"))]
)
async def remove_permission_from_role(
    role_id: UUID,
    permission_code: str,
    organization_id: UUID = Depends(get_current_organization_id),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a permission from a role.
    """
    # Get role
    result = await db.execute(
        select(Role).where(
            and_(
                Role.id == role_id,
                Role.organization_id == organization_id
            )
        )
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role {role_id} not found"
        )
    
    if role.is_system:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="System roles cannot be modified"
        )
    
    # Get permission
    perm_result = await db.execute(
        select(Permission).where(Permission.code == permission_code)
    )
    permission = perm_result.scalar_one_or_none()
    
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Permission '{permission_code}' not found"
        )
    
    # Remove permission from role
    role.remove_permission(permission)
    await db.commit()
    await db.refresh(role)
    
    logger.info(f"Removed permission {permission_code} from role {role_id}")
    
    return RoleWithPermissions.from_orm(role)
