# Post-Harvest Phase 3 — Infrastructure & Product Readiness

**Status snapshot:** 2026-10-05 UTC
**PR #33:** squash-merged to `main`; merge commit `4fa7fd4c8575a906f55301f620bea0346fc26398`.
**Phase branch:** `post-harvest-infra-readiness`.

## Data freeze

- `READY_NO_APPLICATION = 0`.
- The nine current official files/leads remain `QUARANTINED / INSPECTION ONLY`; the 18 historical leads remain `REACQUIRE_REQUIRED`.
- No source status changed. This branch performs no source import, ETL, production database write, facility publication, or real geocoder request. Fixture-only temporary databases used by tests are isolated and destroyed by the test harness.
- Production data/facilities remain at zero. Production launch remains **NO-GO**.

## Decisions and deployment candidates

| Area | Decision | Evidence and remaining gate |
|---|---|---|
| Coordinates | `PENDING`; no provider selected | Baidu documents China address geocoding and a `gcj02ll` output option, but storage/backups/redisplay rights and costs are not established. AMap’s current terms restrict commercial use and storage without a separate license. MapTiler permits geocoding results outside its service with database attribution, but China accuracy, plan-specific public redisplay and deletion handling remain unverified. No calls or writes were made. See [coordinate decision](p14-coordinate-provider-decision.md). |
| Basemap | `PENDING`; no production provider selected | MapTiler is the best evidenced MapLibre candidate: its published Flex plan is currently $30/month with metered overage, but mainland China availability, attribution/data-layer rights and actual latency/reliability need deployment evidence. Public OSM tile servers remain excluded. See [basemap decision](p14-basemap-decision.md). |
| Web hosting | Candidate: Vercel or equivalent Next.js host; not selected/deployed | Next.js officially supports Node.js/Docker deployment, and Vercel documents Next.js Route Handler/function support. App uses Next.js 16 Node Route Handlers and health/readiness/version contracts. No project credentials, host URL, or deployment evidence are available here. |
| Worker hosting | Candidate: Render Background Worker plus a separate scheduled job; not selected/deployed | Official Render docs describe long-running workers and scheduled jobs with environment variables. Confirm current plan cost, region/network, restart/health/log behavior, DB connectivity, and fixture-only schedule before selection. No source schedule is enabled. |
| Staging | `PENDING` | No isolated HTTPS site, database URL, or cloud secret-store access is configured. A local disposable PostGIS test is not staging. Future staging must have a separate database and secrets, apply migrations 001–016, use only synthetic P13 fixtures, and keep all real-source schedules disabled. |

## Code readiness completed in this phase

- Added a shared Redis REST fixed-window rate limiter for facility viewport, detail, search, nearby, correction submission, and admin login. Staging/production fail closed if the shared backend, trusted proxy identity, or HMAC secret is missing. Client identifiers are HMAC-SHA-256 digested before use as Redis keys; raw addresses are not logged. Deployments may set `TRUST_PROXY_HEADERS=true` only behind a proxy that overwrites the configured client-address headers.
- Added an institution correction form for six bounded issue types. Reports are size-limited, same-origin, rate-limited, and saved as pending review records through a dedicated submit-only DB role. Authenticated admins can read the review queue; there is no correction-to-facility mutation action.
- Added the exact coverage message “当前公开数据覆盖仍在逐步完善” and wording that explicitly avoids claiming a complete nationwide directory. Existing no-data and location-permission failure paths remain in place; no synthetic facilities are displayed by the production app.
- Added migration 016 and integration coverage for role separation, pending queue insertion, and unchanged facilities. Staging migrations and all migration checksums now extend through 016.

## Live evidence gates

The following remain `PENDING` because this workspace has no actual staging host, cloud credentials, separate staging database, provider account/key, or external alert destination:

- `STAGING_DATABASE`, `STAGING_DEPLOYMENT`, and `STAGING_SMOKE`.
- `WORKER_HOSTING`, `MONITORING`, and external alert delivery.
- `DEPLOYMENT_NEARBY_PRIVACY`: browser URL contract and application no-body-logging are code-tested, but host, gateway, analytics, and access-log body capture have not been inspected with sentinel coordinates.
- `PRODUCTION_SECURITY_HEADERS`: headers are configured/tested at code level; CSP remains Report-Only and no HTTPS staging response was observed.
- `PRODUCTION_RATE_LIMITING`: shared backend integration is implemented and locally testable, but no real backend credentials, multi-instance evidence, cost/latency observation, or staging load test is available.
- `DATA_CORRECTION_ENTRY`: form and queue are implemented; a human moderator, retention/response policy, deployed spam behavior, and operational privacy review are not yet assigned/verified.
- `BACKUP_RESTORE`: existing local disposable restore drill is engineering evidence only; no restore into an actual separate staging target was performed.
- `PRODUCTION_BASEMAP` and `PRODUCTION_COORDINATE_PROVIDER`.
- `REAL_PUBLISHED_DATA_SAMPLE`, `REAL_DATA_QUALITY_SAMPLE`, and `PRODUCTION_SOURCE_COVERAGE` remain `PENDING` because `READY_NO_APPLICATION=0`.

## Operator run order when infrastructure is provisioned

1. Provision the separate staging DB and web host; inject secrets via the host secret manager. Run ordered migrations 001–016 and verify roles.
2. Configure Upstash Redis REST URL/token and trusted proxy identity behavior; verify limits across multiple application instances and confirm limiter outage returns 503.
3. Deploy web and the fixture-only collector worker. Keep every real-source schedule disabled. Verify `/api/health/live`, `/api/health/ready`, `/api/version`, headers, nearby body privacy, and logs using `scripts/staging-smoke.mjs` plus an explicit sentinel review.
4. Exercise web/API/DB/worker/sync/5xx/latency/release-version/backup-age alerts. Run a staging backup and restore into a separate target.
5. Assign the correction report reviewer, response process, and retention period before turning on a public endpoint.
6. Revisit map/geocoder providers only after terms, costs, mainland availability, attribution, coordinate/storage rights, quotas and deletion obligations are evidenced. Do not import quarantined data or enable production publication.

Official service references: [AMap platform terms](https://lbs.amap.com/pages/terms/), [Baidu Geocoding V3](https://lbs.baidu.com/docs/webapi?title=geocoding%2Fguide%2Fwebservice-geocoding-base), [MapTiler Cloud terms](https://www.maptiler.com/terms/cloud/), [MapTiler pricing](https://www.maptiler.com/cloud/pricing/), [Next.js Route Handlers](https://nextjs.org/docs/app/getting-started/route-handlers), [Next.js deployment options](https://nextjs.org/docs/app/getting-started/deploying), [Vercel's Next.js hosting guide](https://vercel.com/docs/frameworks/full-stack/nextjs), [Render background workers](https://render.com/docs/background-workers), [Render cron jobs](https://render.com/docs/cronjobs), and [Upstash REST API](https://upstash.com/docs/redis/features/restapi).
