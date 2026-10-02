# National Data Harvest Round 1 — execution plan

## Goal

Process the mainland 31 provincial planning units for the first national data-harvest pass using the existing P6 matrices. Reuse official source leads, inspect available official files, import only sources whose current policy/rights/access method and batch limits permit it, run scoped P3 ETL for authorized imports, and record every remaining blocker without lowering review gates.

## Sequence

1. Confirm PR #26 is merged and `main` is clean at its squash merge; create `national-data-harvest-round1` from that exact baseline.
2. Audit existing official source matrices, current gate/source state, and local P5/P6 file directories. Never copy raw source data into the repository.
3. Create a 31-unit checkpoint manifest and progress report before processing records. Preserve existing P6 evidence, scope labels, source statuses, and blocked-versus-rejected distinctions.
4. Process already available files first: recompute raw-byte SHA-256, size, format, sheet/header/row counts, safe quality aggregates, and in-memory adapter preview. Keep UNKNOWN sources inspection-only.
5. Revisit P6 official leads in their existing priority order. Use ordinary official pages and documented downloads only; stop a source on login, captcha, application, extra agreement, access denial, portal error, or unclear rights, then continue to the next province.
6. For currently APPROVED sources, verify exact permitted fields, `manual_only`/automated access policy, retention and withdrawal duties, and any P5 batch cap before importing. Do not change source approval, expand a pilot limit, transfer restricted files between environments, or bypass the P11 publication gate.
7. For each authorized import, use existing immutable provenance/import-run/idempotency path and immediately run P3 ETL scoped to the new import run. Geocoder calls and automatic facility publication remain zero.
8. Update each province to `COMPLETE_FIRST_PASS`, `PARTIAL`, or `BLOCKED` only with evidence; update source-coverage release-gate evidence without promoting the gate to PASS.
9. After each province, commit a small documentation/code checkpoint. Run Collector tests, Ruff, mypy, relevant DB tests, and `git diff --check` about every five provinces.
10. Generate the round-one report and ranked top-20 gap list from the checkpoint data. Verify all 31 units are terminal, the raw-file list is outside Git/Docker/CI, and production launch remains NO.
11. Push the single national branch and open one reviewable PR. Do not merge unless separately instructed or explicitly required by the reviewed PR policy.

## Non-negotiable boundaries

- Mainland only; Hong Kong, Macau, and Taiwan remain out of scope.
- No login, captcha, application, paid access, hidden/private API, robots/access-control evasion, rate-limit bypass, or third-party authoritative data.
- No UNKNOWN → APPROVED changes; no policy, publication-gate, or pilot-cap changes to make data importable.
- No geocoder calls, persistent production coordinates, direct SQL inserts into published facilities, or automatic real-facility publication.
- Raw XLS/XLSX/CSV/ZIP/JSON/XML files remain outside Git, `public/`, Docker context, and CI artifacts. Only minimized manifest metadata and aggregates may be committed.

## Evidence and verification

- Record exact source page, owner, scope, update date, format/access behavior, SHA-256, size, schema, row counts, eye-evidence fields, and blockers where available.
- Keep explicit specialty/ophthalmology evidence separate from institution-name matches.
- Distinguish directory rows, immutable source snapshots, candidates, review cases, verified locations, and published facilities.
- Keep `PRODUCTION_SOURCE_COVERAGE=PENDING` and `Production Launch Allowed=NO` unless the existing release criteria are actually met.
