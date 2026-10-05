# P14 Backup and Recovery

## Backup

Use an operator-only `DATABASE_ADMIN_URL`, set `APP_ENV`, and set `P14_BACKUP_DIR` to an access-controlled directory outside the repository. Run `scripts/backup-db.sh`. The script uses PostgreSQL custom format, writes mode 0600, and names files `eye-map-<environment>-<UTC timestamp>-<commit>.dump`. It fails if the destination resolves inside the checkout or is not configured.

Backups may contain raw source records. Store only in private, access-controlled, encrypted-at-rest storage with an approved retention policy. Never put dumps in Git, CI artifacts, or public object storage. Retention duration and cloud backup/PITR are intentionally unspecified and were not verified.

## Restore

Provision all expected database roles, then create a new empty recovery database from `template0`. Set `RESTORE_DATABASE_URL`, `RESTORE_BACKUP_FILE`, and `RESTORE_CONFIRM` to exactly the target database name. Production-like names are rejected, and the restore tool checks that the target has no user schemas or objects before proceeding. It does not drop or overwrite existing objects. The archive restores object grants; role provisioning must happen before restore. Never test restore against production.

After restore, verify `schema_migrations` checksums through 016, runtime role permissions (including the correction submitter), synthetic published-facility query, audit history, source snapshot count, PostGIS location, health readiness, and public API smoke. Record backup size and backup/restore durations as drill measurements, not an SLA.

## Recovery checklist

- [ ] Stop scheduler and workers; preserve incident logs without secrets or precise user coordinates.
- [ ] Select a verified private backup and a disposable, isolated target.
- [ ] Confirm target name twice and run restore.
- [ ] Verify migration registry/checksums and key synthetic data invariants.
- [ ] Run readiness and public API smoke; verify nearby POST does not expose coordinates in URL/logs.
- [ ] Obtain release owner approval before routing traffic or restarting schedules.
- [ ] Document recovery point, measured recovery time, and follow-up fixes.

P14-A did not have staging DB credentials; an actual staging restore drill remains pending credentials. Disposable CI drill status must be reported from its CI run, not inferred from the runbook.
