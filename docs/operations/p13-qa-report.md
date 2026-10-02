# P13 Comprehensive QA Report

Date: 2026-10-03

## System QA

**Status: BLOCKED.**

The local system checks completed in this branch include 225 Collector unit tests, full disposable P1–P12 database regressions, the P13 5,000-row synthetic performance harness, 12 Web database integration tests, 7 Chromium browser tests, 3 axe-tagged browser scans, and a 150-record deterministic parser/evidence truth set. The final disposable DB run also passed 14 collector DB tests, 3 ETL DB tests, and 1 fixture-geocoder DB test. The full test list and limitations are in [p13-qa-matrix.md](p13-qa-matrix.md).

The requested complete browser→API→database→worker→review→publication journey is not implemented in this pass. The P13 Playwright tests stub public/admin HTTP responses; actual repositories and PostgreSQL/PostGIS are covered separately by DB integration tests. The separate browser flows for incremental change, duplicate conflict/reopen, and two-source failure isolation are also outstanding. A dedicated SQL injection hostile-string matrix and a 500-visible-facility browser pan/zoom stress run remain outstanding. These gaps block SYSTEM QA from PASS.

## Real-data QA

**Status: PENDING_INSUFFICIENT_PUBLISHED_SAMPLE.**

No production database credentials were configured, so this task could not inspect current production counts. No real data was imported. The historical P5 pilot is documented separately and does not represent currently published facilities. Do not calculate or claim a real-data accuracy percentage until the original P0 real-sample thresholds are met. See [p13-coverage-status.md](p13-coverage-status.md).

## Release blockers

| Gate | Status | Owner | Required action | P14 relevance |
|---|---|---|---|---|
| `REAL_PUBLISHED_DATA_SAMPLE` | PENDING | Data QA owner | Query current published source-backed rows; obtain at least 100 eligible real facilities for stratified review | Blocks production launch |
| `PRODUCTION_BASEMAP` | PENDING | Product / licensing owner | Select and verify an appropriately licensed production basemap and attribution terms | Blocks public launch; not staging |
| `PRODUCTION_COORDINATE_PROVIDER` | PENDING | Data / licensing owner | Approve a provider and retention/storage terms; complete per-region coordinate QA before publication | Blocks production coordinate display |
| `DEPLOYMENT_NEARBY_QUERY_LOG_REDACTION` | PENDING | Deployment owner | Prove hosting/gateway access logs omit query strings or redact `lat`/`lng`; application code must continue to avoid logging them | Deployment privacy gate; blocks release |
| `PRODUCTION_SOURCE_COVERAGE` | PENDING | Data sourcing owner | Verify region/source coverage and distinguish discovered, inspected, imported, candidate, and published counts | Blocks any nationwide completeness claim |
| `REAL_DATA_QUALITY_SAMPLE` | PENDING | Data QA owner | Meet P0 evidence precision, duplicate-review, and per-region coordinate sample thresholds without lowering counts | Blocks production launch |
| `SYSTEM_QA_GOLDEN_PATH` | BLOCKED | Engineering owner | Connect disposable DB runtimes, worker, reviewer mutations, and public UI in the requested four deterministic E2E journeys | Must pass before P14 staging entry criteria |
| `PRODUCTION_SECURITY_HEADERS` | PENDING | Deployment owner | Verify production HSTS/CSP/edge headers and sensitive-route cache policy in deployed staging | P14 release hardening |

## No P14 execution

P13 did not perform staging deployment, production source approval, nationwide import, geocoding, facility publication, or P14 implementation. P14 entry requires SYSTEM QA PASS. Production launch remains prohibited until the real-data, basemap, coordinate-provider, source-coverage, and deployment-privacy gates pass.
