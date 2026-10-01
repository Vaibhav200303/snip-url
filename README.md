# SnipURL

SnipURL is a production-minded URL-shortening backend built with FastAPI,
Cassandra, Redis, and Kafka. It demonstrates collision-safe distributed IDs,
cache-aside reads, fail-open rate limiting, protected management APIs, and an
event-driven analytics pipeline.

## Architecture

```text
client -> FastAPI -> Cassandra (source of truth)
                  -> Redis (cache and rate limits)
                  -> Kafka -> analytics consumer -> Cassandra click events
```

Cassandra stores canonical URL records and a denormalized creation-time index.
Redis is non-authoritative: cache or rate-limiter failures do not take down URL
operations. Successful redirects publish privacy-minimal click events containing
only an event ID, short code, and timestamp. The consumer stores idempotent events
partitioned by URL and UTC day.

## Quick start

Requirements: Docker with Compose.

```bash
cp .env.example .env
# Change ADMIN_API_KEY in .env before exposing the service.
docker compose up --build
```

The API is available at `http://localhost:8000`, Swagger UI at `/docs`, and
readiness at `/health/ready`. Cassandra can take around a minute to become healthy
on its first start.

Create and follow a URL:

```bash
curl -X POST http://localhost:8000/api/v1/urls \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com","custom_alias":"example"}'

curl -i http://localhost:8000/example
```

Management calls require the configured API key:

```bash
curl http://localhost:8000/api/v1/urls/example \
  -H "X-API-Key: change-me"

curl -X PATCH http://localhost:8000/api/v1/urls/example \
  -H "X-API-Key: change-me" -H "Content-Type: application/json" \
  -d '{"is_enabled":false}'

curl "http://localhost:8000/api/v1/urls/example/analytics?from=2026-10-01&to=2026-10-31" \
  -H "X-API-Key: change-me"
```

Analytics is eventually consistent; a redirect may take a few seconds to appear.

## API

| Method | Path | Access | Purpose |
|---|---|---|---|
| POST | `/api/v1/urls` | Public | Create a short URL |
| GET | `/{short_code}` | Public | Redirect to the destination |
| GET | `/api/v1/urls` | API key | Cursor-paginated URL list |
| GET | `/api/v1/urls/{short_code}` | API key | Read URL metadata |
| PATCH | `/api/v1/urls/{short_code}` | API key | Update URL, expiration, or state |
| DELETE | `/api/v1/urls/{short_code}` | API key | Idempotently delete a URL |
| GET | `/api/v1/urls/{short_code}/analytics` | API key | Total and daily clicks |
| GET | `/health/live` | Public | Process liveness |
| GET | `/health/ready` | Public | Cassandra readiness |

Errors use `{"error":{"code":"...","message":"..."}}`. Redis failures are
logged and allowed to fail open. Cassandra is required for readiness. Kafka
publication is asynchronous; delivery problems are logged and never delay a
redirect.

## Configuration

See `.env.example` for all settings. Important production values are:

- `PUBLIC_BASE_URL`: externally reachable API origin.
- `ADMIN_API_KEY`: secret for management and analytics operations.
- `SNOWFLAKE_WORKER_ID`: must be unique per concurrently running API replica.
- `CREATE_RATE_LIMIT` and `REDIRECT_RATE_LIMIT`: per-IP requests per window.
- `ANALYTICS_RETENTION_DAYS`: Cassandra TTL for click events.

The default Cassandra schema uses `SimpleStrategy` and replication factor one for
local Compose only. A real multi-node deployment must use
`NetworkTopologyStrategy`, external secret management, and TLS termination.

## Local development

Python 3.14 and [uv](https://docs.astral.sh/uv/) are required.

```bash
uv sync
docker compose up -d cassandra redis kafka
uv run snip-url
# In another terminal:
uv run python -m app.analytics_consumer
```

Quality checks:

```bash
uv run ruff check .
uv run pytest -q
docker compose config
```

Schema bootstrap is intentionally idempotent and can add fields missing from the
original prototype. It is a development convenience, not a general migration
framework. The URL record and listing index are denormalized Cassandra writes and
are not transactional; repair tooling would be appropriate at larger scale.

## Intentional boundaries

This release has one administrator API key rather than user accounts. It does not
include a frontend, billing, custom domains, QR codes, detailed visitor tracking,
or cloud-specific infrastructure. Analytics counts are privacy-minimal and
eventually consistent.
