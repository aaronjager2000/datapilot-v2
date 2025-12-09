from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.permissions import check_permission
from app.api.v1.dependencies.tenant import get_current_org_id, verify_resource_access
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.common import MessageResponse
from app.services.user import UserService, get_user_service

router = APIRouter()


@router.get("", response_model=List[UserResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(check_permission(Permission.USER_READ)),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    users = await user_service.get_all_by_organization(
        current_user.organization_id,
        skip=skip,
        limit=limit
    )

    return [UserResponse.model_validate(user) for user in users]


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(check_permission(Permission.USER_READ)),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify user belongs to same organization
    verify_resource_access(
        resource_org_id=user.organization_id,
        current_org_id=current_user.organization_id,
        is_superuser=current_user.is_superuser
    )

    return UserResponse.model_validate(user)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    update_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Users can update their own profile, or need USER_UPDATE permission
    if user_id != current_user.id:
        # Check if user has permission to update other users
        from app.core.permissions import has_permission
        has_perm = await has_permission(current_user, Permission.USER_UPDATE.value)

        if not has_perm and not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: cannot update other users"
            )

    # Verify user belongs to same organization
    verify_resource_access(
        resource_org_id=user.organization_id,
        current_org_id=current_user.organization_id,
        is_superuser=current_user.is_superuser
    )

    updated_user = await user_service.update(user_id, update_data)

    return UserResponse.model_validate(updated_user)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    current_user: User = Depends(check_permission(Permission.USER_DELETE)),
    user_service: UserService = Depends(get_user_service)
) -> None:
    # Cannot delete self
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )

    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify user belongs to same organization
    verify_resource_access(
        resource_org_id=user.organization_id,
        current_org_id=current_user.organization_id,
        is_superuser=current_user.is_superuser
    )

    # Soft delete - deactivate user
    await user_service.deactivate(user_id)

    return None


@router.post("/invite", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    email: str,
    current_user: User = Depends(check_permission(Permission.USER_CREATE)),
    db: AsyncSession = Depends(get_db)
) -> Any:
    # TODO: Check organization user limit when billing is implemented

    # TODO: Implement invite functionality when InviteService is created
    # from app.services.auth.invite import InviteService
    # invite_service = InviteService(db)
    # await invite_service.create_invite(
    #     email=email,
    #     organization_id=current_user.organization_id,
    #     role_id=default_role_id,
    #     invited_by_user_id=current_user.id
    # )
    # await invite_service.send_invite_email(...)

    raise NotImplementedError("User invite requires InviteService and email service - Week 4")


@router.post("/{user_id}/roles", response_model=MessageResponse)
async def assign_role_to_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(check_permission(Permission.ROLE_ASSIGN)),
    user_service: UserService = Depends(get_user_service)
) -> Any:
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify user belongs to same organization
    verify_resource_access(
        resource_org_id=user.organization_id,
        current_org_id=current_user.organization_id,
        is_superuser=current_user.is_superuser
    )

    # Assign role
    await user_service.assign_role(user_id, role_id)

    return MessageResponse(message="Role assigned successfully")


@router.delete("/{user_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_role_from_user(
    user_id: UUID,
    role_id: UUID,
    current_user: User = Depends(check_permission(Permission.ROLE_ASSIGN)),
    user_service: UserService = Depends(get_user_service)
) -> None:
    user = await user_service.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # Verify user belongs to same organization
    verify_resource_access(
        resource_org_id=user.organization_id,
        current_org_id=current_user.organization_id,
        is_superuser=current_user.is_superuser
    )

    # Remove role
    await user_service.remove_role(user_id, role_id)

    return None
