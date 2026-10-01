# P2 Source Collection Framework Implementation Plan

> **For agentic workers:** Implement task by task with test-first checkpoints. Keep the work on `p2-source-framework`; do not add P3 behavior.

**Goal:** Build a safe, auditable, idempotent collector framework that only runs explicitly approved sources and ships with an offline fixture source.

**Architecture:** A synchronous Python package separates adapter, policy, HTTP, repository, runner, and CLI. Postgres access is centralized and uses the existing P1 tables; HTTPX owns all network requests and enforces bounded retries and per-source throttling.

**Tech Stack:** Python 3.12, HTTPX, Psycopg 3, pytest, Ruff, mypy, PostgreSQL/PostGIS, GitHub Actions.

---

### Task 1: Package scaffold, config, models, and canonical hashing

**Files:**
- Create `services/collector/pyproject.toml`, `.env.example`, `.gitignore`
- Create `services/collector/src/eye_collector/{__init__.py,config.py,models.py,hashing.py,exceptions.py}`
- Create `services/collector/tests/test_config.py`, `test_hashing.py`

- [ ] Write tests for missing `DATABASE_URL`, range-checked timeout/size/retry settings, stable JSON hash across dict order, changed-content hash, and NaN rejection.
- [ ] Run the focused pytest selection and confirm expected failures.
- [ ] Implement typed immutable configuration/models and canonical JSON SHA-256.
- [ ] Run focused tests, Ruff, and mypy.
- [ ] Commit `build: scaffold source collector package`.

### Task 2: Source adapter contract and approval/policy gate

**Files:**
- Create `services/collector/src/eye_collector/sources/{__init__.py,base.py}`
- Create `services/collector/src/eye_collector/policy.py`
- Create `services/collector/tests/test_source_policy.py`

- [ ] Test approved, pending, suspended, unknown, missing-use-basis, missing-field-permission, blocked access policy, and payload with an unpermitted field.
- [ ] Verify the repository fake has no `create_import_run` call in every rejected case.
- [ ] Define adapter metadata and page/record protocol; enforce policy before runner can create a run.
- [ ] Run focused tests and static checks.
- [ ] Commit `feat: gate collector runs on approved sources`.

### Task 3: PostgreSQL repository and least-privilege grants

**Files:**
- Create `services/collector/src/eye_collector/db.py`
- Create `db/migrations/004_collector_permissions.sql`
- Create `db/tests/004_collector_permissions.sql`
- Create `services/collector/tests/test_repository.py`

- [ ] Unit-test parameterized insert/select/update behavior with a repository connection factory.
- [ ] Add a `NOLOGIN` collector role and grants limited to selecting source metadata and inserting/updating import runs and inserting/selecting source snapshots; do not grant writes to facility, candidate, duplicate, location, evidence, or audit tables.
- [ ] Add SQL tests asserting the grants and existing P1 unique/FK constraints.
- [ ] Run P1 plus new migration/database tests on fresh PostGIS.
- [ ] Commit `feat(db): add least-privilege collector grants`.

### Task 4: Shared HTTP client, retries, response bounds, and rate limits

**Files:**
- Create `services/collector/src/eye_collector/http.py`
- Create `services/collector/tests/test_retry.py`, `test_rate_limit.py`, `test_http_safety.py`

- [ ] Test 429 and 500 retry then success, timeout retry, 404 no retry, maximum attempts, Retry-After cap, deterministic jitter/sleep injection, per-source delay, response-size rejection, HTTPS-only requests, and User-Agent.
- [ ] Implement one HTTPX client abstraction with injected transport/clock/sleeper/random source and no adapter-level network escape hatch.
- [ ] Run focused tests without wall-clock sleeps, then Ruff/mypy.
- [ ] Commit `feat: add bounded HTTP retry and rate limiting`.

### Task 5: Fixture adapter and offline fixtures

**Files:**
- Create `services/collector/src/eye_collector/sources/fixture.py`
- Create `services/collector/src/eye_collector/fixtures/fixture/{page-1.json,page-1-updated.json,page-2.json}` (packaged synthetic fixtures so the installed CLI remains offline)
- Create `services/collector/tests/test_fixture_adapter.py`

- [ ] Test multi-page cursor traversal, 6–10 source records, a duplicate unchanged key across pages, updated revision, and mock responses for 429/500/timeout.
- [ ] Implement fixture requests through the shared HTTP client with `httpx.MockTransport`; ensure no public network transport is created for the fixture.
- [ ] Run focused tests and prove the adapter preserves source payload fields and source URLs.
- [ ] Commit `feat: add offline fixture source adapter`.

### Task 6: Import runner, lifecycle, idempotency, cancellation, and logs

**Files:**
- Create `services/collector/src/eye_collector/runner.py`
- Create `services/collector/tests/test_import_run.py`, `test_idempotency.py`, `test_logging.py`

- [ ] Test approval before run insert, running→succeeded, running→failed with safe summary, KeyboardInterrupt→cancelled, no permanent running record, same content unchanged, changed content inserted, correct counts, dry-run no snapshot writes, and secret-free structured logs.
- [ ] Implement repository conflict handling against `(source_id, source_key, content_hash)` and finalize run on every exit path.
- [ ] Run unit tests; inspect captured logs for query tokens, Authorization, Cookie, and secret values.
- [ ] Commit `feat: run approved source imports idempotently`.

### Task 7: CLI, fixture registration, documentation, and operator commands

**Files:**
- Create `services/collector/src/eye_collector/cli.py`
- Create `services/collector/README.md`
- Create `docs/data-sources/README.md`
- Create `scripts/seed-fixture-source.sql`
- Create `services/collector/tests/test_cli.py`

- [ ] Test CLI arguments, invalid config, fixture selection, region, limit, and dry-run forwarding.
- [ ] Document install, DB setup, least-privilege URL, source approval/registration, fixture run, dry-run semantics, retry/rate policy, and policy boundaries.
- [ ] Verify example commands use no real source and require no credentials committed to the repo.
- [ ] Commit `feat: add collector CLI and operating docs`.

### Task 8: Database test runner and CI

**Files:**
- Create `scripts/test-db.sh`
- Create `.github/workflows/collector.yml`
- Modify `scripts/test-db.ps1` only if needed to preserve equivalent local entrypoint behavior.

- [ ] Make the Linux script select an ephemeral loopback port, start a uniquely named Compose project, apply P1/P2 migrations and SQL tests, provision a test login as a member of the collector role, run database-marked pytest, and always remove the container/volume.
- [ ] Add CI jobs for Python unit tests, Ruff, mypy, database tests, and `git diff --check`, with no public network data source.
- [ ] Run the exact CI commands locally where supported; confirm YAML parses and DB cleanup succeeds.
- [ ] Commit `ci: verify collector and database contracts`.

### Task 9: Full verification and pull request

- [ ] Re-read the P2 spec and check every acceptance criterion against code and tests.
- [ ] Run unit tests, lint, typecheck, P1/P2 database tests, CLI fixture run, CLI dry-run, and `git diff --check`.
- [ ] Confirm `git status`, commit history, no `.env`, no production source or P3 files.
- [ ] Push `p2-source-framework` and create PR to `main` titled `建立 P2 数据来源采集框架`.
- [ ] Wait for CI and report only evidence-backed results using the requested P2 status template.
