from typing import Optional, List
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status, Depends

from app.core.security import get_password_hash, verify_password
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate, PasswordChange


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def get_all_by_organization(
        self,
        organization_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> List[User]:
        result = await self.db.execute(
            select(User)
            .where(User.organization_id == organization_id)
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create(
        self,
        user_data: UserCreate,
        organization_id: UUID
    ) -> User:
        # Check if user already exists
        existing_user = await self.get_by_email(user_data.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # Hash password
        hashed_password = get_password_hash(user_data.password)

        user = User(
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            organization_id=organization_id,
            is_active=True,
            is_superuser=False
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def update(
        self,
        user_id: UUID,
        update_data: UserUpdate
    ) -> User:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Check email uniqueness if being updated
        if update_data.email and update_data.email != user.email:
            existing_user = await self.get_by_email(update_data.email)
            if existing_user:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already in use"
                )

        # Update only provided fields
        update_dict = update_data.model_dump(exclude_unset=True)

        for field, value in update_dict.items():
            setattr(user, field, value)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def change_password(
        self,
        user_id: UUID,
        password_data: PasswordChange
    ) -> User:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # Verify current password
        if not verify_password(password_data.current_password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )

        # Hash and set new password
        user.hashed_password = get_password_hash(password_data.new_password)

        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def delete(self, user_id: UUID) -> bool:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        await self.db.delete(user)
        await self.db.commit()

        return True

    async def activate(self, user_id: UUID) -> User:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.is_active = True
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def deactivate(self, user_id: UUID) -> User:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        user.is_active = False
        await self.db.commit()
        await self.db.refresh(user)

        return user

    async def count_by_organization(self, organization_id: UUID) -> int:
        result = await self.db.execute(
            select(User).where(User.organization_id == organization_id)
        )
        users = result.scalars().all()
        return len(users)

    async def assign_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Assign a role to a user."""
        from app.models import Role
        
        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get role
        role_result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Verify role belongs to same organization
        if role.organization_id != user.organization_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role and user must belong to same organization"
            )
        
        # Assign role if not already assigned
        if role not in user.roles:
            user.roles.append(role)
            await self.db.commit()
        
        return True

    async def remove_role(self, user_id: UUID, role_id: UUID) -> bool:
        """Remove a role from a user."""
        from app.models import Role
        
        user = await self.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get role
        role_result = await self.db.execute(
            select(Role).where(Role.id == role_id)
        )
        role = role_result.scalar_one_or_none()
        
        if not role:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Role not found"
            )
        
        # Remove role if assigned
        if role in user.roles:
            user.roles.remove(role)
            await self.db.commit()
            return True
        
        return False

    async def grant_permission(self, user_id: UUID, permission_code: str) -> bool:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # TODO: Implement when RBAC tables are created
        # Permission overrides allow granting specific permissions to users
        # outside of their role permissions
        # user_permission = UserPermission(
        #     user_id=user_id,
        #     permission_code=permission_code
        # )
        # self.db.add(user_permission)
        # await self.db.commit()

        raise NotImplementedError("Permission grants require RBAC tables - Week 3")

    async def revoke_permission(self, user_id: UUID, permission_code: str) -> bool:
        user = await self.get_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        # TODO: Implement when RBAC tables are created
        # result = await self.db.execute(
        #     select(UserPermission).where(
        #         UserPermission.user_id == user_id,
        #         UserPermission.permission_code == permission_code
        #     )
        # )
        # user_permission = result.scalar_one_or_none()
        # if user_permission:
        #     await self.db.delete(user_permission)
        #     await self.db.commit()
        #     return True

        raise NotImplementedError("Permission revocation requires RBAC tables - Week 3")


async def get_user_service(db: AsyncSession = Depends(get_db)) -> UserService:
    return UserService(db)
