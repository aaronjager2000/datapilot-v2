from typing import Optional
from uuid import UUID

from fastapi import Request, HTTPException, status, Depends

from app.api.v1.dependencies.auth import get_current_user
from app.models.user import User


def get_organization_id(request: Request) -> UUID:
    org_id = getattr(request.state, "organization_id", None)

    if not org_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No organization context found"
        )

    return org_id


def get_optional_organization_id(request: Request) -> Optional[UUID]:
    return getattr(request.state, "organization_id", None)


def verify_resource_access(
    resource_org_id: UUID,
    current_org_id: UUID,
    is_superuser: bool = False
) -> None:
    if is_superuser:
        return

    if resource_org_id != current_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: resource belongs to different organization"
        )


async def verify_resource_ownership(
    resource_org_id: UUID,
    current_user: User = Depends(get_current_user)
) -> None:
    verify_resource_access(
        resource_org_id,
        current_user.organization_id,
        current_user.is_superuser
    )


def get_current_org_id(
    current_user: User = Depends(get_current_user)
) -> UUID:
    return current_user.organization_id


# Alias for backwards compatibility
get_current_organization_id = get_current_org_id
