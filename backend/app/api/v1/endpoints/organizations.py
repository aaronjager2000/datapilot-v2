from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies.auth import get_current_user
from app.api.v1.dependencies.permissions import check_permission
from app.core.permissions import Permission
from app.db.session import get_db
from app.models.user import User
from app.schemas.organization import OrganizationResponse, OrganizationUpdate
from app.services.organization import OrganizationService, get_organization_service

router = APIRouter()


@router.get("/me", response_model=OrganizationResponse)
async def get_current_organization(
    current_user: User = Depends(get_current_user),
    org_service: OrganizationService = Depends(get_organization_service)
) -> Any:
    organization = await org_service.get_by_id(current_user.organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return OrganizationResponse.model_validate(organization)


@router.get("/{organization_id}", response_model=OrganizationResponse)
async def get_organization(
    organization_id: UUID,
    current_user: User = Depends(check_permission(Permission.ORG_READ)),
    org_service: OrganizationService = Depends(get_organization_service)
) -> Any:
    # Superusers can view any organization
    if not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot view other organizations"
        )

    organization = await org_service.get_by_id(organization_id)

    if not organization:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization not found"
        )

    return OrganizationResponse.model_validate(organization)


@router.patch("/me", response_model=OrganizationResponse)
async def update_current_organization(
    update_data: OrganizationUpdate,
    current_user: User = Depends(check_permission(Permission.ORG_UPDATE)),
    org_service: OrganizationService = Depends(get_organization_service)
) -> Any:
    organization = await org_service.update(
        current_user.organization_id,
        update_data
    )

    return OrganizationResponse.model_validate(organization)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
@router.put("/{organization_id}", response_model=OrganizationResponse)
async def update_organization(
    organization_id: UUID,
    update_data: OrganizationUpdate,
    current_user: User = Depends(check_permission(Permission.ORG_UPDATE)),
    org_service: OrganizationService = Depends(get_organization_service)
) -> Any:
    # Only superusers can update other organizations
    if not current_user.is_superuser and current_user.organization_id != organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: cannot update other organizations"
        )

    organization = await org_service.update(organization_id, update_data)

    return OrganizationResponse.model_validate(organization)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization(
    organization_id: UUID,
    current_user: User = Depends(check_permission(Permission.ORG_DELETE)),
    org_service: OrganizationService = Depends(get_organization_service)
) -> None:
    # Only superusers can delete organizations
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: only superusers can delete organizations"
        )

    await org_service.delete(organization_id)

    return None
