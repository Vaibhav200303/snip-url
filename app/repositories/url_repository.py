import base64
import hashlib
from datetime import datetime
from typing import Any

from cassandra.cluster import Session

BUCKET = "all"


class InvalidCursorError(ValueError):
    pass


class UrlRepository:
    def __init__(self, session: Session):
        self.session = session
        self._create = session.prepare(
            "INSERT INTO urls (short_code,long_url,created_at,expiration_at,is_custom,is_enabled) "
            "VALUES (?,?,?,?,?,?) IF NOT EXISTS"
        )
        self._get = session.prepare("SELECT * FROM urls WHERE short_code = ?")
        self._delete = session.prepare("DELETE FROM urls WHERE short_code = ?")
        self._update = session.prepare(
            "UPDATE urls SET long_url=?, expiration_at=?, is_enabled=? WHERE short_code=?"
        )
        self._index_create = session.prepare(
            "INSERT INTO urls_by_created "
            "(bucket,created_at,short_code,long_url,expiration_at,is_custom,is_enabled) "
            "VALUES (?,?,?,?,?,?,?)"
        )
        self._index_delete = session.prepare(
            "DELETE FROM urls_by_created WHERE bucket=? AND created_at=? AND short_code=?"
        )
        self._list_first = session.prepare(
            "SELECT * FROM urls_by_created WHERE bucket=?"
        )
        self._destination_create = session.prepare(
            "INSERT INTO urls_by_destination "
            "(destination_hash,created_at,short_code,long_url,expiration_at,is_enabled) "
            "VALUES (?,?,?,?,?,?)"
        )
        self._destination_delete = session.prepare(
            "DELETE FROM urls_by_destination "
            "WHERE destination_hash=? AND created_at=? AND short_code=?"
        )
        self._destination_get = session.prepare(
            "SELECT * FROM urls_by_destination WHERE destination_hash=?"
        )

    def create(
        self,
        short_code: str,
        long_url: str,
        created_at: datetime,
        expiration_at: datetime | None,
        is_custom: bool,
    ) -> bool:
        result = self.session.execute(
            self._create,
            [short_code, long_url, created_at, expiration_at, is_custom, True],
        ).one()
        if not result.applied:
            return False
        self.session.execute(
            self._index_create,
            [BUCKET, created_at, short_code, long_url, expiration_at, is_custom, True],
        )
        self._put_destination(
            short_code, long_url, created_at, expiration_at, is_enabled=True
        )
        return True

    def create_custom(self, **kwargs: Any) -> bool:
        return self.create(is_custom=True, **kwargs)

    def get_by_short_code(self, short_code: str):
        return self.session.execute(self._get, [short_code]).one()

    def get_by_destination(self, long_url: str):
        digest = self.destination_hash(long_url)
        rows = self.session.execute(self._destination_get, [digest])
        # Retain the exact comparison even though SHA-256 collisions are only
        # theoretical for this use case.
        return [row for row in rows if row.long_url == long_url]

    def update(
        self,
        row: Any,
        long_url: str,
        expiration_at: datetime | None,
        is_enabled: bool,
    ) -> None:
        if row.long_url != long_url:
            self._remove_destination(row)
        self.session.execute(
            self._update, [long_url, expiration_at, is_enabled, row.short_code]
        )
        self.session.execute(
            self._index_create,
            [
                BUCKET,
                row.created_at,
                row.short_code,
                long_url,
                expiration_at,
                row.is_custom,
                is_enabled,
            ],
        )
        self._put_destination(
            row.short_code,
            long_url,
            row.created_at,
            expiration_at,
            is_enabled,
        )

    def delete(self, row: Any) -> None:
        self.session.execute(self._delete, [row.short_code])
        self.session.execute(
            self._index_delete, [BUCKET, row.created_at, row.short_code]
        )
        self._remove_destination(row)

    def _put_destination(
        self,
        short_code: str,
        long_url: str,
        created_at: datetime,
        expiration_at: datetime | None,
        is_enabled: bool,
    ) -> None:
        self.session.execute(
            self._destination_create,
            [
                self.destination_hash(long_url),
                created_at,
                short_code,
                long_url,
                expiration_at,
                is_enabled,
            ],
        )

    def _remove_destination(self, row: Any) -> None:
        self.session.execute(
            self._destination_delete,
            [self.destination_hash(row.long_url), row.created_at, row.short_code],
        )

    def list(self, limit: int, cursor: str | None):
        paging_state = self.decode_cursor(cursor) if cursor else None
        statement = self._list_first.bind([BUCKET])
        statement.fetch_size = limit
        try:
            result = self.session.execute(statement, paging_state=paging_state)
        except ValueError as exc:
            raise InvalidCursorError("invalid pagination cursor") from exc
        next_cursor = self.encode_cursor(result.paging_state)
        return list(result.current_rows), next_cursor

    @staticmethod
    def encode_cursor(paging_state: bytes | None) -> str | None:
        if paging_state is None:
            return None
        return base64.urlsafe_b64encode(paging_state).decode().rstrip("=")

    @staticmethod
    def decode_cursor(cursor: str) -> bytes:
        try:
            padded = cursor + "=" * (-len(cursor) % 4)
            return base64.b64decode(padded, altchars=b"-_", validate=True)
        except (ValueError, TypeError) as exc:
            raise InvalidCursorError("invalid pagination cursor") from exc

    @staticmethod
    def destination_hash(long_url: str) -> str:
        return hashlib.sha256(long_url.encode("utf-8")).hexdigest()
