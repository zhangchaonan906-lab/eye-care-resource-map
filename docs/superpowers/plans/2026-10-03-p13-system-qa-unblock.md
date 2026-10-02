# P13.1 System QA Unblock Implementation Plan

> **For agentic workers:** Execute this plan task by task in the existing `p13-comprehensive-qa` worktree. Preserve PR #24; do not merge it or start P14.

**Goal:** Add deterministic real-browser system E2E against an isolated disposable PostGIS database, worker/scheduler, authenticated review UI, public API, hostile inputs, and 500-facility viewport stress, while keeping production launch blocked by real-data gates.

**Architecture:** Reuse the existing PostGIS Compose service and one shared database bootstrap implementation for migrations 001–015 and runtime-role provisioning. A dedicated P13.1 orchestrator creates a random isolated Compose project, provisions synthetic fixture-only state and random credentials, runs the real Next server and Playwright system tests, scans artifacts, and always removes volumes. System tests use HTTP and SQL only for state assertions/setup; candidate creation, change ingestion, geocoding, and reviewer decisions exercise their actual application pipelines and UI.

**Tech Stack:** PostgreSQL/PostGIS 17, Python Collector CLI and SyncWorker, Next.js route handlers, Playwright Chromium, Node.js orchestration, existing npm/pytest/Ruff/mypy gates.

---

### Task 1: Inspect P11/P12 contracts and establish shared DB bootstrap

**Files:** `scripts/test-db.sh`, `scripts/test-db.ps1`, new `scripts/db-test-bootstrap.mjs`, new `scripts/test-p13-system-e2e.mjs`.

- Extract migration 001–015 ordering, required test fixtures, and runtime-role provisioning from existing DB setup into one reusable helper.
- Keep the existing P1–P13 disposable DB regression behavior unchanged.
- Make system orchestration generate an isolated Compose project, random runtime passwords, web auth settings, and unconditional volume cleanup.

### Task 2: Add deterministic test-only worker injection

**Files:** `services/collector/src/eye_collector/cli.py`, `services/collector/src/eye_collector/sync/registry.py`, `services/collector/src/eye_collector/sync/worker.py`, focused Collector tests.

- Keep the production adapter allowlist limited to its current fixture adapter.
- Gate test-only fixture revision and synthetic source identities/failure transports behind an explicit test-only environment setting.
- Exercise stable and updated snapshots through the actual SyncWorker and scoped ETL.

### Task 3: Add real browser lifecycle and reviewer coverage

**Files:** `apps/web/e2e/system-golden-path.spec.ts`, `apps/web/e2e/hostile-input.spec.ts`, `apps/web/e2e/system-stress.spec.ts`, small stable `data-testid` additions only when accessible roles are insufficient.

- Real login via `/admin/login`; real route handlers and PostgreSQL roles; no route mocks or forged cookies.
- Exercise candidate, location, facility, duplicate decisions and full public API visibility/removal/republish/withdraw behavior.
- Verify hostile query and admin filters/actions do not leak SQL/database internals or mutate persistent tables.
- Runtime-generate 500 source-backed synthetic published rows; rapidly change viewports and assert request cancellation/current viewport consistency without timing thresholds.

### Task 4: CI, evidence, and status reporting

**Files:** `.github/workflows/collector.yml`, `apps/web/package.json`, `apps/web/playwright.config.ts`, system artifact scanner, `docs/operations/p13-qa-matrix.md`, `docs/operations/p13-qa-report.md`, `docs/operations/p13-performance.md`.

- Add isolated `p13-system-e2e` CI job with no production network dependencies and always-run cleanup.
- Run every existing unit, DB, browser, accessibility, static, and dependency gate.
- Mark each SYSTEM QA criterion PASS only after observing its assertion in a fresh run; retain REAL-DATA as pending, overall PARTIAL, production launch NO-GO, and P14 unexecuted.
- Push commits to the existing P13 branch and update PR #24 only after local/CI evidence.
