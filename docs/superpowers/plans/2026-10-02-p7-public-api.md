# P7 Public API Implementation Plan

> **For agentic workers:** Implement task by task with test-first checkpoints. The user has authorized inline execution for this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add read-only public facility, detail, search, and category endpoints backed only by verified published data.

**Architecture:** Next.js App Router Route Handlers validate bounded query parameters and delegate to a parameterized PostgreSQL repository. A dedicated database role can only read a purpose-built public view; the view exposes published facility fields, a minimal verified ophthalmology summary, and approved-source attribution while excluding raw snapshots and private fields. Bbox queries use PostGIS against the existing GiST geography index. Keyset cursors keep viewport lists bounded at 100/500 and search at the P0-specified 20 records.

**Tech Stack:** Next.js 16 App Router, TypeScript, `pg`, Vitest, PostgreSQL/PostGIS.

---

## Files

- Create `apps/web/package.json`, lockfile, TypeScript and Next configuration for a server-only API package.
- Create `apps/web/src/lib/public-api/{types,validation,repository,handlers}.ts` for response types, input validation, repository access, and injectable handlers.
- Create `apps/web/src/app/api/facilities/route.ts`, `apps/web/src/app/api/facilities/[id]/route.ts`, `apps/web/src/app/api/search/route.ts`, and `apps/web/src/app/api/meta/categories/route.ts` as GET-only Route Handlers.
- Create Vitest unit tests for validation, route behavior, response safety, and error mapping; create PostGIS integration tests using synthetic facilities only.
- Create `db/migrations/011_public_api.sql`, `db/tests/011_public_api.sql`, and `scripts/provision-public-api-login.sql` for the safe view and least-privilege API role.
- Update `scripts/test-db.sh` and `.github/workflows/collector.yml` to run API unit, integration, typecheck, lint, and Next build gates.
- Create `docs/api/p7-public-api.md` documenting the contract and security boundary.

## Tasks

### Task 1 — Route and validation tests (RED)

- [x] Write tests for missing/malformed/out-of-range bbox, invalid and excessive limit, invalid region/category/cursor, UUID validation, empty-result responses, 404 detail, prefix/exact search, all public categories, and generic 500 responses.
- [x] Run the tests and confirm expected failures because handlers/validators are not implemented.

### Task 2 — API package and pure handlers (GREEN)

- [x] Add the minimal Next/TypeScript/Vitest package and scripts.
- [x] Implement strict validation, bounded keyset pagination, allowlisted JSON output, uniform `{data, meta, error}` envelopes, and injectable repository handlers.
- [x] Run unit tests, typecheck, lint, and build.

### Task 3 — Safe database view and role

- [x] Add a `public.published_facility_api` view with only published WGS84 facilities, allowlisted verified-evidence summary, and approved-source attribution.
- [x] Add a dedicated no-login read role with SELECT only on that view, plus a separate disposable-test login provisioning script.
- [x] Add SQL tests proving private tables/raw payloads are inaccessible and personal representative/responsible-person values are absent from the view.

### Task 4 — Parameterized repository and PostGIS tests

- [x] Implement bbox via `ST_Intersects(geog_wgs84, ST_MakeEnvelope(... )::geography)` and deterministic category/region filtering with keyset cursors.
- [x] Implement detail and normalized-name exact/prefix search with explicit column selection and hard limits.
- [x] Test 3 synthetic inside facilities, 1 outside facility, multiple categories/regions, empty results, evidence/attribution, database role boundaries, and an index-compatible GiST query plan.

### Task 5 — CI and documentation

- [x] Add API tests, lint, typecheck, and production build to CI; run database integration against the disposable PostGIS harness.
- [x] Document endpoint parameters, response/error schemas, cursor behavior, WGS84 bbox semantics, safe public fields, exclusions, and runtime `PUBLIC_API_DATABASE_URL` role.
- [x] Run P1–P5 regressions, API tests, lint, typecheck, build, CI-equivalent DB tests, and `git diff --check`.
