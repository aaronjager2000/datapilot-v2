from typing import Optional, Dict
from uuid import UUID

from app.core.config import settings

class OAuthService:
    def __init__(self):
        self.google_client_id = settings.GOOGLE_CLIENT_ID
        self.google_client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = f"{settings.FRONTEND_URL}/auth/callback/google"
    
    async def get_google_auth_url(self, state: Optional[str] = None) -> str:
        #TODO: Implement Google OAuth URL generation
        #Will use google-auth library to generate authorization URL
        # URL format: https://accounts.google.com/o/oauth2/v2/auth?...
        raise NotImplementedError("Google OAuth URL generation is not implemented")
    
    async def exchange_code_for_token(
        self,
        code: str,
        provider: str = "google"
    ) -> Dict[str, str]:
        # TODO: Implement OAuth code exchange in Week 4
        # Exchange authorization code for access token
        # Returns: {"access_token": "...", "id_token": "...", "email": "..."}
        raise NotImplementedError("OAuth code exchange not yet implemented")

    async def get_user_info_from_token(
        self,
        access_token: str,
        provider: str = "google"
    ) -> Dict[str, str]:
        # TODO: Implement user info retrieval in Week 4
        # Fetch user profile from OAuth provider
        # Returns: {"email": "...", "name": "...", "picture": "..."}
        raise NotImplementedError("OAuth user info retrieval not yet implemented")

    async def verify_oauth_token(
        self,
        id_token: str,
        provider: str = "google"
    ) -> Optional[Dict[str, str]]:
        # TODO: Implement token verification in Week 4
        # Verify JWT token from OAuth provider
        # Returns user claims if valid, None otherwise
        raise NotImplementedError("OAuth token verification not yet implemented")


oauth_service = OAuthService()


def get_oauth_service() -> OAuthService:
    return oauth_service