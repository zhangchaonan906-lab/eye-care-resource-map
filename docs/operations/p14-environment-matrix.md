# P14 Environment Matrix

| Setting | Local | CI | Staging | Production |
|---|---|---|---|---|
| Database projects | Disposable local PostGIS | Per-job disposable PostGIS | Dedicated isolated DB required | Separate production DB; not available in P14-A |
| `PUBLIC_API_DATABASE_URL` | Local least-privilege role | Ephemeral test role | Public API runtime role | Public API runtime role |
| `ADMIN_DATABASE_URL` | Local admin-review role | Ephemeral test role | Admin-review runtime role | Admin-review runtime role |
| `CORRECTION_DATABASE_URL` | Local correction submitter role | Ephemeral correction role | Dedicated correction submitter role | Dedicated correction submitter role |
| `UPSTASH_REDIS_REST_URL` / `UPSTASH_REDIS_REST_TOKEN` | Optional; in-memory development limiter | Mocked unit tests | Required shared distributed limiter | Required shared distributed limiter |
| `TRUST_PROXY_HEADERS` | `false` | Test controlled | `true` only behind a proxy that overwrites forwarded client address | `true` only behind a proxy that overwrites forwarded client address |
| `RATE_LIMIT_HASH_SECRET` | Local-only fallback | Ephemeral test value | Secret-manager value, random high-entropy | Secret-manager value, random high-entropy |
| `DATABASE_URL` | Collector runtime role | Ephemeral test role | Collector runtime role | Collector runtime role |
| `ETL_DATABASE_URL` | ETL runtime role | Ephemeral test role | ETL runtime role | ETL runtime role |
| `GEOCODE_DATABASE_URL` | Fixture only | Fixture only | Fixture only | Not configured; production provider gate pending |
| `SYNC_DATABASE_URL` | Local sync role | Ephemeral test role | Sync worker role | Disabled until release approval |
| `DATABASE_ADMIN_URL` | Operator-only migration/backup | Disposable test admin | One-shot operator secret | Separate break-glass process |
| `ADMIN_USERNAME` | Local test identity | Random test identity | Named authorized reviewers | Named authorized reviewers |
| `ADMIN_PASSWORD_HASH` | Scrypt test hash | Random ephemeral hash | Scrypt hash of operator password | Scrypt hash; rotate per policy |
| `ADMIN_SESSION_SECRET` | Random local secret | Random ephemeral secret | High-entropy secret manager value | High-entropy secret manager value |
| `ADMIN_ACTOR_ID` | Local UUID | Ephemeral UUID | Stable reviewer UUID | Stable reviewer UUID |
| `SITE_URL` | Optional HTTPS only | Unset | Exact staging HTTPS origin | Reserved for verified production origin |
| Basemap | Placeholder/development | Placeholder | Placeholder; no production provider | Pending provider rights and attribution review |

All credentials are supplied through an approved secret store or local ignored environment file. Never commit passwords, connection strings, session secrets, tokens, or real downloaded files. `DATABASE_ADMIN_URL` is for one-shot operations only; Web and workers use their least-privilege runtime URLs.

## Phase 4 environment check (2026-10-05 14:55 UTC)

This check found no configured staging site URL, staging database URL, shared Redis URL/token, hosting credential, SSH deployment credential, or monitoring DSN in the local process environment. The GitHub repository has no `staging` Actions environment (environment lookup returned 404), and no repository Actions secrets were listed. Docker CLI is installed, but its Linux Engine is unavailable (`docker info` cannot connect to the Docker Desktop pipe). No remote deployment, migration, backup, or live smoke was attempted. Values were checked for presence only; no secret values were read or printed.

These are missing infrastructure prerequisites, not successful staging evidence. Keep all staging gates pending until a separately provisioned HTTPS Web app, isolated PostgreSQL/PostGIS, shared rate-limit backend, worker host, and monitoring/backup services are accessible.
