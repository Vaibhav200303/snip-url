from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl


class ShortenUrlRequest(BaseModel):
    long_url: HttpUrl
    expires_at: datetime | None = None
    custom_alias: str | None = Field(
        default=None,
        min_length=3,
        max_length=32,
    )


class ShortenUrlResponse(BaseModel):
    short_code: str
    short_url: str
    long_url: HttpUrl