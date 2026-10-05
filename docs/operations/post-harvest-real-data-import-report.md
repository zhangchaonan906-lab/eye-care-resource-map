# Post-Harvest Real-Data Import Report

Date: 2026-10-05
Baseline: Round 5 PR #31 squash merge `7142c34d9aedf51b70bbf90e4f4447026ab4a317`
Branch: `post-harvest-controlled-import`

## Outcome

**Status: `BLOCKED_RIGHTS` (partial completion of Phase 1).** The nine locally verifiable sources received individual rights decisions and their local artifact metadata was revalidated. No reviewed source has explicit source-specific evidence authorizing durable secondary storage, processing, and use of derived institution fields in the public application. No import was attempted.

The Harvest Store files are user-local quarantine artifacts and are not included in Git. The 18 Round 2/3 historical-only sources remain `REACQUIRE_REQUIRED`; originals and row-level ledger are unavailable for current verification.

## Rights decisions

| Decision | Sources |
| --- | ---: |
| `APPROVED_FOR_CONTROLLED_IMPORT` | 0 |
| `APPROVED_FOR_DISPLAY` | 0 |
| `INSPECTION_ONLY` | 0 |
| `RIGHTS_REVIEW_REQUIRED` | 8 |
| `BLOCKED_RIGHTS` | 0 |
| `STALE` | 1 |
| Tier A sources / approved | 3 / 0 |
| Historical-only `REACQUIRE_REQUIRED` | 18 |

Tier A comprises three Guangzhou licensing workbooks with diagnostic-subject fields. Their combined local source files contain 292 rows and 105 explicit eye-evidence rows, but those are quarantined-source inspection statistics only; they were not imported and are not application candidates. The wider nine-file local baseline is 5,007 rows and 132 explicit eye-evidence rows, as previously recorded in the Harvest manifest. These figures do not establish cross-source unique institutions.

The Jiangyin file is a single Q2 2025 registration event, not a registry, and is stale. Its portal copyright statement requires prior authorization for covered copying/republication; applicability to the spreadsheet and derived records remains unresolved.

## Revalidation

All 9 current local sources were rechecked for file existence, byte size, SHA-256, metadata and inspection sidecars, schema/headers, row count, source URL, region, and stated scope. All 9 passed. Personal-name column labels and values are excluded from this report and the public rights metadata. Guangzhou and Wuxi workbooks contain unnecessary natural-person-name fields; any future approved onboarding must explicitly exclude them.

No source-specific durable-storage, processing, derived-display, commercial-use, retention, or withdrawal permission was established beyond the per-source qualifications in [the rights matrix](../data-sources/nationwide/source-rights-triage.md).

## Import and publication results

| Measure | Result |
| --- | ---: |
| Import runs | 0 |
| Raw rows imported | 0 |
| Immutable source snapshots written | 0 |
| Candidates persisted | 0 |
| Imported explicit eye evidence | 0 |
| Distinct imported eye candidates | 0 |
| Database duplicate cases / region conflicts / terminal skips | 0 / 0 / 0 |
| Replay idempotency | NOT RUN — no import was authorized |
| Ready except coordinate | 0 |
| Needs duplicate review | 0 |
| Needs rights review | 0 persisted candidates; 9 sources remain under source-level review/stale status |
| Production DB writes | 0 |
| Isolated real-data DB writes | 0 |
| Real geocoder calls | 0 |
| Facilities published / automatic publish | 0 / NO |
| Source approvals changed | 0 |
| Raw source files committed to Git | NO |

The pre-existing Wuxi/Jiangyin ambiguous campus note was not converted into a database duplicate case because no candidate data was persisted. Existing release-gate statuses were not changed; `REAL_PUBLISHED_DATA_SAMPLE` remains unmet.

## Why import did not proceed

The required rights gate failed for every source. Creating an isolated database or running real-data dry-runs before a source has permission for project storage and processing would cross the user's rights boundary. Docker Desktop's local PostGIS engine is also unavailable in this environment; database and P13 system E2E checks must run in GitHub Actions. This environment limitation did not cause or override the rights decision.

## Required clearance

Obtain written, dataset-specific terms from each source owner that cover: durable storage and retention; processing; use of derived institution fields in this public app, including commercial use; attribution; withdrawal/deletion; and treatment/exclusion of unnecessary natural-person-name fields. Keep each source `UNKNOWN` / `manual_only` until its own evidence is reviewed. After clearance, revalidate the exact file hash and scope, create the isolated current-schema database with least-privileged roles, and only then run the approved-file-bound dry-run and scoped import.
