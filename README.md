# SnipURL

SnipURL is a portfolio-grade full-stack URL shortener built with React,
FastAPI, Cassandra, Redis, and Kafka. It combines a polished responsive UI with
collision-safe distributed IDs, cache-aside reads, fail-open rate limiting,
protected management APIs, and event-driven analytics.

## Architecture

```text
User
  |
Frontend / Nginx reverse proxy
  |
FastAPI
  |-- Redis (cache and rate limits)
  |-- Cassandra (URL source of truth)
  `-- Kafka
        |
        `-- Analytics consumer --> Cassandra (click events)
```

The frontend is React, TypeScript, and Vite. Nginx serves its production build
and routes `/api/*`, `/health/*`, and valid single-segment short codes to
FastAPI. Only `/` and `/admin` are frontend routes, preventing arbitrary SPA
paths from being mistaken for short codes.

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

The complete application is available at `http://localhost`, the admin dashboard
at `/admin`, Swagger UI at `/docs`, and readiness at `/health/ready`. The backend
also binds to local-only `127.0.0.1:8000` for development. Cassandra can take
around a minute to become healthy on its first start.

Create and follow a URL:

```bash
curl -X POST http://localhost/api/v1/urls \
  -H "Content-Type: application/json" \
  -d '{"long_url":"https://example.com","custom_alias":"example"}'

curl -i http://localhost/example
```

Management calls require the configured API key:

```bash
curl http://localhost/api/v1/urls/example \
  -H "X-API-Key: change-me"

curl -X PATCH http://localhost/api/v1/urls/example \
  -H "X-API-Key: change-me" -H "Content-Type: application/json" \
  -d '{"is_enabled":false}'

curl "http://localhost/api/v1/urls/example/analytics?from=2026-10-01&to=2026-10-31" \
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
- `TRUSTED_HOSTS`: comma-separated hosts accepted by FastAPI.
- `CORS_ORIGINS`: comma-separated development origins; use an empty value for
  same-origin production.

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
# In a third terminal:
cd frontend
npm install
npm run dev
```

Quality checks:

```bash
uv run ruff check .
uv run pytest -q
docker compose config
cd frontend && npm run lint && npm run build
```

Schema bootstrap is intentionally idempotent and can add fields missing from the
original prototype. It is a development convenience, not a general migration
framework. The URL record and listing index are denormalized Cassandra writes and
are not transactional; repair tooling would be appropriate at larger scale.

## Intentional boundaries

This release has one administrator API key rather than user accounts. It does not
include billing, custom domains, QR codes, or detailed visitor tracking.
Analytics counts are privacy-minimal and eventually consistent.

## Frontend and admin dashboard

The home page creates generated or custom short links, supports expiration, and
keeps the eight most recent creations in browser `localStorage`. That recent list
is explicitly local history, not an account feature.

`/admin` prompts for `ADMIN_API_KEY`, stores it only in browser `sessionStorage`,
and provides URL listing, enable/disable, deletion, and date-range analytics. The
key is never compiled into the frontend bundle or written to persistent browser
storage. Use **Clear key & log out** on shared computers.

For standalone Vite development, set `VITE_API_BASE_URL` only when the backend is
not reached through Vite's localhost proxy. Production should leave it unset so
the browser uses the same public origin.

## Docker networking and persistence

The Compose stack runs six containers: `web`, `api`, `analytics-consumer`,
`cassandra`, `redis`, and `kafka`. Only Nginx port 80 is publicly bound. The API
has a loopback-only development binding; Cassandra, Redis, and Kafka have no host
port mappings.

Named volumes survive ordinary restarts and `docker compose down`:

- `snip-url_cassandra_data`: canonical URLs, listing index, and analytics.
- `snip-url_redis_data`: rebuildable cache and rate-limit counters.
- `snip-url_kafka_data`: queued click events and broker metadata.

Never run `docker compose down -v` when data must be retained. Cassandra is the
only authoritative store and should be snapshotted and copied off-host.

## Google Cloud deployment

The initial portfolio deployment uses one Ubuntu 24.04 Compute Engine
`e2-standard-2` VM in `asia-south1`, a 50 GB balanced persistent disk, Docker
Compose, and a reserved static external IP. The repository includes
`deploy/bootstrap-vm.sh` to install Docker Engine and the Compose plugin.

Deployment outline:

```bash
gcloud compute instances create snipurl-vm \
  --zone=asia-south1-a --machine-type=e2-standard-2 \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud --boot-disk-size=50GB \
  --boot-disk-type=pd-balanced --tags=snipurl-web \
  --metadata-from-file=startup-script=deploy/bootstrap-vm.sh

gcloud compute scp --recurse . snipurl-vm:/tmp/snip-url \
  --zone=asia-south1-a
gcloud compute ssh snipurl-vm --zone=asia-south1-a
sudo cp -a /tmp/snip-url/. /opt/snip-url/
cd /opt/snip-url
sudo docker compose up -d --build
```

Create a production `.env` on the VM with a strong `ADMIN_API_KEY`, the public
IP in `PUBLIC_BASE_URL` and `TRUSTED_HOSTS`, and an empty `CORS_ORIGINS`. Permit
TCP 80 to instances tagged `snipurl-web`; do not create public firewall rules
for Cassandra, Redis, or Kafka. If a domain is later attached, point its A record
to the reserved IP and add Caddy or another TLS-terminating proxy for Let's
Encrypt HTTPS. Never use self-signed TLS as a public-production substitute.

## Security and scaling notes

- Input is validated on both frontend and backend; aliases allow only
  `[A-Za-z0-9_-]{3,32}` and reserved application paths are rejected.
- Management endpoints use constant-time API-key comparison. The key belongs in
  the VM-only `.env`, not Git, image layers, or frontend variables.
- Nginx adds basic browser security headers, FastAPI validates trusted hosts, and
  production runs same-origin without permissive CORS.
- Redis failures degrade to Cassandra and fail open for availability. Cassandra
  remains required for readiness; Kafka analytics are eventually consistent.
- Swagger/OpenAPI is intentionally public for this portfolio. Disable it in a
  private production product if API discovery is undesirable.
- Horizontally scaled API instances require a unique `SNOWFLAKE_WORKER_ID` each.
  This single-VM deployment intentionally uses one API instance.
- The local single-node Cassandra configuration uses `SimpleStrategy` and
  replication factor one. A high-availability deployment requires a real cluster,
  `NetworkTopologyStrategy`, monitoring, tested backups, and multiple hosts.
