
# JWT Service Layer - Business logic for JWT token operations.



from typing import Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta, timezone

from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_token,
)
from app.core.config import settings
from app.schemas.auth import TokenResponse


class JWTService:
    def __init__(self, redis_client=None):
        self.redis = redis_client

    async def create_token_pair(
        self,
        user_id: UUID,
        organization_id: UUID,
        email: str,
        is_superuser: bool = False
    ) -> TokenResponse:

        # Create access token (short-lived)
        access_token = create_access_token(
            user_id=user_id,
            organization_id=organization_id,
            email=email,
            is_superuser=is_superuser
        )

        # Create refresh token (long-lived)
        refresh_token = create_refresh_token(
            user_id=user_id,
            organization_id=organization_id
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60  # Convert to seconds
        )

    async def refresh_access_token(
        self,
        refresh_token: str,
        user_email: str,
        is_superuser: bool = False
    ) -> Optional[TokenResponse]:

        # Verify the refresh token
        token_data = verify_token(refresh_token, token_type="refresh")

        if not token_data:
            return None

        # Check if token is blacklisted (if Redis is available)
        if self.redis:
            is_blacklisted = await self._is_token_blacklisted(refresh_token)
            if is_blacklisted:
                return None

        # Token is valid - blacklist the old refresh token (token rotation)
        if self.redis:
            await self._blacklist_token(
                token=refresh_token,
                expiry_seconds=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400
            )

        # Create new token pair
        new_tokens = await self.create_token_pair(
            user_id=token_data.sub,
            organization_id=token_data.org_id,
            email=user_email,
            is_superuser=is_superuser
        )

        return new_tokens

    async def revoke_token(self, token: str, token_type: str = "refresh") -> bool:

        if not self.redis:
            # Without Redis, we can't implement token revocation
            return False

        # Verify token is valid before blacklisting
        token_data = verify_token(token, token_type=token_type)
        if not token_data:
            return False

        # Calculate expiry based on token type
        if token_type == "access":
            expiry_seconds = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        else:
            expiry_seconds = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400

        # Add to blacklist
        await self._blacklist_token(token, expiry_seconds)
        return True

    async def revoke_all_user_tokens(self, user_id: UUID) -> bool:

        if not self.redis:
            return False

        # Store a "revoke all" timestamp for this user
        # Any token issued before this timestamp is considered invalid
        key = f"user_revoke_all:{user_id}"
        timestamp = datetime.now(timezone.utc).isoformat()

        await self.redis.set(
            key,
            timestamp,
            ex=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400  # Keep for max token lifetime
        )

        return True

    async def is_user_tokens_revoked(self, user_id: UUID, token_issued_at: int) -> bool:

        if not self.redis:
            return False

        key = f"user_revoke_all:{user_id}"
        revoke_timestamp = await self.redis.get(key)

        if not revoke_timestamp:
            return False

        # Parse timestamps and compare
        # Handle both bytes and str return from Redis
        if isinstance(revoke_timestamp, bytes):
            revoke_timestamp = revoke_timestamp.decode()
        revoke_dt = datetime.fromisoformat(revoke_timestamp)
        token_dt = datetime.fromtimestamp(token_issued_at, tz=timezone.utc)

        return token_dt < revoke_dt

    async def _blacklist_token(self, token: str, expiry_seconds: int) -> None:

        if not self.redis:
            return

        key = f"blacklist:{token}"
        await self.redis.set(key, "1", ex=expiry_seconds)

    async def _is_token_blacklisted(self, token: str) -> bool:

        if not self.redis:
            return False

        key = f"blacklist:{token}"
        result = await self.redis.get(key)
        return result is not None

    async def validate_token(
        self,
        token: str,
        token_type: str = "access"
    ) -> Optional[dict]:

        # Verify token signature and expiration
        token_data = verify_token(token, token_type=token_type)
        if not token_data:
            return None

        # Check if token is blacklisted
        if self.redis:
            is_blacklisted = await self._is_token_blacklisted(token)
            if is_blacklisted:
                return None

            # Check if user's tokens have been globally revoked
            # Note: This requires the token to have an 'iat' (issued at) claim
            # which we added in the security.py hardening
            if token_data.iat is not None:
                is_revoked = await self.is_user_tokens_revoked(
                    user_id=token_data.sub,
                    token_issued_at=token_data.iat
                )
                if is_revoked:
                    return None

        # Token is valid
        return {
            "user_id": token_data.sub,
            "org_id": token_data.org_id,
            "email": token_data.email,
            "is_superuser": token_data.is_superuser,
            "type": token_data.type
        }


# Singleton instance (can be initialized with Redis client in app startup)
jwt_service = JWTService()


def get_jwt_service() -> JWTService:

    return jwt_service


# Alias for backwards compatibility
decode_token = verify_token
