# P12 Incremental Sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a durable and policy-gated scheduler/worker that imports immutable snapshots, records deterministic NEW/CHANGED/UNCHANGED events, runs ETL for only the successful import run, and exposes audited sync controls to P11 admins.

**Architecture:** Keep collector, ETL, scheduler, and sync worker credentials separate. Migration 014 adds sync policy/task/change/alert tables and fixed SECURITY DEFINER transition functions; Python registry/runner code executes only registered adapters and reuses the current CollectorRunner and Pipeline. P11 admin routes only enqueue or change sync policy state; the worker owns long-running collection and scoped ETL. Changes never publish or geocode facilities.

**Tech Stack:** PostgreSQL/PostGIS, psycopg 3, Python 3.12, existing CollectorRunner/HTTP client/ETL pipeline, Next.js App Router, Vitest, pytest, Ruff, mypy, Docker Compose.

---

## Existing implementation facts

- Migrations 001–013 already define source approval and access policy, immutable `source_records`, `import_runs`, P3 scoped `Pipeline.run(import_run_id=...)`, P11 admin authentication/CSRF/idempotency/audit, and dedicated public/ETL/geocode/admin runtime roles.
- `CollectorRunner.run` currently counts only `inserted`/`unchanged`; `PostgresRepository.insert_snapshot` inserts idempotently but does not classify first-seen versus revised source keys.
- `ETLRepository.fetch_pending` accepts an optional import run scope and currently supports the existing manual-only approved source behavior. Preserve that path while adding automated-source runs.
- `HttpClient` already owns network timeouts, bounded retries, response size limits and safe errors. Reuse it; task deadline must be checked at collection/ETL checkpoints.
- GitHub Actions runs `scripts/test-db.sh`, collector unit/lint/typecheck, Web unit/lint/typecheck/build, and diff checking. P12 CI tests remain synthetic/offline.

## File map

- Create `db/migrations/014_incremental_sync.sql`, `db/tests/014_incremental_sync.sql`, and `scripts/provision-sync-worker-login.sql` for policy/task/change/alert schema, DB transition functions, role grants and regression coverage.
- Modify `services/collector/src/eye_collector/models.py`, `runner.py`, and `db.py`; add focused `changes.py`, `sync/models.py`, `sync/repository.py`, `sync/registry.py`, and `sync/worker.py` modules. Extend `sources/fixture.py` for stable/updated revisions and add tests under `services/collector/tests/sync/` plus focused runner/repository/ETL tests.
- Modify `services/collector/src/eye_collector/cli.py`, `.env.example`, `scripts/test-db.sh`, and `scripts/test-db.ps1`; add optional `worker` Compose profile only if it remains disabled by default.
- Extend `apps/web/src/lib/admin/repository.ts`, admin API routes and `/admin` console for task/alert views and RUN_NOW/PAUSE_SYNC/RESUME_SYNC. Extend migration 014 with separate admin decision functions; do not give admin runtime direct sync-table updates.
- Create `docs/operations/p12-incremental-sync.md`, `docs/operations/p12-worker-runbook.md`, and `docs/api/p12-admin-sync.md`.

## Task 1: Incremental classification contract

1. Add failing unit tests for deterministic recursive JSON paths, stable ordering, list-as-whole-field changes, 100-path truncation, and NEW/CHANGED/UNCHANGED classification semantics.
2. Run those tests and verify failures identify the missing module/behavior.
3. Implement pure deterministic classification/diff functions in `changes.py`; never copy old/new raw values into event payloads.
4. Add `new` and `changed` to run/task count output while preserving `inserted == new + changed` and current `unchanged` behavior.
5. Run focused tests, then commit the contract and implementation.

## Task 2: Sync schema and DB authorization boundary

1. Add SQL regression tests first for policy validation, active-task uniqueness, due scheduling, manual-only/pending/suspended source denial, worker/admin/public role privileges, task transitions, alerts, and source-record erasure with related change events.
2. Implement migration 014 with `source_sync_policies`, `source_sync_tasks`, `source_change_events`, and `source_sync_alerts`; enforce a single active task per source+region with a partial unique index. FK behavior for change events must allow existing source erasure (`ON DELETE CASCADE` or nullable references plus erasure regression).
3. Implement safe `SECURITY DEFINER` transaction functions for schedule enqueue, manual enqueue, claim/reclaim, heartbeat, retry/dead-letter, successful finish, pause/resume, and alert visibility. Fix search paths and revoke execute from PUBLIC and `eye_public_api`.
4. Add `eye_sync_worker` NOLOGIN and provision a separate `eye_sync_worker_runtime` login using `SYNC_DATABASE_URL`; admin sync controls go through separate narrowly scoped functions and P11 runtime remains unable to update task tables directly.
5. Apply migrations 001–014 in the disposable DB test, run focused SQL tests, and commit.

## Task 3: Scheduler and adapter registry

1. Add failing tests for due/not-due/disabled/paused policies, automated access gate, pending/suspended source exclusion, duplicate scheduler race, advancing `next_due_at` from the injected current time without catch-up storm, and allowlisted adapter descriptor/catalog matching.
2. Implement an explicit code registry keyed by `adapter_key`; never import module paths or use DB-supplied endpoint URLs. Initially register only synthetic `fixture`.
3. Implement `scheduler --once` as a DB transaction that locks due policies with `FOR UPDATE SKIP LOCKED`, enqueues idempotently, and advances each due time from now. It performs no HTTP or ETL.
4. Verify racing scheduler transactions produce one active task and that no real source schedule is enabled; commit.

## Task 4: Atomic snapshot classification and change events

1. Add failing DB-backed tests for first-seen NEW, exact replay UNCHANGED, revised-key CHANGED with prior record link and stable changed paths, concurrent source-key writers, no raw-value duplication, immutable snapshots, and erase behavior.
2. Add repository operation that takes an advisory transaction lock for `(source_id, source_key)`, classifies and inserts the immutable snapshot, then records one durable event for NEW/CHANGED in the same transaction. Keep the existing unique snapshot key as the final idempotency guard.
3. Update `CollectorRunner` counts/logs and import run counts so `new + changed == inserted`; exact existing hash remains unchanged. Do not infer deleted/missing records.
4. Run unit and DB regression tests, then commit.

## Task 5: Worker lifecycle, retry and ETL scope

1. Add failing tests for one-task claim, unexpired lease exclusion, expired lease reclaim, heartbeat checkpoints, injected monotonic timeout, retryable versus terminal error classes, persisted exponential `not_before`, max-attempt dead-letter alert, severe policy/schema pause, consecutive-failure pause, success reset, and source A failure not blocking source B.
2. Implement `worker --once` and `worker --loop --poll-seconds` with injectable wall/monotonic clocks. Claim/reclaim through DB functions, use allowlisted adapters, reuse CollectorRunner, and check deadline at safe checkpoints.
3. On successful collection, invoke `Pipeline.run(import_run_id=current_run_id)` using `ETL_DATABASE_URL`; ETL errors keep stage `etl` and retry against the same run. A retry during collection may create a new import run.
4. Enable approved `automated_access_allowed` runs in the ETL repository without breaking approved manual-only scoped ETL. Failed or unapproved runs remain blocked.
5. Ensure sync worker, collector and ETL each use distinct runtime URLs and their existing table boundaries. Run tests and commit.

## Task 6: Admin sync API and console

1. Add failing tests for authenticated+same-origin+CSRF RUN_NOW/PAUSE_SYNC/RESUME_SYNC, idempotent replay, unauthorized/missing CSRF rejection, manual-only `MANUAL_FILE_REQUIRED`, and refusal to enqueue after source suspension.
2. Add P11 SECURITY DEFINER admin decision functions with reason and request UUID audit records. RUN_NOW only enqueues and returns task ID; no collector, HTTP, or ETL call is permitted in Next.js.
3. Extend safe admin projections for paginated policies/tasks/alerts and add `/api/admin/sync/[sourceId]/decision`; preserve actor identity from the verified P11 session only.
4. Add an “增量任务” admin tab showing policy state, due/success timestamps, latest task attempt/stage/safe error, and open alerts with RUN_NOW/pause/resume actions. Preserve import runs as a separate read-only view.
5. Run Web unit, DB integration, typecheck, lint and build, then commit.

## Task 7: CLI, configuration, docs and full regression

1. Add CLI tests for `scheduler --once`, `worker --once`, `worker --loop`, injected/no-sleep poll behavior, and unchanged legacy commands (`run`, `process`, `geocode`, `pilot`, `inspect-file`).
2. Add `SYNC_DATABASE_URL`, optional `WORKER_ID`, and `WORKER_POLL_SECONDS` to `.env.example` with no secrets. If Compose gets a worker service, guard it behind an inactive `worker` profile.
3. Extend both `scripts/test-db.sh` and `scripts/test-db.ps1` to apply 014, provision disposable sync worker credentials, run SQL tests and Python/Web DB suites; update CI only where needed. Keep test traffic synthetic.
4. Document scheduling, no catch-up, task/lease state machine, retries, failure isolation, source access gate, manual-only boundary, change semantics, scoped ETL, alerts, P11 handoff, no disappearance inference, no geocoding/publishing, and deployment deferred to P14.
5. Run full collector/database regressions, Web unit/database tests, Ruff, mypy, TypeScript, lint, build, secret/log safety checks, and `git diff --check`. Confirm no real data, approval changes, geocoder, or facility publication.
6. Commit, push `p12-incremental-sync`, create PR titled `实现增量同步、任务调度与来源变更检测（P12）`, and wait for GitHub Actions. Do not merge this P12 PR.

## Acceptance coverage map

- Scheduling, no catch-up, races and source gates: Tasks 2–3.
- Queue state, leasing, heartbeats, recovery, timeout, retries, backoff, dead letters, failure isolation, policy pauses and durable alerts: Tasks 2 and 5.
- NEW/CHANGED/UNCHANGED, stable bounded changed paths, immutable snapshots and erasure: Tasks 1 and 4.
- Scoped ETL and manual-only compatibility: Task 5.
- P11 admin auth/CSRF/idempotency/audit and sync visibility/actions: Task 6.
- Legacy command compatibility, CI, docs and prohibition checks: Task 7.
- P12 never creates deleted/missing events, calls a geocoder, imports real data, changes source approval, or publishes a facility.
