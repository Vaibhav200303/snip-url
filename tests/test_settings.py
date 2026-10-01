import pytest

from app.config.settings import settings, validate_production_settings


def test_production_rejects_default_admin_key(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "change-me")
    monkeypatch.setattr(settings, "short_code_secret", "s" * 32)
    monkeypatch.setattr(settings, "trusted_hosts", "example.com")
    with pytest.raises(RuntimeError, match="ADMIN_API_KEY"):
        validate_production_settings()


def test_production_requires_short_code_secret(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "a" * 32)
    monkeypatch.setattr(settings, "short_code_secret", "")
    monkeypatch.setattr(settings, "trusted_hosts", "example.com")
    with pytest.raises(RuntimeError, match="SHORT_CODE_SECRET"):
        validate_production_settings()


def test_production_rejects_wildcard_host(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "a" * 32)
    monkeypatch.setattr(settings, "short_code_secret", "s" * 32)
    monkeypatch.setattr(settings, "trusted_hosts", "*")
    with pytest.raises(RuntimeError, match="TRUSTED_HOSTS"):
        validate_production_settings()


def test_valid_production_settings_pass(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "admin_api_key", "a" * 32)
    monkeypatch.setattr(settings, "short_code_secret", "s" * 32)
    monkeypatch.setattr(settings, "trusted_hosts", "example.com")
    validate_production_settings()
