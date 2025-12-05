"""
Configuration Management for Rake Service

Centralized configuration using Pydantic Settings v2. All settings are loaded
from environment variables with type validation and sensible defaults.

Environment Variables:
    See .env.example for all available configuration options.

Example:
    >>> from config import settings
    >>> print(settings.DATABASE_URL)
    postgresql://localhost:5432/forge
"""

from typing import List, Optional, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All settings are loaded from environment variables with automatic type
    conversion and validation. Supports .env file loading in development.

    Attributes:
        VERSION: Application version
        ENVIRONMENT: Runtime environment (development, staging, production)
        LOG_LEVEL: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

        RAKE_HOST: Service bind host
        RAKE_PORT: Service bind port
        ALLOWED_ORIGINS: CORS allowed origins

        DATABASE_URL: PostgreSQL connection string
        DATABASE_POOL_SIZE: Connection pool size
        DATABASE_MAX_OVERFLOW: Max overflow connections

        DATAFORGE_BASE_URL: DataForge API base URL
        DATAFORGE_TIMEOUT: Request timeout in seconds

        OPENAI_API_KEY: OpenAI API key for embeddings
        OPENAI_EMBEDDING_MODEL: Embedding model name
        OPENAI_MAX_TOKENS: Max tokens per embedding request
        ANTHROPIC_API_KEY: Anthropic API key (optional, for future use)

        MAX_WORKERS: Max concurrent pipeline workers
        RETRY_ATTEMPTS: Number of retry attempts for failed operations
        RETRY_DELAY: Base delay between retries (seconds)
        CHUNK_SIZE: Default chunk size in tokens
        CHUNK_OVERLAP: Token overlap between chunks

        SCHEDULER_ENABLED: Enable scheduled jobs
        SCHEDULER_INTERVAL: Default job interval in seconds

    Example:
        >>> from config import settings
        >>> if settings.ENVIRONMENT == "production":
        ...     print("Running in production mode")
    """

    # Application
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = Field(default="development", pattern="^(development|staging|production)$")
    LOG_LEVEL: str = Field(default="INFO", pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")

    # Service
    RAKE_HOST: str = "0.0.0.0"
    RAKE_PORT: int = 8002
    ALLOWED_ORIGINS: Union[str, List[str]] = "http://localhost:3000,http://localhost:5173"

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://localhost:5432/forge",
        description="PostgreSQL connection string (use asyncpg driver)"
    )
    DATABASE_POOL_SIZE: int = Field(default=10, ge=1, le=50)
    DATABASE_MAX_OVERFLOW: int = Field(default=20, ge=0, le=100)

    # DataForge Service
    DATAFORGE_BASE_URL: str = "http://localhost:8001"
    DATAFORGE_TIMEOUT: int = Field(default=30, ge=1, le=300)
    DATAFORGE_DB_PATH: str = Field(
        default="/home/charles/projects/Coding2025/Forge/DataForge/dataforge.db",
        description="Path to DataForge SQLite database for telemetry"
    )

    # OpenAI
    OPENAI_API_KEY: str = Field(default="", description="OpenAI API key for embeddings")
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    OPENAI_MAX_TOKENS: int = Field(default=8191, ge=1, le=8191)
    OPENAI_BATCH_SIZE: int = Field(default=100, ge=1, le=2048)

    # Anthropic (optional, for future use)
    ANTHROPIC_API_KEY: Optional[str] = None

    # JWT Authentication
    JWT_SECRET_KEY: str = Field(
        default="development_secret_key_change_in_production",
        min_length=32,
        description="Secret key for JWT token signing (min 32 characters)"
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        pattern="^(HS256|HS384|HS512|RS256|RS384|RS512)$",
        description="JWT signing algorithm"
    )
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        ge=5,
        le=1440,
        description="Access token expiration in minutes (5 min - 24 hours)"
    )
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = Field(
        default=30,
        ge=1,
        le=90,
        description="Refresh token expiration in days (1-90 days)"
    )

    # SEC EDGAR Configuration
    SEC_EDGAR_USER_AGENT: str = Field(
        default="",
        description="User-Agent for SEC EDGAR (must include contact info)"
    )
    SEC_EDGAR_RATE_LIMIT: float = Field(
        default=0.1,
        ge=0.1,
        le=1.0,
        description="Rate limit delay in seconds (0.1 = 10 req/s max)"
    )

    # URL Scraping Configuration
    URL_SCRAPE_USER_AGENT: str = Field(
        default="Rake/1.0 (Data Ingestion Bot)",
        description="User-Agent for URL scraping"
    )
    URL_SCRAPE_RATE_LIMIT: float = Field(
        default=1.0,
        ge=0.1,
        le=10.0,
        description="Rate limit delay per domain in seconds"
    )
    URL_SCRAPE_MAX_SIZE: int = Field(
        default=10 * 1024 * 1024,  # 10MB
        ge=1024 * 1024,  # Min 1MB
        le=50 * 1024 * 1024,  # Max 50MB
        description="Maximum page size in bytes"
    )
    URL_SCRAPE_TIMEOUT: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Request timeout in seconds"
    )
    URL_SCRAPE_RESPECT_ROBOTS: bool = Field(
        default=True,
        description="Whether to respect robots.txt"
    )

    # API Fetch Configuration
    API_FETCH_USER_AGENT: str = Field(
        default="Rake/1.0 (API Integration Bot)",
        description="User-Agent for API requests"
    )
    API_FETCH_RATE_LIMIT: float = Field(
        default=0.5,
        ge=0.1,
        le=10.0,
        description="Rate limit delay between API requests in seconds"
    )
    API_FETCH_TIMEOUT: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="API request timeout in seconds"
    )
    API_FETCH_MAX_RETRIES: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Maximum retry attempts for failed API requests"
    )
    API_FETCH_MAX_ITEMS: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Maximum items to fetch per API job"
    )
    API_FETCH_VERIFY_SSL: bool = Field(
        default=True,
        description="Verify SSL certificates for API requests"
    )

    # Database Query Configuration
    DB_QUERY_MAX_ROWS: int = Field(
        default=1000,
        ge=1,
        le=10000,
        description="Maximum rows to fetch per database query"
    )
    DB_QUERY_READ_ONLY: bool = Field(
        default=True,
        description="Only allow SELECT queries (security: prevent modifications)"
    )
    DB_QUERY_TIMEOUT: float = Field(
        default=30.0,
        ge=5.0,
        le=120.0,
        description="Database query timeout in seconds"
    )
    DB_QUERY_POOL_SIZE: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Database connection pool size"
    )
    DB_QUERY_MAX_OVERFLOW: int = Field(
        default=10,
        ge=0,
        le=50,
        description="Maximum overflow connections beyond pool size"
    )

    # Pipeline Configuration
    MAX_WORKERS: int = Field(default=4, ge=1, le=32, description="Max concurrent pipeline workers")
    RETRY_ATTEMPTS: int = Field(default=3, ge=1, le=10)
    RETRY_DELAY: float = Field(default=1.0, ge=0.1, le=60.0)
    RETRY_BACKOFF: float = Field(default=2.0, ge=1.0, le=10.0)

    # Chunking Configuration
    CHUNK_SIZE: int = Field(default=500, ge=100, le=2000, description="Default chunk size in tokens")
    CHUNK_OVERLAP: int = Field(default=50, ge=0, le=500, description="Token overlap between chunks")

    # Scheduler
    SCHEDULER_ENABLED: bool = Field(default=False, description="Enable scheduled jobs")
    SCHEDULER_INTERVAL: int = Field(default=3600, ge=60, le=86400, description="Default job interval (seconds)")

    # Model configuration
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    @model_validator(mode="after")
    def normalize_allowed_origins(self):
        """Parse ALLOWED_ORIGINS from comma-separated string or list.

        Ensures ALLOWED_ORIGINS is always a list of strings after validation.

        Returns:
            Self with normalized ALLOWED_ORIGINS
        """
        if isinstance(self.ALLOWED_ORIGINS, str):
            self.ALLOWED_ORIGINS = [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
        return self

    @field_validator("CHUNK_OVERLAP")
    @classmethod
    def validate_chunk_overlap(cls, v: int, info) -> int:
        """Ensure chunk overlap is less than chunk size.

        Args:
            v: Chunk overlap value
            info: Validation context with other field values

        Returns:
            Validated chunk overlap

        Raises:
            ValueError: If overlap >= chunk_size

        Example:
            >>> # CHUNK_SIZE=500, CHUNK_OVERLAP=50 → Valid
            >>> # CHUNK_SIZE=500, CHUNK_OVERLAP=500 → Raises ValueError
        """
        chunk_size = info.data.get("CHUNK_SIZE", 500)
        if v >= chunk_size:
            raise ValueError(f"CHUNK_OVERLAP ({v}) must be less than CHUNK_SIZE ({chunk_size})")
        return v

    @field_validator("OPENAI_API_KEY")
    @classmethod
    def validate_openai_api_key(cls, v: str, info) -> str:
        """Validate OpenAI API key format.

        Args:
            v: API key value
            info: Validation context

        Returns:
            Validated API key

        Raises:
            ValueError: If API key is empty in non-development environments

        Example:
            >>> # In production: empty key raises ValueError
            >>> # In development: empty key is allowed (for testing)
        """
        environment = info.data.get("ENVIRONMENT", "development")
        if not v and environment == "production":
            raise ValueError("OPENAI_API_KEY is required in production environment")
        if v and not v.startswith("sk-"):
            raise ValueError("OPENAI_API_KEY must start with 'sk-'")
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            True if ENVIRONMENT == "production"

        Example:
            >>> from config import settings
            >>> if settings.is_production:
            ...     print("Running in production")
        """
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            True if ENVIRONMENT == "development"

        Example:
            >>> from config import settings
            >>> if settings.is_development:
            ...     print("Debug mode enabled")
        """
        return self.ENVIRONMENT == "development"

    def get_database_url(self, hide_password: bool = True) -> str:
        """Get database URL with optional password masking.

        Args:
            hide_password: If True, mask the password in the URL

        Returns:
            Database URL string

        Example:
            >>> settings.get_database_url(hide_password=True)
            'postgresql+asyncpg://user:***@localhost:5432/forge'
        """
        if not hide_password:
            return self.DATABASE_URL

        # Mask password in URL
        if "@" in self.DATABASE_URL and ":" in self.DATABASE_URL:
            parts = self.DATABASE_URL.split("@")
            if ":" in parts[0]:
                user_pass = parts[0].split(":")
                return f"{user_pass[0]}:***@{parts[1]}"

        return self.DATABASE_URL


# Global settings instance
settings = Settings()


# Log configuration on import (only in development)
if settings.is_development:
    import logging
    logger = logging.getLogger(__name__)
    logger.info(
        "Configuration loaded",
        extra={
            "correlation_id": "config-init",
            "environment": settings.ENVIRONMENT,
            "database": settings.get_database_url(hide_password=True),
            "dataforge": settings.DATAFORGE_BASE_URL
        }
    )
