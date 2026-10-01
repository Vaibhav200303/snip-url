from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from app.api.dependencies.services import (
    get_click_publisher,
    get_redirect_service,
    get_url_service,
)
from app.config.settings import settings
from app.main import app


class UrlService:
    def shorten(self, _payload):
        return {
            "short_code": "abc",
            "short_url": f"{settings.public_base_url}/abc",
            "long_url": "https://example.com",
            "created_at": datetime.now(UTC),
            "expiration_at": None,
            "is_custom": False,
            "is_enabled": True,
        }

    def get(self, _code):
        return self.shorten(None)


class RedirectService:
    def get_long_url(self, _code):
        return "https://example.com"


class Publisher:
    def __init__(self):
        self.codes = []

    def publish(self, code):
        self.codes.append(code)


@asynccontextmanager
async def no_lifespan(_app):
    yield


def make_client():
    publisher = Publisher()
    app.dependency_overrides[get_url_service] = lambda: UrlService()
    app.dependency_overrides[get_redirect_service] = lambda: RedirectService()
    app.dependency_overrides[get_click_publisher] = lambda: publisher
    app.router.lifespan_context = no_lifespan
    return TestClient(app), publisher


def test_create_returns_followable_root_url():
    client, _ = make_client()
    with client:
        response = client.post(
            "/api/v1/urls", json={"long_url": "https://example.com"}
        )
    assert response.status_code == 201
    assert response.json()["short_url"].endswith("/abc")


def test_redirect_publishes_click_event():
    client, publisher = make_client()
    with client:
        response = client.get("/abc", follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "https://example.com"
    assert publisher.codes == ["abc"]


def test_management_endpoint_requires_api_key():
    client, _ = make_client()
    with client:
        unauthorized = client.get("/api/v1/urls/abc")
        authorized = client.get(
            "/api/v1/urls/abc", headers={"X-API-Key": settings.admin_api_key}
        )
    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "unauthorized"
    assert authorized.status_code == 200
