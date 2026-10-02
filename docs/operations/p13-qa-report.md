# P13 Comprehensive QA Report

Date: 2026-10-03

## System QA

**Status: PASS.**

The isolated system orchestrator creates a uniquely named disposable PostgreSQL/PostGIS project, applies migrations 001–015 and the existing regression suite, provisions least-privilege runtime roles, seeds only synthetic fixtures, starts the production Next.js build, and drives real Chromium browser requests through actual API routes and database-backed admin actions. Its `finally` cleanup removes the dedicated compose project and volume on success or failure.

The real browser golden path now covers scheduler → fixture worker → scoped ETL → fixture geocoder → real admin login/review → duplicate publish block/merge/reopen → publish → incremental source change while public values remain stable → return/visibility removal → reverify/republish → withdraw. A separate failure-isolation test proves one adapter retries/dead-letters while a second completes. Real hostile-input tests exercise public and admin filters/actions against disposable PostgreSQL and confirm tables remain intact. A real map browser test covers 500 synthetic visible facilities, cluster rendering, 20 rapid pans plus zoom/filter interactions, stale-request cancellation, bounded API pages, and latest viewport response consistency. All 3 system Playwright tests passed; the artifact scan passed.

The exact evidence and existing suite counts are in [p13-qa-matrix.md](p13-qa-matrix.md). No production database, government source, production geocoder, or real hospital data was accessed.

## Real-data QA

**Status: PENDING_INSUFFICIENT_PUBLISHED_SAMPLE.**

No production database credentials were configured, so this task could not inspect current production counts. No real data was imported. The historical P5 pilot is documented separately and does not represent currently published facilities. Do not calculate or claim a real-data accuracy percentage until the original P0 real-sample thresholds are met. See [p13-coverage-status.md](p13-coverage-status.md).

**P13 OVERALL STATUS: PARTIAL.** System engineering QA has passed; the real-data QA gate is still pending. **PRODUCTION LAUNCH: NO-GO.**

## Release blockers

| Gate | Status | Owner | Required action | P14 relevance |
|---|---|---|---|---|
| `REAL_PUBLISHED_DATA_SAMPLE` | PENDING | Data QA owner | Query current published source-backed rows; obtain at least 100 eligible real facilities for stratified review | Blocks production launch |
| `PRODUCTION_BASEMAP` | PENDING | Product / licensing owner | Select and verify an appropriately licensed production basemap and attribution terms | Blocks public launch; not staging |
| `PRODUCTION_COORDINATE_PROVIDER` | PENDING | Data / licensing owner | Approve a provider and retention/storage terms; complete per-region coordinate QA before publication | Blocks production coordinate display |
| `DEPLOYMENT_NEARBY_QUERY_LOG_REDACTION` | PENDING | Deployment owner | Prove hosting/gateway access logs omit query strings or redact `lat`/`lng`; application code must continue to avoid logging them | Deployment privacy gate; blocks release |
| `PRODUCTION_SOURCE_COVERAGE` | PENDING | Data sourcing owner | Verify region/source coverage and distinguish discovered, inspected, imported, candidate, and published counts | Blocks any nationwide completeness claim |
| `REAL_DATA_QUALITY_SAMPLE` | PENDING | Data QA owner | Meet P0 evidence precision, duplicate-review, and per-region coordinate sample thresholds without lowering counts | Blocks production launch |
| `SYSTEM_QA_GOLDEN_PATH` | PASS | Engineering owner | Keep the isolated real-system E2E and artifact secret scan green | P14 staging entry allowed; production remains blocked by the other gates |
| `PRODUCTION_SECURITY_HEADERS` | PENDING | Deployment owner | Verify production HSTS/CSP/edge headers and sensitive-route cache policy in deployed staging | P14 release hardening |

## No P14 execution

P13.1 did not perform staging deployment, production source approval, nationwide import, production geocoding, or production facility publication. **P14 staging entry is allowed** because SYSTEM QA is PASS. This does not permit a production launch. Production launch remains prohibited until the real-data, basemap, coordinate-provider, source-coverage, deployment-privacy, and production security-header gates pass. PR #24 remains open and unmerged; no P14 work has started.
