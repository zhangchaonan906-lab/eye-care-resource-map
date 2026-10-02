# P14-B Production Release Readiness — implementation plan

## Goal

Deliver an honest, reviewable production-readiness baseline after P14-A PR #25 merged. Record verified evidence and external blockers, improve release-gate metadata validation, and document provider/source decisions without claiming deployment, rights, production data quality, or launch readiness that has not been verified.

## Scope

1. Confirm this worktree is based on the merged `main` commit and use branch `p14b-production-readiness`.
2. Inspect the current release gates, P14-A runbooks, and P5/P6 source evidence. Record missing staging/provider credentials without exposing secret values.
3. Update every gate record with `status`, `owner`, `evidence`, `requiredAction`, and `verifiedAt`. Preserve PENDING where an external proof is missing; separate local engineering proof from real staging proof.
4. Add a shared release-gate manifest validator and unit tests so both staging and production guards fail closed when required gate metadata is missing or malformed.
5. Write the P14-B blocker dashboard, basemap decision, and coordinate-provider decision. Make no provider selection absent complete documented terms/approval.
6. Correct the stale P5 pilot README by marking it superseded and linking the final pilot report; reconcile current local app DB counts separately from historical P5 pilot DB counts.
7. Run the focused release-tool tests, repository checks, and diff validation. Confirm the production guard still exits non-zero.
8. Commit the docs/tooling-only change, push the branch, and open a clearly labeled partial-readiness PR if checks pass. Do not merge or claim P14-B completion.

## Explicit boundaries

- No cloud deployment, database migration, production data import/publication, geocoder call, real-source schedule, basemap activation, or account/provider setup.
- No public OSM tile service in production.
- No final release-review document until actual final release review.
- External conditions remain PENDING and production launch remains NO-GO.

## Verification

- Node unit tests for release-gate metadata validation.
- `node scripts/check-production-release.mjs` must remain blocked (non-zero).
- `node scripts/check-staging-release.mjs` must remain blocked (non-zero) without staging environment.
- `git diff --check` and review changed-file list.
