# P12 Scheduler and Worker Runbook

This runbook covers local or controlled synthetic execution. P14 will select the production deployment boundary. `docker compose up` does not start a scheduler or worker.

## Environment

Use distinct PostgreSQL runtime credentials and set `SYNC_DATABASE_URL`, `DATABASE_URL`, and `ETL_DATABASE_URL` as described in `services/collector/.env.example`. Do not use `DATABASE_ADMIN_URL` or `ADMIN_DATABASE_URL` for worker execution. `WORKER_ID` is optional; `WORKER_POLL_SECONDS` defaults to 5 and accepts 1–300 seconds.

## Commands

From `services/collector`:

```powershell
python -m eye_collector.cli scheduler --once
python -m eye_collector.cli worker --once
python -m eye_collector.cli worker --loop --poll-seconds 5
```

The scheduler only queues due eligible policies. `worker --once` processes at most one claim and exits. `worker --loop` polls until interrupted. Neither command enables a policy. Policies are disabled by default; source admission remains a separate, human-controlled operation. The initial adapter registry contains only synthetic `fixture` records.

## Observe and recover

Use `/admin` → **同步来源**, **同步任务**, and **同步告警** to inspect schedule state, task stage/attempts, last safe error, and alerts. **立即运行** enqueues an asynchronous task and returns; it never runs collection in the web request. **暂停同步** and **恢复同步** affect future schedule claims and are audited. They do not change `source_catalog.status`.

Tasks with `retry_wait` become claimable at `not_before`; no operator sleep or manual state edit is needed. Expired leases are reclaimed by the next worker. For `dead_letter`, inspect the sanitized error and source policy before using Run Now. A schema, rights, or access issue needs review and a code/source approval change through its normal governance path; do not repeatedly retry it.

One sync task may have multiple `import_runs` if collection had to retry. A successful collection advances the task to `etl` with one `import_run_id`; ETL retry reuses that same run. Only full collection plus scoped ETL success completes a task.

## Operational boundaries

Do not enable Beijing, Shenzhen, Tianjin, Guangzhou, Dazhou, Yichang, or any other real source from P12. Do not use manual-only files as worker inputs. No production data, geocoder, facility publication, email/SMS/Slack notifications, or cloud scheduler is part of this runbook.
