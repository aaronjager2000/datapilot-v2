"""
Authentication Pydantic schemas for request/response validation.
"""

from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field

from app.schemas.common import BaseSchema
from app.schemas.user import UserResponse


# Login Request
class LoginRequest(BaseSchema):
    """Schema for user login."""
    email: EmailStr
    password: str
    remember_me: bool = False


# Token Response
class TokenResponse(BaseSchema):
    """Schema for JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# Token Refresh Request
class TokenRefreshRequest(BaseSchema):
    """Schema for refreshing access token."""
    refresh_token: str


# Token Payload (internal use)
class TokenPayload(BaseSchema):
    """Schema for JWT token payload."""
    sub: UUID  # user_id
    org_id: UUID  # organization_id
    exp: int  # expiration timestamp
    type: str  # "access" or "refresh"
    email: Optional[str] = None
    is_superuser: bool = False
    iat: Optional[int] = None  # issued at timestamp (for revocation checking)
    jti: Optional[str] = None  # JWT ID (unique token identifier)


# Login Response (includes tokens and user info)
class LoginResponse(BaseSchema):
    """Schema for login response with tokens and user data."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


# OAuth Login Request
class OAuthLoginRequest(BaseSchema):
    """Schema for OAuth login."""
    provider: str = Field(..., pattern=r"^(google|github|microsoft)$")
    code: str  # Authorization code from OAuth provider
    redirect_uri: str


# OAuth Callback Request
class OAuthCallbackRequest(BaseSchema):
    """Schema for OAuth callback."""
    code: str
    state: Optional[str] = None


# Logout Request
class LogoutRequest(BaseSchema):
    """Schema for logout (optional - can invalidate tokens)."""
    refresh_token: Optional[str] = None


# Verify Token Request
class VerifyTokenRequest(BaseSchema):
    """Schema for verifying a token."""
    token: str


# Verify Token Response
class VerifyTokenResponse(BaseSchema):
    """Schema for token verification response."""
    valid: bool
    user_id: Optional[UUID] = None
    organization_id: Optional[UUID] = None
    email: Optional[str] = None
    expires_at: Optional[int] = None
