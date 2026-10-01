import re
from datetime import UTC, date, datetime

from pydantic import BaseModel, Field, HttpUrl, field_validator, model_validator

ALIAS_PATTERN = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
RESERVED_ALIASES = {"admin", "api", "docs", "redoc", "health", "openapi.json"}


class ShortenUrlRequest(BaseModel):
    long_url: HttpUrl
    expiration_at: datetime | None = Field(
        default=None,
    )
    custom_alias: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
    )

    @field_validator("custom_alias")
    @classmethod
    def validate_alias(cls, value: str | None) -> str | None:
        if value is None:
            return value
        if not ALIAS_PATTERN.fullmatch(value):
            raise ValueError("alias may contain only letters, numbers, '_' and '-'")
        if value.lower() in RESERVED_ALIASES:
            raise ValueError("alias is reserved")
        return value

    @field_validator("expiration_at")
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("expiration_at must be in the future")
        return normalized


class ShortenUrlResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: HttpUrl
    created_at: datetime
    expiration_at: datetime | None
    is_custom: bool
    is_enabled: bool


class UpdateUrlRequest(BaseModel):
    long_url: HttpUrl | None = None
    expiration_at: datetime | None = None
    clear_expiration: bool = False
    is_enabled: bool | None = None

    @field_validator("expiration_at")
    @classmethod
    def validate_expiration(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        normalized = value if value.tzinfo else value.replace(tzinfo=UTC)
        if normalized <= datetime.now(UTC):
            raise ValueError("expiration_at must be in the future")
        return normalized

    @model_validator(mode="after")
    def validate_change(self):
        changed = (
            self.long_url is not None
            or self.expiration_at is not None
            or self.clear_expiration
            or self.is_enabled is not None
        )
        if not changed:
            raise ValueError("at least one field must be changed")
        if self.expiration_at is not None and self.clear_expiration:
            raise ValueError(
                "expiration_at and clear_expiration are mutually exclusive"
            )
        return self


class UrlResponse(ShortenUrlResponse):
    pass


class UrlListResponse(BaseModel):
    items: list[UrlResponse]
    next_cursor: str | None


class DailyClicks(BaseModel):
    date: date
    clicks: int


class AnalyticsResponse(BaseModel):
    short_code: str
    total_clicks: int
    daily: list[DailyClicks]


class PublicAnalyticsRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2048)
    from_date: date | None = Field(default=None, alias="from")
    to_date: date | None = Field(default=None, alias="to")

    @field_validator("url")
    @classmethod
    def strip_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("url cannot be empty")
        return value


class PublicAnalyticsResponse(BaseModel):
    matched_links: int
    total_clicks: int
    daily: list[DailyClicks]
