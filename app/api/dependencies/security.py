import secrets

from fastapi import Header

from app.config.settings import settings
from app.core.exceptions import InvalidApiKeyError


def require_admin_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key is None or not secrets.compare_digest(x_api_key, settings.admin_api_key):
        raise InvalidApiKeyError("invalid or missing API key")
