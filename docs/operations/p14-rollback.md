# P14 Rollback Runbook

1. Identify the release from `/api/version` and the release manifest. Stop the rollout if readiness is failing or a privacy/security gate regresses.
2. Web rollback: redeploy the previous known-good commit/image and verify `/api/health/live`, `/api/health/ready`, version, map shell, and admin login.
3. Worker rollback: stop scheduling new work, drain or safely requeue in-flight tasks, then run the previous immutable collector image. Do not move a long-running worker into a Web request runtime.
4. Database changes have no automatic down migration. Prefer a reviewed forward fix. If data integrity is compromised, stop writers and restore a verified private backup to an explicitly named non-production target before any operator-approved recovery action.
5. Re-run migration checksum verification, least-privilege checks, staging smoke, and nearby privacy checks. Record incident, release IDs, backup/restore timings, and follow-up actions.

No staging or production rollback was rehearsed against a cloud service in P14-A because no deployment credentials were available.
