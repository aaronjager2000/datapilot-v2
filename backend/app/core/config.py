from pydantic_settings import BaseSettings
from pydantic import field_validator, Field
from typing import Optional, List, Any
import json

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Datapilot"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Database Settings
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis Configuration
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_MAX_CONNECTIONS: int = 50

    # Security & Authentication
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS Settings
    BACKEND_CORS_ORIGINS: List[str] = []

    # File Storage Configuration
    STORAGE_TYPE: str = "local"  # local, s3, r2
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: str = "us-east-1"
    S3_BUCKET_NAME: str = "datapilot-uploads"
    S3_ENDPOINT_URL: Optional[str] = None
    LOCAL_UPLOAD_DIR: str = "./storage/uploads"
    MAX_UPLOAD_SIZE: int = 104857600  # 100MB in bytes

    # Email Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    EMAILS_FROM_EMAIL: str = "noreply@datapilot.com"
    EMAILS_FROM_NAME: str = "Datapilot"

    # Celery Configuration
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"
    CELERY_TASK_ALWAYS_EAGER: bool = False

    # LLM API Keys
    ANTHROPIC_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    DEFAULT_LLM_PROVIDER: str = "anthropic"  # anthropic or openai

    # Stripe (Billing)
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    STRIPE_PRICE_ID_PRO: Optional[str] = None
    STRIPE_PRICE_ID_ENTERPRISE: Optional[str] = None

    # Monitoring & Logging
    LOG_LEVEL: str = "INFO"
    SENTRY_DSN: Optional[str] = None

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 10

    # Superuser (Initial Setup)
    FIRST_SUPERUSER_EMAIL: Optional[str] = None
    FIRST_SUPERUSER_PASSWORD: Optional[str] = None
    FIRST_SUPERUSER_NAME: Optional[str] = None

    # Feature Flags
    ENABLE_WEBHOOKS: bool = True
    ENABLE_AI_INSIGHTS: bool = True
    ENABLE_OAUTH: bool = False

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # WebSocket Configuration
    WS_MESSAGE_QUEUE_SIZE: int = 100
    WS_PING_INTERVAL: int = 30
    WS_PING_TIMEOUT: int = 10

    # Validators
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """Parse CORS origins from JSON string or return as-is if already a list."""
        if isinstance(v, str):
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Fallback to comma-separated values
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v):
        """Ensure database URL is not empty."""
        if not v:
            raise ValueError("DATABASE_URL must be set")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v):
        """Ensure SECRET_KEY is strong enough."""
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters long")
        return v

    # Computed Properties
    @property
    def database_url_sync(self) -> str:
        """Convert async database URL to sync version for Alembic."""
        return self.DATABASE_URL.replace("+asyncpg", "").replace("+aiomysql", "")

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.ENVIRONMENT.lower() in ["development", "dev", "local"]

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.ENVIRONMENT.lower() in ["production", "prod"]

    # Config
    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }

# Global instance
settings = Settings()