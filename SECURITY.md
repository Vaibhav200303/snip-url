# Security policy

## Supported version

Security fixes are applied to the latest commit on the active deployment branch.
This is a portfolio deployment rather than a multi-tenant hosted product.

## Public and private surfaces

The public Nginx listener exposes only:

- the homepage and static assets;
- `POST /api/v1/urls`;
- `POST /api/v1/public/analytics`;
- valid single-segment short-code redirects;
- liveness, readiness, and API documentation.

Public analytics return aggregate click totals and daily buckets only for active,
unexpired links. They never return destinations, short codes, request metadata,
IP addresses, user agents, or referrers. Missing, malformed, disabled, and
expired inputs share the same neutral response. Requests are rate-limited per IP.

The admin dashboard, URL metadata, management operations, and per-code
administrator analytics are available only from the loopback-bound Nginx
listener on VM port `8080`. The FastAPI port is also bound to loopback.
Cassandra, Redis, and Kafka have no host port mappings.

## Administrator credential transport

Never send `ADMIN_API_KEY` to the public HTTP listener. Until a trusted domain
and publicly valid TLS certificate are configured, reach the admin listener only
through an encrypted SSH tunnel:

```bash
gcloud compute ssh snipurl-vm --zone=asia-south1-a -- \
  -L 18080:localhost:8080
```

Open `http://localhost:18080/admin` after the tunnel is established. The browser
sends the key through the local tunnel, so it is encrypted between the workstation
and VM. The dashboard stores the key in `sessionStorage`, not persistent storage.

For a domain-based deployment, terminate HTTPS with a publicly trusted
certificate before exposing any protected endpoint. Redirect HTTP to HTTPS and
keep Cassandra, Redis, Kafka, and the direct FastAPI listener private.

## Secret handling

- Store production secrets only in the VM's root-owned `/opt/snip-url/.env`.
- Keep the file mode at `0600` and never commit it.
- Use at least 32 random characters for `ADMIN_API_KEY` and
  `SHORT_CODE_SECRET`.
- Do not put the admin key in frontend environment variables, image layers,
  logs, URLs, screenshots, or support messages.
- Rotate the key immediately if it may have been disclosed.

Production startup rejects default or weak administrator credentials, a weak
short-code secret, and wildcard trusted-host configuration.

## Data and privacy

Cassandra is the authoritative store for URL records and click aggregates.
Redis contains rebuildable cache entries and rate-limit counters. Kafka contains
queued click events and broker metadata. Click events contain only an event UUID,
short code, and UTC timestamp.

Back up the Cassandra volume before infrastructure changes. Do not run
`docker compose down -v` when data must be retained.

## Reporting a vulnerability

Do not open a public issue containing credentials, exploit details, or private
deployment information. Contact the repository owner privately with the affected
version, reproduction steps, impact, and any suggested mitigation.
