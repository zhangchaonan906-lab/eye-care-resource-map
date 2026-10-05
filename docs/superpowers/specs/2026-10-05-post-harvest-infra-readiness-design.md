# Post-Harvest Infrastructure & Product Readiness Design

## Goal

Advance infrastructure and product readiness without importing quarantined data or representing unavailable cloud resources as deployed. Keep production launch at `NO-GO` while `READY_NO_APPLICATION=0` and any required deployment evidence is absent.

## Constraints

- The nine current local source files stay `QUARANTINED / INSPECTION ONLY`; 18 historical leads stay `REACQUIRE_REQUIRED`.
- No provider applications, government contacts, real-data imports, ETL, source approval, or publication.
- Never use synthetic QA records in production.
- No real geocoder calls or persisted provider coordinates until one provider's terms explicitly allow storage and public redisplay.
- Never use the OSM Foundation public tile server as production basemap.
- Staging must be a separately provisioned HTTPS web deployment, PostgreSQL/PostGIS database, and fixture-only worker. Local Docker tests are not staging evidence.
- External deployment, provider, secret, and backup evidence stays `PENDING` until observed against the actual configured service.

## Approach

1. Retain `PENDING` for coordinate provider and production basemap unless official terms, China operation, pricing, attribution, MapLibre compatibility, coordinate/storage rights, and deployment behavior all pass. Compare AMap, Baidu, MapTiler, and a no-provider option using current official sources; choose no provider by default when critical evidence is missing.
2. Add a provider-backed distributed rate-limit interface for public API and admin authentication. Local/test runs may use a deterministic in-process implementation; staging/production must fail closed when the configured shared backend is unavailable or missing.
3. Add a correction submission path that validates bounded, minimal input and creates only a pending review record. Admin review can inspect and disposition a report; no report action directly mutates a facility.
4. Improve empty-data messaging so the map, search, nearby, and facility detail views explain incomplete public coverage and provide an appropriate retry or correction path without showing synthetic rows.
5. Refresh release-gate evidence and runbooks. Only mark code-level checks `PASS`; actual cloud staging, provider, monitoring, backups, nearby-log privacy, and external alert delivery remain pending until live evidence exists.

## Data flow and interfaces

- Browser correction form → bounded POST route → server-side rate limit → least-privilege database function → `pending` correction queue → authenticated admin review.
- A correction records an optional facility id, one allowed issue category, and a bounded description. It does not accept exact user location, credentials, or required contact details. The UI warns users not to include personal or medical information.
- API rate limits use separate named policies for viewport/facility reads, search, nearby, and admin login. Client identity is derived only from a documented hosting proxy header; raw IPs are not logged or stored as a limiter key.
- Basemap credentials remain server/deployment-managed configuration with public token scope restrictions; no provider key is committed.

## Failure behavior

- If the shared rate-limit backend is missing/unavailable in staging or production, protected routes return a generic retryable service error; they do not silently fall back to process-local counters.
- Invalid, oversized, or too-frequent correction submissions are rejected with generic responses. Accepted reports remain pending and visible only to authenticated reviewers.
- Map/data API failures retain the existing list/search affordances and show honest empty/limited-data language.
- A missing cloud credential or provider term prevents the corresponding release gate from passing; it does not trigger a production fallback.

## Verification

- Unit tests for rate-limit policies, fail-closed configuration, correction validation, review disposition, and empty/limited-data states.
- Database migration/integration coverage proving submission only inserts into the review queue and cannot alter facility rows.
- Existing collector and web suites, Ruff, mypy, lint, typecheck, build, P13 E2E/accessibility/system E2E, P14 release checks, database regression, backup/restore drill, secret scan, and `git diff --check`.
- Live staging checks are reported `PENDING` until a separate HTTPS deployment and isolated staging database/worker are provisioned and observed.

## Decision status

Coordinate provider: `PENDING` (`NO_PROVIDER / DEFER` is safer than an unsupported selection).

Production basemap: `PENDING` until MapLibre-compatible service, lawful China coverage, rights, attribution, quota, pricing, and live reliability are verified.

Production launch: `NO-GO` until at least one `READY_NO_APPLICATION` source and all data, infrastructure, privacy, and release gates pass.
