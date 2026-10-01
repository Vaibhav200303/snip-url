from datetime import UTC, datetime
from typing import Any

from app.config.settings import settings
from app.id_generator.short_code import ShortCodeGenerator
from app.repositories.url_cache import UrlCache
from app.repositories.url_repository import UrlRepository
from app.schemas.url import ShortenUrlRequest, UpdateUrlRequest


class UrlNotFoundError(Exception):
    pass


class CustomAliasAlreadyExistsError(Exception):
    pass


class CodeGenerationError(Exception):
    pass


class UrlService:
    def __init__(
        self,
        repository: UrlRepository,
        short_code_generator: ShortCodeGenerator,
        cache: UrlCache | None = None,
    ):
        self.repository = repository
        self.short_code_generator = short_code_generator
        self.cache = cache or UrlCache()

    @staticmethod
    def serialize(row: Any) -> dict:
        return {
            "short_code": row.short_code,
            "short_url": f"{settings.public_base_url.rstrip('/')}/{row.short_code}",
            "long_url": row.long_url,
            "created_at": row.created_at,
            "expiration_at": row.expiration_at,
            "is_custom": row.is_custom,
            "is_enabled": True if row.is_enabled is None else row.is_enabled,
        }

    def shorten(self, request: ShortenUrlRequest) -> dict:
        created_at = datetime.now(UTC)
        long_url = str(request.long_url)
        if request.custom_alias:
            created = self.repository.create(
                request.custom_alias,
                long_url,
                created_at,
                request.expiration_at,
                True,
            )
            if not created:
                raise CustomAliasAlreadyExistsError("custom alias already exists")
            short_code = request.custom_alias
        else:
            short_code = ""
            for _ in range(settings.generated_code_retries):
                candidate = self.short_code_generator.generate()
                if self.repository.create(
                    candidate, long_url, created_at, request.expiration_at, False
                ):
                    short_code = candidate
                    break
            if not short_code:
                raise CodeGenerationError("could not allocate a unique short code")

        row = self.repository.get_by_short_code(short_code)
        return self.serialize(row)

    def get(self, short_code: str) -> dict:
        row = self.repository.get_by_short_code(short_code)
        if row is None:
            raise UrlNotFoundError("short URL not found")
        return self.serialize(row)

    def list(self, limit: int, cursor: str | None) -> dict:
        rows, next_cursor = self.repository.list(limit, cursor)
        return {"items": [self.serialize(row) for row in rows], "next_cursor": next_cursor}

    def update(self, short_code: str, request: UpdateUrlRequest) -> dict:
        row = self.repository.get_by_short_code(short_code)
        if row is None:
            raise UrlNotFoundError("short URL not found")
        long_url = str(request.long_url) if request.long_url is not None else row.long_url
        expiration_at = (
            None
            if request.clear_expiration
            else request.expiration_at
            if request.expiration_at is not None
            else row.expiration_at
        )
        current_enabled = True if row.is_enabled is None else row.is_enabled
        enabled = request.is_enabled if request.is_enabled is not None else current_enabled
        self.repository.update(row, long_url, expiration_at, enabled)
        self.cache.delete(short_code)
        return self.get(short_code)

    def delete(self, short_code: str) -> None:
        row = self.repository.get_by_short_code(short_code)
        if row is not None:
            self.repository.delete(row)
        self.cache.delete(short_code)
