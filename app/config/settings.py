from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SnipURL"
    app_version: str = "0.1.0"
    environment: str = "development"

    cassandra_host: str = "localhost"
    cassandra_port: int = 9042

    redis_host: str = "localhost"
    redis_port: int = 6379
    public_base_url: str = "http://localhost:8000"
    admin_api_key: str = "change-me"
    short_code_secret: str = ""
    cache_ttl_seconds: int = 3600
    create_rate_limit: int = 30
    redirect_rate_limit: int = 300
    public_analytics_rate_limit: int = 30
    rate_limit_window_seconds: int = 60
    max_page_size: int = 100
    generated_code_retries: int = 5

    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_click_topic: str = "snipurl.clicks"
    kafka_consumer_group: str = "snipurl-analytics"
    analytics_retention_days: int = 365
    analytics_max_range_days: int = 366

    startup_attempts: int = 20
    startup_delay_seconds: float = 2.0
    trusted_hosts: str = "*"
    cors_origins: str = "http://localhost:5173"
    snowflake_worker_id: int = 1
    snowflake_epoch_ms: int = 1767225600000
    snowflake_max_clock_rollback_ms: int = 5

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


def validate_production_settings() -> None:
    if settings.environment.lower() != "production":
        return
    if len(settings.admin_api_key) < 32 or settings.admin_api_key == "change-me":
        raise RuntimeError("ADMIN_API_KEY must be a strong production secret")
    if len(settings.short_code_secret) < 32:
        raise RuntimeError("SHORT_CODE_SECRET must be a strong production secret")
    if settings.trusted_hosts.strip() == "*":
        raise RuntimeError("TRUSTED_HOSTS must be restricted in production")
