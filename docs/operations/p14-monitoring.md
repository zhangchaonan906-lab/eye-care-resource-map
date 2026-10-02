# P14 Monitoring Contract

## Signals

| Signal | Source | Initial response |
|---|---|---|
| HTTP 5xx rate | Hosting request metrics | Check deploy/version and application errors |
| Web liveness/readiness | `/api/health/live`, `/api/health/ready` | Restart only after distinguishing process from DB failure |
| Database connectivity | readiness `SELECT 1` | Check DB reachability and runtime credentials; response contains no internals |
| Worker task failures | `source_sync_tasks` terminal failures and structured worker logs | Pause that source and inspect sanitized error summary |
| Dead letters | durable sync task status | Review before retry; do not silently discard |
| Consecutive sync failures / open alerts | sync alerts | Disable the affected schedule pending review |
| Last successful sync | task completion timestamp | Compare with the approved source cadence |
| Backup age / restore drill | private backup inventory and drill record | Raise recovery incident if policy threshold is exceeded |

## Privacy and delivery

The application must not log credentials, session/CSRF values, raw source payloads, or exact browser coordinates. Nearby coordinates are sent in a POST body and application handlers do not log request bodies. Whether a future hosting provider captures request bodies in edge/access logs is **unverified**; provider log settings and a sentinel review are required before production.

Monitoring contract: **implemented in this runbook and health routes**. External alert delivery and a selected metrics provider: **pending**. Do not represent this documentation as an active alerting service.
