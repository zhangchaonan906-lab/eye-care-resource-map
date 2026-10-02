# P14 Environment Matrix

| Setting | Local | CI | Staging | Production |
|---|---|---|---|---|
| Database projects | Disposable local PostGIS | Per-job disposable PostGIS | Dedicated isolated DB required | Separate production DB; not available in P14-A |
| `PUBLIC_API_DATABASE_URL` | Local least-privilege role | Ephemeral test role | Public API runtime role | Public API runtime role |
| `ADMIN_DATABASE_URL` | Local admin-review role | Ephemeral test role | Admin-review runtime role | Admin-review runtime role |
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

All credentials are supplied through an approved secret store or local ignored environment file. Never commit passwords, connection strings, session secrets, tokens, or real downloaded files. `DATABASE_ADMIN_URL` is for one-shot operations only; Web and workers use their least-privilege runtime URLs. No environment credentials were present during P14-A, so staging deployment was not attempted.
