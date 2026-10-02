# P12 Incremental Sync

P12 adds durable, interval based collection scheduling for explicitly registered adapters. It does not approve sources or configure any real source for automatic collection. Migration `014_incremental_sync.sql` creates policy, task, change event, and alert records in `app_private`.

## Source gate and policy

The scheduler and database claim function require `source_catalog.status = 'approved'` and `access_policy = 'automated_access_allowed'`. Pending, suspended, `manual_only`, and `manual_review_required` sources are ineligible. A schedule pause only pauses that schedule; it never changes source approval. Run Now on a manual file source returns `MANUAL_FILE_REQUIRED`.

Policies are disabled by default. A policy can only use a code registered in `AdapterRegistry`; the worker checks the registered source name and catalog URL against the approved catalog row. Database values cannot specify Python imports, arbitrary endpoints, or test fixture revisions.

## Scheduling and task state

Run `python -m eye_collector.cli scheduler --once` from the collector package. The scheduler only locks due policies with `FOR UPDATE SKIP LOCKED`, enqueues one task per source and region, and advances `next_due_at` from the current scheduler time. This intentionally avoids catch-up storms after downtime. A partial unique index prevents more than one active task for a source and region.

Tasks move through `queued → running → succeeded`. Failures can move `running → retry_wait → running`; exhausted or non-retryable failures move to `dead_letter`. `stage` tracks `collect`, `etl`, and `complete`. A task retains its state and safe counts. Collection retries may create another `import_run`; ETL retries reuse the successful run already attached to the task.

Workers claim work under a row lock and a bounded lease. A live lease prevents another worker from claiming the task. An expired lease is safely reclaimed; an invalid or no-longer-approved source is dead-lettered without running the adapter. Heartbeats run at collection and ETL checkpoints. A monotonic deadline bounds the task, while HTTP and database operations retain their own timeouts.

## Snapshot changes and ETL

`NEW` means a `source_key` has not appeared before. `CHANGED` means the key exists with a different canonical content hash. `UNCHANGED` means the exact key and hash already exist. A per-source-key advisory transaction lock serializes the classification and insert. Snapshots remain immutable; `source_change_events` stores only record references, sorted changed paths, and a truncation flag. It does not copy raw values.

Absence from an import is not evidence of deletion. There is no `DELETED` or `MISSING` classification, no automatic facility withdrawal, and no inference that a partial file or API page is complete. Source erasure cascades change-event rows with the erased snapshot.

On collection success, the worker runs P3 ETL scoped to that exact successful `import_run_id`. It never sweeps unrelated sources. Candidate records and duplicates remain subject to P11 human review. P12 does not call the geocoder, update published values, or publish facilities.

## Failure handling and alerts

Timeouts, temporary database/network errors, exhausted 429/5xx retries, and ETL errors are retryable within the task attempt limit. Policy, access, adapter configuration, and schema errors are non-retryable and pause the schedule where appropriate. Backoff is persisted as `not_before`, using `min(base × 2^(attempt-1), maximum)`. Consecutive failures pause only the schedule. Alerts are durable and visible in `/admin`; external notification integrations are deferred.

Worker and scheduler credentials use `SYNC_DATABASE_URL` and the separate `eye_sync_worker` role. Snapshot writes use `DATABASE_URL`; ETL uses `ETL_DATABASE_URL`; the web administrator uses `ADMIN_DATABASE_URL`. Runtime worker access is through explicit security-definer transitions, not direct sync-table mutation.

## Current safety scope

Only packaged synthetic fixture data is registered in the worker adapter registry. No real data was imported, no real source schedule was enabled, no source approval changed, no geocoder call was made, and no facility was published. Deployment of scheduler and worker processes is deferred to P14. Do not add a production scheduled GitHub Actions workflow from this stage.
