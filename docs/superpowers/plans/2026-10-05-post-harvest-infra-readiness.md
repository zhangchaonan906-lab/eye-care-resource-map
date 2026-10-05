# Post-Harvest Infrastructure & Product Readiness Implementation Plan

> **For agentic workers:** This plan is being executed inline in the existing isolated worktree; tasks are ordered by dependency and verification checkpoints.

**Goal:** Improve infrastructure and empty-data product readiness while preserving the no-application data freeze and keeping unverified external deployment gates pending.

**Architecture:** Use isolated staging configuration/runbooks, no real-source imports, and fail-closed provider decisions. Add bounded correction reports to a database-backed review queue, distributed API throttling at server route boundaries, and clear empty/limited-coverage UI. Live cloud resources remain unclaimed until configured and observed.

**Tech Stack:** Next.js 16, React 19, PostgreSQL/PostGIS migrations and integration tests, TypeScript/Vitest/Playwright, Python collector pytest/Ruff/mypy, GitHub Actions.

---

### Task 1: Baseline and deployment inventory

**Files:** existing release docs, `docs/operations/p14-release-gates.json`, `.github/workflows/collector.yml`.

- [x] Confirm branch starts at PR #33 squash merge and worktree is clean.
- [x] Run existing collector and web unit/static checks before implementation; baseline Collector full pytest needs DB env for its system marker, and CI-scoped tests pass.
- [x] Inventory which current release gates have local evidence versus external credentials/provider dependencies.

### Task 2: Provider decisions and readiness evidence

**Files:** `docs/operations/p14-coordinate-provider-decision.md`, `docs/operations/p14-basemap-decision.md`.

- [x] Re-check official AMap, Baidu, MapTiler, and MapLibre/service documents and pricing.
- [x] Keep coordinate and basemap decisions `PENDING` unless every China, rights, attribution, pricing, and production-operation criterion is evidenced.
- [x] Document candidate, disqualifying gap, forbidden public OSM tile server, and no real API calls.

### Task 3: Correction review queue

**Files:** new migration `db/migrations/016_correction_reports.sql`; database test; Next.js feedback API/schema/UI/admin queue and tests; `db/migrations/manifest.json`.

- [x] Add failing DB/API/UI tests proving bounded reports queue without changing a facility.
- [x] Run tests to observe expected failures.
- [x] Add a report table, constrained categories/statuses, least-privilege submit/read/disposition functions, privacy-safe form, and authenticated review queue.
- [x] Pass DB integration in a disposable PostGIS environment; P1–P13 database regression and correction report migration tests passed in GitHub Actions run 37325065806. Local Docker daemon is unavailable.

### Task 4: Empty and limited-data UX

**Files:** `apps/web/src/features/eye-map/eye-hospitals-client.tsx`, `apps/web/src/features/eye-map/facility-detail-content.tsx`, related components/tests/CSS.

- [x] Add failing component tests for explicit ongoing coverage notice and empty map/search/nearby states.
- [x] Implement only explanatory text, retry/search/region navigation, and correction entry; do not seed or display synthetic facilities.
- [x] Pass unit and P13 accessibility/E2E tests.

### Task 5: Production rate limiting

**Files:** new server-only limiter/config module, affected API route handlers, tests, environment matrix and runbook.

- [x] Add tests for shared backend call, retry metadata, and fail-closed behavior in staging/production.
- [x] Implement a shared provider-backed limiter plus deterministic local/test implementation, with no raw-IP logging and trusted-proxy assumptions documented.
- [x] Cover facilities, search, nearby, detail, correction submission, and admin session/login.
- [x] Keep `PRODUCTION_RATE_LIMITING=PENDING` until provider secrets and live multi-instance evidence are configured.

### Task 6: Staging/worker/monitoring/recovery readiness

**Files:** `docs/operations/p14-staging-release.md`, environment matrix, monitoring, backup/restore, release gates, deploy configuration as supported by the selected host.

- [x] Define isolated web/database/worker deployment, secrets, migration, fixture-only runtime and rollback steps.
- [x] Document that exact coordinates are absent from app logs and that no real-source schedules are enabled; live host-log and scheduler evidence remains pending.
- [x] Add health/worker/sync/backup signals and alert exercises to the operations runbook; external alert exercises need credentials.
- [x] Keep staging, worker, remote backup restore, deployed privacy, headers, and monitoring pending without live evidence.

### Task 7: Verification and PR

**Files:** release-gate docs and branch diff.

- [x] Run Collector unit, Web unit, Ruff, mypy, lint, typecheck, build, P13 E2E/accessibility, P14 release tools, secret scan, and `git diff --check`; GitHub Actions run 37325065806 also passed the database regression, disposable backup/restore, and P13 system E2E gates.
- [x] Re-read each requirement and release-gate status; report unavailable external evidence as `PENDING`.
- [x] Commit in small coherent changes, push `post-harvest-infra-readiness`, and open PR #34 with the requested title; CI passed.
