# P14-A Staging and Release Engineering

## Current status

P13 PR #24 is merged to `main` at `111452519e033df94726809308a9a2349feb48cd`. P14-A builds staging and release controls; it does not authorize production launch. No Vercel, staging host, `STAGING_SITE_URL`, or isolated staging database credentials were present in the environment. Therefore cloud deployment and remote smoke are **blocked by missing credentials**, and no deployment is claimed.

## Operator sequence

1. Provision a dedicated staging Web app and isolated PostgreSQL/PostGIS database. Do not point staging at production.
2. Store secrets in the approved secret manager. Configure the roles and variables in [the environment matrix](p14-environment-matrix.md); Web uses runtime roles only. Do not give Web `DATABASE_ADMIN_URL`. Set `APP_ENV=staging` and the exact HTTPS `SITE_URL` before building so compiled security headers and metadata identify staging correctly.
3. Review `docs/operations/p14-release-gates.json`, run the production and staging guards, and confirm the production guard still blocks launch.
4. Provision PostGIS in the database's `public` schema, then run `DATABASE_ADMIN_URL=... scripts/apply-migrations.sh` as a one-shot operator action. The runner verifies the 001–016 inventory/checksums and records each applied version. It bootstraps the reviewed P5 source catalog baseline after migration 008, then refuses untracked existing application schemas or drift.
5. Deploy the Web image and separate collector container/scheduled runner. Start with fixture-only configuration; keep every real-source schedule disabled.
6. Set the exact HTTPS `SITE_URL`, deploy, then run `STAGING_SITE_URL=... node scripts/staging-smoke.mjs`. Validate `/api/version`, readiness, security headers, noindex, admin cache behavior, and nearby POST validation.
7. Run and record a disposable backup/restore drill. No backup from this project may be copied to Git or CI artifacts.

The migration runner is a one-shot release command, never part of a Next.js request. Do not edit an already-applied migration; add a new migration and update its checksum inventory through review. SHA-256 checksums use canonical LF text so Git's Windows CRLF checkout does not create platform-specific drift. The current runner fails closed when an existing schema has no history registry.

## Release constraints

- `GET /api/nearby` returns 405. Nearby coordinates are sent in a JSON POST body and are not written by the application to logs. Provider access-log body retention still requires host-specific verification.
- CSP is `Content-Security-Policy-Report-Only`; production CSP is not approved. HSTS is emitted only for staging/production with an HTTPS `SITE_URL`; no deployed staging host was available to verify it.
- Staging gets `X-Robots-Tag: noindex` and a disallow-all robots file. Production does not inherit staging noindex.
- Collector image uses a non-root account, runtime dependencies only, and no baked credentials. Scheduler and worker are configured artifacts, not deployed services.
- Public distributed rate limiting, production basemap, production coordinate provider, real source coverage, and real-data QA remain pending. Production launch is NO-GO.
- Public API and admin-login routes require the shared Redis REST limiter when `APP_ENV=staging` or `production`; configure `UPSTASH_REDIS_REST_URL`, `UPSTASH_REDIS_REST_TOKEN`, `RATE_LIMIT_HASH_SECRET`, and `TRUST_PROXY_HEADERS=true` only behind a proxy that overwrites client-address headers. Missing limiter or identity configuration fails closed. Live multi-instance and provider log evidence is still required before the gate can pass.
- Configure `CORRECTION_DATABASE_URL` with the dedicated `eye_correction_runtime` role. Migration 016 stores bounded correction reports in a pending queue, grants only a definer submission function, and exposes a read-only admin review view. Reports never mutate facilities. A staffed moderation process and deployed abuse/privacy validation are still required.
- Nearby privacy at the application layer is covered by POST contract and E2E tests. The production nearby privacy gate and deployment access-log/body privacy remain pending provider evidence.

Use [monitoring](p14-monitoring.md), [backup/recovery](p14-backup-recovery.md), and [rollback](p14-rollback.md) procedures. Cloud monitoring, alert delivery, worker hosting, and remote staging smoke remain unverified until credentials and provider settings exist.
