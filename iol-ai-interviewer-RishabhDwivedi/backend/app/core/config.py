"""
Configuration management using Pydantic Settings
Enhanced for Phase 2 with file upload and CORS settings
"""
from typing import List, Literal
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings and configuration"""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        json_schema_extra={
            'env_parse_none_str': None
        }
    )
    
    # Application
    app_name: str = Field(default="AI Interviewer Phase 2", alias="APP_NAME")
    app_version: str = Field(default="2.0.0", alias="APP_VERSION")
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    log_level: str = "INFO"
    
    # API
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_workers: int = Field(default=4, alias="API_WORKERS")
    
    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://interviewer:password@localhost:5433/interviewer_phase2_db",
        alias="DATABASE_URL"
    )
    database_pool_size: int = 20
    database_max_overflow: int = 10
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6380/0", alias="REDIS_URL")
    redis_max_connections: int = 50
    
    # LLM Configuration
    llm_provider: Literal["azure_openai", "openai", "anthropic"] = "openai"
    
    # Azure OpenAI
    azure_openai_key: str = Field(default="", alias="AZURE_OPENAI_KEY")
    azure_openai_endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    azure_model_gpt_4: str = Field(default="gpt-4o", alias="AZURE_MODEL_GPT_4")
    azure_openai_api_version: str = Field(default="2024-02-15-preview", alias="AZURE_OPENAI_API_VERSION")
    
    # OpenAI (Standard)
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = "gpt-4o-mini"
    openai_max_tokens: int = 2000
    openai_temperature: float = 0.7
    
    # Anthropic
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    anthropic_model: str = "claude-3-sonnet-20240229"
    anthropic_max_tokens: int = 2000
    
    # Interview Configuration
    max_interview_duration_minutes: int = 60
    default_interview_template: str = "backend-engineer"
    enable_follow_up_questions: bool = True
    max_follow_up_depth: int = 3
    
    # Scoring
    scoring_scale_min: int = 1
    scoring_scale_max: int = 5
    
    # Security
    secret_key: str = Field(
        default="change-this-secret-key-in-production",
        alias="SECRET_KEY"
    )
    access_token_expire_minutes: int = 60
    algorithm: str = "HS256"
    
    # CORS
    cors_origins_str: str = Field(default="http://localhost:8501,http://localhost:8502,http://localhost:8503,http://localhost:8504", alias="CORS_ORIGINS")
    cors_allow_credentials: bool = True
    cors_allow_methods_str: str = Field(default="*", alias="CORS_ALLOW_METHODS")
    cors_allow_headers_str: str = Field(default="*", alias="CORS_ALLOW_HEADERS")
    
    # File Upload
    max_resume_size_mb: int = 5
    allowed_resume_formats_str: str = Field(default="pdf,docx,txt", alias="ALLOWED_RESUME_FORMATS")
    upload_dir: str = "./uploads/resumes"
    
    # Storage
    reports_storage_path: str = "./storage/reports"
    transcripts_storage_path: str = "./storage/transcripts"
    
    # Rate Limiting
    rate_limit_per_minute: int = 30
    
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins_str.split(",")]
    
    @property
    def cors_allow_methods(self) -> List[str]:
        """Parse CORS methods"""
        if self.cors_allow_methods_str == "*":
            return ["*"]
        return [method.strip() for method in self.cors_allow_methods_str.split(",")]
    
    @property
    def cors_allow_headers(self) -> List[str]:
        """Parse CORS headers"""
        if self.cors_allow_headers_str == "*":
            return ["*"]
        return [header.strip() for header in self.cors_allow_headers_str.split(",")]
    
    @property
    def allowed_resume_formats(self) -> List[str]:
        """Parse allowed resume formats"""
        return [fmt.strip() for fmt in self.allowed_resume_formats_str.split(",")]
    
    @property
    def database_url_sync(self) -> str:
        """Get synchronous database URL for Alembic"""
        return self.database_url.replace("+asyncpg", "")
    
    @property
    def max_resume_size_bytes(self) -> int:
        """Get max resume size in bytes"""
        return self.max_resume_size_mb * 1024 * 1024


# Global settings instance
settings = Settings()
