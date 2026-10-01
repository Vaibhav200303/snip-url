import logging
from contextlib import asynccontextmanager
from time import sleep

from cassandra import DriverException
from cassandra.cluster import NoHostAvailable
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse

from app.api.routes.urls import api_router, redirect_router
from app.config.settings import settings
from app.core.exceptions import InvalidApiKeyError
from app.database.cassandra.connection import cassandra_connection
from app.database.cassandra.schema import create_keyspace, create_tables
from app.repositories.url_repository import InvalidCursorError
from app.services.analytics_service import AnalyticsRangeError
from app.services.click_publisher import ClickPublisher
from app.services.rate_limiter import RateLimitExceededError
from app.services.redirect_service import (
    UrlDisabledError,
    UrlExpiredError,
)
from app.services.redirect_service import (
    UrlNotFoundError as RedirectUrlNotFoundError,
)
from app.services.url_service import (
    CodeGenerationError,
    CustomAliasAlreadyExistsError,
    UrlNotFoundError,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)
click_publisher = ClickPublisher()


def _connect_cassandra() -> None:
    for attempt in range(1, settings.startup_attempts + 1):
        try:
            cassandra_connection.connect()
            create_keyspace()
            create_tables()
            return
        except NoHostAvailable:
            cassandra_connection.close()
            if attempt == settings.startup_attempts:
                raise
            logger.warning("Cassandra unavailable; retry %d", attempt)
            sleep(settings.startup_delay_seconds)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    _connect_cassandra()
    logger.info("Application ready")
    yield
    click_publisher.close()
    cassandra_connection.close()


app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[host.strip() for host in settings.trusted_hosts.split(",") if host.strip()],
)
if settings.cors_origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()
        ],
        allow_methods=["GET", "POST", "PATCH", "DELETE"],
        allow_headers=["Content-Type", "X-API-Key"],
    )


def error(code: str, message: str, http_status: int) -> JSONResponse:
    return JSONResponse(
        status_code=http_status, content={"error": {"code": code, "message": message}}
    )


@app.exception_handler(RequestValidationError)
def validation_error(_request: Request, exc: RequestValidationError):
    message = "; ".join(str(item["msg"]) for item in exc.errors())
    return error("validation_error", message, status.HTTP_422_UNPROCESSABLE_ENTITY)


@app.exception_handler(CustomAliasAlreadyExistsError)
def alias_conflict(_request: Request, exc: CustomAliasAlreadyExistsError):
    return error("alias_conflict", str(exc), status.HTTP_409_CONFLICT)


@app.exception_handler(UrlNotFoundError)
@app.exception_handler(RedirectUrlNotFoundError)
def not_found(_request: Request, exc: Exception):
    return error("url_not_found", str(exc), status.HTTP_404_NOT_FOUND)


@app.exception_handler(UrlExpiredError)
def expired(_request: Request, exc: UrlExpiredError):
    return error("url_expired", str(exc), status.HTTP_410_GONE)


@app.exception_handler(UrlDisabledError)
def disabled(_request: Request, exc: UrlDisabledError):
    return error("url_disabled", str(exc), status.HTTP_410_GONE)


@app.exception_handler(InvalidApiKeyError)
def unauthorized(_request: Request, exc: InvalidApiKeyError):
    return error("unauthorized", str(exc), status.HTTP_401_UNAUTHORIZED)


@app.exception_handler(RateLimitExceededError)
def rate_limited(_request: Request, exc: RateLimitExceededError):
    return error("rate_limited", str(exc), status.HTTP_429_TOO_MANY_REQUESTS)


@app.exception_handler(InvalidCursorError)
@app.exception_handler(AnalyticsRangeError)
def bad_request(_request: Request, exc: Exception):
    return error("invalid_request", str(exc), status.HTTP_400_BAD_REQUEST)


@app.exception_handler(CodeGenerationError)
def allocation_failure(_request: Request, exc: CodeGenerationError):
    return error("service_unavailable", str(exc), status.HTTP_503_SERVICE_UNAVAILABLE)


@app.get("/health/live", tags=["Health"])
def liveness():
    return {"status": "ok"}


@app.get("/health/ready", tags=["Health"])
def readiness():
    try:
        cassandra_connection.get_session().execute("SELECT now() FROM system.local")
    except (DriverException, RuntimeError):
        return error(
            "not_ready", "Cassandra is unavailable", status.HTTP_503_SERVICE_UNAVAILABLE
        )
    return {"status": "ready"}


app.include_router(api_router)
app.include_router(redirect_router)
