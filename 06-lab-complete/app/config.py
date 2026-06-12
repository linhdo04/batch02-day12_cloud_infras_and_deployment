"""Environment-based configuration for the production agent."""
import logging
import os
from dataclasses import dataclass, field


def _as_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "development"))
    debug: bool = field(default_factory=lambda: _as_bool("DEBUG"))

    app_name: str = field(default_factory=lambda: os.getenv("APP_NAME", "Production AI Agent"))
    app_version: str = field(default_factory=lambda: os.getenv("APP_VERSION", "1.0.0"))
    instance_id: str = field(
        default_factory=lambda: os.getenv("INSTANCE_ID", os.getenv("HOSTNAME", "local"))
    )

    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    llm_model: str = field(default_factory=lambda: os.getenv("LLM_MODEL", "mock-llm"))
    enable_docs: bool = field(default_factory=lambda: _as_bool("ENABLE_DOCS", "true"))

    agent_api_key: str = field(
        default_factory=lambda: os.getenv("AGENT_API_KEY", "")
    )
    allowed_origins: list[str] = field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
            if origin.strip()
        ]
    )

    redis_url: str = field(
        default_factory=lambda: os.getenv("REDIS_URL", "redis://localhost:6379/0")
    )
    conversation_ttl_seconds: int = field(
        default_factory=lambda: int(os.getenv("CONVERSATION_TTL_SECONDS", "2592000"))
    )
    conversation_max_messages: int = field(
        default_factory=lambda: int(os.getenv("CONVERSATION_MAX_MESSAGES", "40"))
    )

    rate_limit_per_minute: int = field(
        default_factory=lambda: int(os.getenv("RATE_LIMIT_PER_MINUTE", "10"))
    )
    monthly_budget_usd: float = field(
        default_factory=lambda: float(os.getenv("MONTHLY_BUDGET_USD", "10.0"))
    )

    def validate(self) -> "Settings":
        if self.port <= 0 or self.port > 65535:
            raise ValueError("PORT must be between 1 and 65535")
        if self.rate_limit_per_minute <= 0:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be positive")
        if self.monthly_budget_usd <= 0:
            raise ValueError("MONTHLY_BUDGET_USD must be positive")
        if self.environment == "production" and not self.agent_api_key:
            raise ValueError("AGENT_API_KEY must be set in production")
        if not self.openai_api_key:
            logging.getLogger(__name__).warning("OPENAI_API_KEY is not set; using mock LLM")
        return self


settings = Settings().validate()
