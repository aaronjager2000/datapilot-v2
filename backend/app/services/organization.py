from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Depends

from app.db.session import get_db
from app.models.organization import Organization
from app.models.user import User
from app.schemas.organization import OrganizationCreate, OrganizationUpdate


class OrganizationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, organization_id: UUID) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.id == organization_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Optional[Organization]:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create(self, org_data: OrganizationCreate) -> Organization:
        # Check if slug already exists
        existing_org = await self.get_by_slug(org_data.slug)
        if existing_org:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Organization with this slug already exists"
            )

        organization = Organization(
            name=org_data.name,
            slug=org_data.slug,
            settings=org_data.settings or {}
        )

        self.db.add(organization)
        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def update(
        self,
        organization_id: UUID,
        update_data: OrganizationUpdate
    ) -> Organization:
        organization = await self.get_by_id(organization_id)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Check slug uniqueness if being updated
        if update_data.slug and update_data.slug != organization.slug:
            existing_org = await self.get_by_slug(update_data.slug)
            if existing_org:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Organization with this slug already exists"
                )

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(organization, field, value)

        await self.db.commit()
        await self.db.refresh(organization)

        return organization

    async def delete(self, organization_id: UUID) -> bool:
        organization = await self.get_by_id(organization_id)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Check if organization has users
        result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = result.scalars().all()

        if users:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete organization with {len(users)} active users"
            )

        await self.db.delete(organization)
        await self.db.commit()

        return True

    async def get_user_count(self, organization_id: UUID) -> int:
        result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = result.scalars().all()
        return len(users)

    async def update_settings(
        self,
        organization_id: UUID,
        settings: dict
    ) -> Organization:
        organization = await self.get_by_id(organization_id)

        if not organization:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found"
            )

        # Merge with existing settings
        current_settings = organization.settings or {}
        current_settings.update(settings)
        organization.settings = current_settings

        await self.db.commit()
        await self.db.refresh(organization)

        return organization


async def get_organization_service(db: AsyncSession = Depends(get_db)) -> OrganizationService:
    return OrganizationService(db)
