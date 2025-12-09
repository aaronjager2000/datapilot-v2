from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID
import secrets

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import get_password_hash, create_access_token
from app.models.user import User
from app.models.organization import Organization


class InviteService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.invite_expiry_hours = 72  # 3 days

    async def create_invite(
        self,
        email: str,
        organization_id: UUID,
        role_id: UUID,
        invited_by_user_id: UUID
    ) -> dict:
        # Check if user already exists
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        existing_user = result.scalar_one_or_none()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User with this email already exists"
            )

        # Generate secure invite token
        invite_token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(hours=self.invite_expiry_hours)

        # Store invite in database (placeholder - requires Invite model)
        invite_data = {
            "token": invite_token,
            "email": email,
            "organization_id": organization_id,
            "role_id": role_id,
            "invited_by_user_id": invited_by_user_id,
            "expires_at": expires_at,
            "status": "pending"
        }

        # TODO: Save invite to database when Invite model is created
        # invite = Invite(**invite_data)
        # self.db.add(invite)
        # await self.db.commit()

        return invite_data

    async def send_invite_email(
        self,
        email: str,
        invite_token: str,
        organization_name: str,
        invited_by_name: str
    ) -> None:
        # TODO: Implement email sending in Week 4
        invite_url = f"{settings.FRONTEND_URL}/invite/accept?token={invite_token}"
        
        # Placeholder - actual email service implementation
        email_data = {
            "to": email,
            "subject": f"You've been invited to join {organization_name} on Datapilot",
            "body": f"{invited_by_name} has invited you to join {organization_name}. Click here to accept: {invite_url}",
            "invite_url": invite_url,
            "expires_hours": self.invite_expiry_hours
        }
        
        # TODO: Replace with actual email service
        # await email_service.send_invite_email(email_data)
        raise NotImplementedError("Email service not yet implemented")

    async def verify_invite_token(self, token: str) -> dict:
        # TODO: Query database when Invite model is created
        # result = await self.db.execute(
        #     select(Invite).where(Invite.token == token)
        # )
        # invite = result.scalar_one_or_none()
        
        # if not invite:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="Invalid invite token"
        #     )
        
        # if invite.status != "pending":
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Invite has already been used or cancelled"
        #     )
        
        # if invite.expires_at < datetime.now(timezone.utc):
        #     raise HTTPException(
        #         status_code=status.HTTP_400_BAD_REQUEST,
        #         detail="Invite has expired"
        #     )
        
        # return {
        #     "email": invite.email,
        #     "organization_id": invite.organization_id,
        #     "role_id": invite.role_id
        # }
        
        raise NotImplementedError("Invite verification not yet implemented - requires Invite model")

    async def accept_invite(
        self,
        token: str,
        password: str,
        first_name: str,
        last_name: str
    ) -> User:
        # Verify token and get invite details
        invite_data = await self.verify_invite_token(token)
        
        # Create new user
        hashed_password = get_password_hash(password)
        
        new_user = User(
            email=invite_data["email"],
            hashed_password=hashed_password,
            first_name=first_name,
            last_name=last_name,
            organization_id=invite_data["organization_id"],
            is_active=True,
            is_superuser=False
        )
        
        self.db.add(new_user)
        
        # TODO: Assign role to user when RBAC tables exist
        # user_role = UserRole(
        #     user_id=new_user.id,
        #     role_id=invite_data["role_id"]
        # )
        # self.db.add(user_role)
        
        # TODO: Mark invite as accepted
        # invite.status = "accepted"
        # invite.accepted_at = datetime.now(timezone.utc)
        
        await self.db.commit()
        await self.db.refresh(new_user)
        
        return new_user

    async def cancel_invite(self, token: str, user_id: UUID) -> None:
        # TODO: Implement when Invite model is created
        # result = await self.db.execute(
        #     select(Invite).where(Invite.token == token)
        # )
        # invite = result.scalar_one_or_none()
        
        # if not invite:
        #     raise HTTPException(
        #         status_code=status.HTTP_404_NOT_FOUND,
        #         detail="Invite not found"
        #     )
        
        # # Verify user has permission to cancel (same org)
        # if invite.invited_by_user_id != user_id:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="You can only cancel invites you created"
        #     )
        
        # invite.status = "cancelled"
        # await self.db.commit()
        
        raise NotImplementedError("Cancel invite not yet implemented - requires Invite model")

    async def resend_invite(self, token: str, user_id: UUID) -> dict:
        # TODO: Implement when Invite model is created
        # Verify invite exists and user has permission
        # Generate new token with extended expiry
        # Send new email
        raise NotImplementedError("Resend invite not yet implemented - requires Invite model")


async def get_invite_service(db: AsyncSession) -> InviteService:
    return InviteService(db)