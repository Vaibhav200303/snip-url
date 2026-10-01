import pytest

from app.api.dependencies.security import require_admin_api_key
from app.config.settings import settings
from app.core.exceptions import InvalidApiKeyError


def test_admin_api_key_accepts_configured_secret():
    assert require_admin_api_key(settings.admin_api_key) is None


@pytest.mark.parametrize("key", [None, "wrong"])
def test_admin_api_key_rejects_invalid_secret(key):
    with pytest.raises(InvalidApiKeyError):
        require_admin_api_key(key)
