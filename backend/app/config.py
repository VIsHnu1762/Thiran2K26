"""
BillAgent Pro - Application Configuration
==========================================
Centralized configuration using Pydantic Settings.
Loads values from environment variables and .env file.
"""

from functools import lru_cache
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # -------------------------------------------------------------------------
    # Database Configuration
    # -------------------------------------------------------------------------
    postgres_host: str = Field(default="localhost", description="PostgreSQL host")
    postgres_port: int = Field(default=5432, description="PostgreSQL port")
    postgres_db: str = Field(default="billagent", description="Database name")
    postgres_user: str = Field(default="billagent", description="Database user")
    postgres_password: str = Field(default="billagent_dev_password", description="Database password")
    
    @property
    def database_url(self) -> str:
        """Async database URL for SQLAlchemy."""
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    @property
    def database_url_sync(self) -> str:
        """Sync database URL for Alembic migrations."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
    
    # -------------------------------------------------------------------------
    # Redis Configuration
    # -------------------------------------------------------------------------
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, description="Redis port")
    redis_password: Optional[str] = Field(default=None, description="Redis password")
    
    @property
    def redis_url(self) -> str:
        """Redis URL for Celery and caching."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/0"
        return f"redis://{self.redis_host}:{self.redis_port}/0"
    
    # -------------------------------------------------------------------------
    # OCR API Keys
    # -------------------------------------------------------------------------
    mistral_api_key: Optional[str] = Field(default=None, description="Mistral OCR API key")
    openai_api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    google_api_key: Optional[str] = Field(default=None, description="Google Gemini API key")
    
    # -------------------------------------------------------------------------
    # OCR Configuration
    # -------------------------------------------------------------------------
    ocr_primary_engine: str = Field(
        default="mistral",
        description="Primary OCR engine (mistral, gpt4, gemini)"
    )
    ocr_fallback_engine: str = Field(
        default="gpt4",
        description="Fallback OCR engine (mistral, gpt4, gemini)"
    )
    ocr_confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score to accept OCR result"
    )
    ocr_max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retry attempts per OCR engine"
    )
    ocr_timeout_seconds: float = Field(
        default=60.0,
        description="OCR request timeout in seconds"
    )
    
    # Mistral OCR specific
    mistral_model: str = Field(
        default="pixtral-large-latest",
        description="Mistral model for OCR"
    )
    
    # OpenAI specific
    openai_model: str = Field(
        default="gpt-4o",
        description="OpenAI model for OCR fallback"
    )
    
    # -------------------------------------------------------------------------
    # Application Settings
    # -------------------------------------------------------------------------
    environment: str = Field(default="development", description="Environment name")
    debug: bool = Field(default=True, description="Debug mode")
    api_v1_prefix: str = Field(default="/api/v1", description="API version prefix")
    project_name: str = Field(default="BillAgent Pro", description="Project name")
    
    # CORS
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:5173",
        description="Comma-separated CORS origins"
    )
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins as a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]
    
    # -------------------------------------------------------------------------
    # Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT"
    )
    access_token_expire_minutes: int = Field(default=30, description="Access token TTL")
    refresh_token_expire_days: int = Field(default=7, description="Refresh token TTL")
    
    # Rate Limiting
    rate_limit_per_minute: int = Field(
        default=100,
        description="Max API requests per minute per client"
    )
    rate_limit_burst_size: int = Field(
        default=20,
        description="Burst size for rate limiting"
    )
    
    # Sentry (Error Monitoring)
    sentry_dsn: Optional[str] = Field(
        default=None,
        description="Sentry DSN for error tracking"
    )
    
    # -------------------------------------------------------------------------
    # File Storage
    # -------------------------------------------------------------------------
    upload_dir: str = Field(default="./uploads", description="Upload directory")
    max_file_size_mb: int = Field(default=10, description="Max file size in MB")
    
    @property
    def max_file_size_bytes(self) -> int:
        """Max file size in bytes."""
        return self.max_file_size_mb * 1024 * 1024
    
    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v.lower()


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure settings are loaded only once.
    """
    return Settings()


# Export settings instance for convenience
settings = get_settings()
