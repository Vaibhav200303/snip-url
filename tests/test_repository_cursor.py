import pytest

from app.repositories.url_repository import InvalidCursorError, UrlRepository


def test_cursor_round_trip():
    state = b"opaque-cassandra-paging-state"
    cursor = UrlRepository.encode_cursor(state)
    assert cursor is not None
    assert UrlRepository.decode_cursor(cursor) == state


def test_invalid_cursor_is_rejected():
    with pytest.raises(InvalidCursorError):
        UrlRepository.decode_cursor("not!base64")
