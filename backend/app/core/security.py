#this is my favorite file to write lolololol

#if ur reading this, this bitch is for password hashing, verification, JWT token creation + validation, and payload encoding/decoding, some real G shit right here

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from uuid import UUID
import secrets

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings
from app.schemas.auth import TokenPayload

# Password hashing context - using bcrypt with increased rounds for extra security
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12  # Increased from default 10 for better security
)

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(
    user_id: UUID,
    organization_id: UUID,
    email: str,
    is_superuser: bool = False,
    expires_delta: Optional[timedelta] = None
) -> str:
    
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "email": email,
        "is_superuser": is_superuser,
        "exp": int(expire.timestamp()),  # Convert to Unix timestamp
        "iat": int(now.timestamp()),      # Issued at timestamp
        "jti": secrets.token_urlsafe(32), # Unique token ID for revocation
        "aud": settings.APP_NAME,          # Audience claim
        "type": "access"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def create_refresh_token(
    user_id: UUID,
    organization_id: UUID,
    expires_delta: Optional[timedelta] = None
) -> str:
    
    now = datetime.now(timezone.utc)

    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode = {
        "sub": str(user_id),
        "org_id": str(organization_id),
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(32),  # For token rotation/revocation
        "aud": settings.APP_NAME,
        "type": "refresh"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )

    return encoded_jwt


def decode_token(token: str) -> Optional[TokenPayload]:
    try:
        # Decode with audience validation
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.APP_NAME,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True,
                "require": ["sub", "org_id", "exp", "type"]
            }
        )

        user_id = payload.get("sub")
        org_id = payload.get("org_id")
        exp = payload.get("exp")
        token_type = payload.get("type")

        if user_id is None or org_id is None:
            return None

        # Validate UUIDs
        try:
            user_uuid = UUID(user_id)
            org_uuid = UUID(org_id)
        except (ValueError, AttributeError):
            return None

        token_data = TokenPayload(
            sub=user_uuid,
            org_id=org_uuid,
            exp=exp,
            type=token_type,
            email=payload.get("email"),
            is_superuser=payload.get("is_superuser", False)
        )
        return token_data
    except JWTError:
        return None
    except Exception:
        return None

def verify_token(token: str, token_type: str = "access") -> Optional[TokenPayload]:
    token_data = decode_token(token)
    if token_data is None:
        return None
    if token_data.type != token_type:
        return None

    return token_data


def create_email_verification_token(email: str) -> str:
    """Create a secure email verification token (24 hour expiry)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=24)

    to_encode = {
        "sub": email,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(16),
        "aud": settings.APP_NAME,
        "type": "email_verification"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_email_token(token: str) -> Optional[str]:
    """Verify email verification token with security checks."""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.APP_NAME,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True
            }
        )

        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "email_verification" or not email:
            return None

        return email
    except JWTError:
        return None
    except Exception:
        return None

def create_password_reset_token(email: str) -> str:
    """Create a secure password reset token (1 hour expiry - short for security)."""
    now = datetime.now(timezone.utc)
    expire = now + timedelta(hours=1)

    to_encode = {
        "sub": email,
        "exp": int(expire.timestamp()),
        "iat": int(now.timestamp()),
        "jti": secrets.token_urlsafe(16),
        "aud": settings.APP_NAME,
        "type": "password_reset"
    }

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM
    )
    return encoded_jwt

def verify_password_reset_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            audience=settings.APP_NAME,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_aud": True
            }
        )

        email = payload.get("sub")
        token_type = payload.get("type")

        if token_type != "password_reset" or not email:
            return None

        return email

    except JWTError:
        return None
    except Exception:
        return None