# P14-B Production Release Readiness

**Status: PARTIAL — production launch NO-GO**

**Evidence snapshot:** 2026-10-05 UTC

**P14-A merge:** PR #25 squash-merged to `main` at `db50b4aa72d5577dc134e8127460e757c3b54de2`.

This document records the current release evidence and the actions still requiring real infrastructure, provider terms, and authorized data. A local test, source discovery lead, or historical pilot is not treated as cloud or production proof. The authoritative gate manifest is [`p14-release-gates.json`](p14-release-gates.json); every gate records its owner, evidence, required action, and last verification time.

## Current environment boundary

On 2026-10-02 the environment had no staging URL, staging database credentials, hosting credentials, or production map/geocoder provider configuration. The local `eye-p11-db-1` container was healthy, but it is a local application database, not staging or production. A read-only query found 0 rows in `public.published_facility_api`, 0 current source snapshots, and 0 current candidates. These counts do not include a separate historical P5 pilot database.

The final P5 report records an isolated local pilot of 50 Beijing source rows and 27 Bao'an source rows, producing 72 candidates and 8 duplicate-review cases. It records 0 published facilities, 0 verified coordinates, and no geocoder calls. These historical pilot outputs are not current P11 application rows, are not a public sample, and do not satisfy P14 real-data publication or quality gates. See [`p5-real-pilot-final-report.md`](p5-real-pilot-final-report.md).

## 1. Deployment

| Gate | Status | Evidence and required action |
|---|---|---|
| `STAGING_DATABASE` | PENDING | No isolated remote PostgreSQL/PostGIS credentials. Provision a separate database, apply migrations 001–016, and verify role isolation/least privilege. |
| `STAGING_DEPLOYMENT` | PENDING | No staging URL or hosting credentials. Select host, inject secrets through its secret manager, and deploy Web and a fixture-only worker artifact. |
| `STAGING_HEALTH` | PENDING | Health route contracts pass automated tests; no remote host response has been observed. |
| `STAGING_SMOKE` | PENDING | Run `scripts/staging-smoke.mjs` against HTTPS staging and record live/ready/version, map, admin login, nearby POST, noindex, security/cache headers, and commit SHA. |
| `WORKER_HOSTING` | PENDING | Container exists, runtime does not. Select a scheduler/worker host and verify one-shot/loop operation, restart policy, secrets, network, logs, and resource limits. Keep all real-source schedules disabled. |
| `BACKUP_RESTORE` | PENDING | P14-A's local synthetic drill passed; actual staging backup and restore to a separate target has not been performed. Verify schema, PostGIS, audit, source records, and public data. |

`APP_HEALTH_CONTRACT`, build, system QA, and CI security scans are PASS as code/CI evidence only. The security scan result means runtime high/critical findings are zero and production runtime exposure to `braces` was not detected; the full development tree has the temporary, expiring `GHSA-vfj7-8cjw-p6xm` exception recorded in [`npm-audit-exceptions.json`](../security/npm-audit-exceptions.json). It does not mean all dependencies are clean or prove staging deployment. The exception must be reviewed before its recorded expiry of `2026-11-03T16:42:45Z` and removed when a compatible upstream patch is available. The P14-A disposable backup drill is separately recorded as `LOCAL_BACKUP_RESTORE_DRILL=PASS`.

## 2. Basemap

`PRODUCTION_BASEMAP=PENDING`. No provider has been selected. Do not use the OpenStreetMap Foundation's public tile server as a production basemap. The development placeholder remains separate from any production provider.

Before approval, record mainland China availability, coordinate system, browser/MapLibre compatibility, commercial/public display rights, tile/style/font/icon rights, exact attribution text, quotas/pricing, allowed domains, retention/caching, and review/audit requirements. See [`p14-basemap-decision.md`](p14-basemap-decision.md).

## 3. Coordinates

`PRODUCTION_COORDINATE_PROVIDER=PENDING`. No real geocoder was called and no production coordinates were stored. A map choice does not imply permission to geocode or persist returned coordinates.

No provider is approved until documented terms cover geocoding, result persistence, database storage, redisplay/public map display, public/commercial application use, coordinate system, accuracy, quota, pricing, and deletion/withdrawal. See [`p14-coordinate-provider-decision.md`](p14-coordinate-provider-decision.md).

## 4. Real data

### Current publication and quality evidence

- Current local P11 published facility count: **0**.
- Current local P11 source snapshot count: **0**; candidate count: **0**.
- Historical P5 separate pilot database: 74 source snapshots, 72 candidates, 8 duplicate-review cases, 0 facilities, 0 facility locations. Its QA was source/candidate review, not a production published-coordinate sample.
- Required production sample: at least 100 real facilities with explicit ophthalmology evidence, verified coordinates, source rights, and human publication review. No thresholds may be lowered to reach the count.
- Evidence QA, duplicate QA, and coordinate QA remain PENDING until the specified real samples exist. Insufficient sample size cannot pass by extrapolation.

### Source readiness snapshot

The status below separates catalog approval from automated access, file acquisition, and permission to move data between environments.

| Source | Source/catalog classification | P14-B release treatment |
|---|---|---|
| Beijing, designated medical institutions | `APPROVED` in source catalog; `manual_only`; field/right metadata recorded. P5's broad use/reuse interpretation and current app transfer need a fresh rights review before production. | Not enabled. Historical 50-row P5 pilot is not in the current P11 DB. |
| Beijing, general “医院” dataset | Catalog says `APPROVED`, name-only permitted fields; last source update in the catalog is 2024-11-20. Treat freshness as `STALE` pending a current source review; not a useful ophthalmology-evidence source by itself. | Excluded from publication candidates until refreshed and scope reviewed. |
| Shenzhen Bao'an, “医院基本信息” | `APPROVED` for the reviewed bounded pilot and `manual_only`; app display is listed, while raw transfer/redistribution is not allowed and deletion on withdrawal applies. | `district_only`. Historical 27-row pilot exists in a separate DB; do not transfer it into the app DB absent rights approval. |
| Tianjin municipal “医疗机构执业登记信息” | `UNKNOWN`, `manual_only`; 36-row file was inspected, but coverage is `municipality_source_scope_unknown` and continued storage/display rights are unresolved. | Not an approved publication candidate. |
| Tianjin Xiqing registration lead | `UNKNOWN`; 2023 plan entry only. `district_only`; no current detail page, file, or verified schema. | No inherited row/hash/schema/evidence from the separate municipal file. |
| Dazhou “医疗机构执业许可证” | `UNKNOWN`; directory metadata lists 81 rows, but the real file was not acquired/inspected. | Not approved for import. The separate 4,018-record registration dataset has acquisition blocked by an official redirect error; this is not a source rejection. |

Only a source whose current approval and rights explicitly cover permitted fields, retention, the intended environment transfer, and app display may enter a publication batch. `manual_only` does not authorize an automated worker. Do not enable sources in bulk.

### P14-B real data batch 1 sequence

Any future batch must remain auditable end to end: official source → immutable file provenance and SHA-256 → import run → P3 ETL → location review → P11 human review → publication gate. No direct SQL inserts into published facilities. First target at least 100 qualifying real facilities, with no relaxed evidence or coordinate requirements.

### Correction and feedback entry

`DATA_CORRECTION_ENTRY=PENDING`. This phase adds a bounded public report form, dedicated submit-only database role, migration-backed pending queue, and authenticated read-only admin queue. Reports cannot mutate canonical facility rows. Before enabling a live form, assign a human triage owner, publish retention/response details, and verify deployed abuse controls and privacy handling.

## 5. Security / Privacy

| Gate | Status | Evidence and required action |
|---|---|---|
| `DEPLOYMENT_NEARBY_PRIVACY` | PENDING | Application sends nearby coordinates in POST JSON and does not log bodies. Verify browser URL/history, application logs, host access logs, and gateway logs with sentinel coordinates; prove request-body capture/retention is off. |
| `PRODUCTION_SECURITY_HEADERS` | PENDING | Verify headers on actual HTTPS staging. CSP remains Report-Only; collect reports and assess legitimate violations before considering enforcement. |
| `PRODUCTION_RATE_LIMITING` | PENDING | Shared Redis REST integration now protects facilities, search, detail, nearby, correction submissions, and admin login with separate fixed-window limits; missing backend/proxy identity fails closed in staging/production. Provider credentials and live multi-instance behavior are not configured or tested. |
| `NEARBY_POST_CONTRACT` | PASS | Automated code/CI evidence only; must also pass deployed staging smoke. |

No privacy gate is passed based solely on source code when hosting/gateway behavior is unknown.

## 6. Monitoring

`MONITORING=PENDING`. Documentation is not monitoring proof. Configure actual external alert delivery and exercise signals for web health and HTTP 5xx, database readiness, worker dead-letter/sync failures, and backup age. `WORKER_HOSTING` also remains pending until a real worker runtime is deployed and verified.

## Release decision

- Production guard: expected to remain blocked (non-zero exit).
- Production launch allowed: **NO**.
- Do not create `p14-final-release-review.md` until final release review; actual staging and all mandatory production evidence are still outstanding.
- Next step: resolve external staging credentials/host and provider/source rights decisions, then close gates only with deployment or signed-term evidence.
