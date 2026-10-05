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

## Phase 4 live status (2026-10-05)

No staging host, monitoring destination, alert integration, worker host, or staging credentials were available to this run. No external health monitor, 5xx alert, worker heartbeat, database connectivity monitor, latency dashboard, or fault-injection alert was exercised. `MONITORING` and `WORKER_HOSTING` remain **PENDING**. A future verification must record the monitor/provider, sanitized test event, observed alert, and timestamp without including secret values or exact nearby coordinates. See [the live verification record](staging-live-verification.md).

## Post-harvest Phase 3 additions

- The correction queue has a bounded submit function and DB regression coverage for pending state and no facility mutation. Assign a reviewer and a response/retention policy before enabling a live form; monitor submission volume and review backlog without logging report bodies.
- Rate limiting is an application dependency in staging/production. Alert on sanitized `SERVICE_UNAVAILABLE` rates and shared Redis availability. Do not log limiter keys, raw client addresses, nearby POST bodies, or correction descriptions.
- The UI says “当前公开数据覆盖仍在逐步完善”; do not imply nationwide completeness while approved/publication-ready sources remain unavailable.
