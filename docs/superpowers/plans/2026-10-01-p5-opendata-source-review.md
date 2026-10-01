# P5 Open Data Source Review Implementation Plan

> **For agentic workers:** Execute inline in this session. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Qualify official Beijing and Shenzhen open-data sources, add a fail-closed local file adapter and structured source-use metadata, then import and QA only bounded records if official account-authorized files are available.

**Architecture:** Preserve the first-round UNKNOWN records and add independent dataset reviews. Store source rights and attribution requirements as structured catalog metadata; use one local CSV/XLS/XLSX adapter with explicit exact-header mappings and the existing import/hash/idempotency lifecycle. Do not perform network scraping, publish facilities, call a geocoder, or commit real source files.

**Tech Stack:** Python 3.12, csv, openpyxl, xlrd, psycopg/PostgreSQL, pytest, Ruff, mypy, PowerShell database CI runner.

---

### Task 1: Record official source qualification

**Files:**
- Create: `docs/data-sources/pilot/beijing/beijing-open-data-hospitals.md`
- Create: `docs/data-sources/pilot/beijing/beijing-open-data-designated-medical-institutions.md`
- Create: `docs/data-sources/pilot/shenzhen/shenzhen-baoan-hospital-basic-information.md`
- Modify: `docs/data-sources/pilot/README.md`

- [ ] Preserve existing Beijing/Guangdong query-entry UNKNOWN reviews unchanged.
- [ ] Record current official terms, exact dataset metadata, rights, attribution, registration requirements, update limits, and decision for each new source.
- [ ] Record Shenzhen's exact 27-row archived dataset and explain why Dapeng remains unqualified until its official field metadata is visible.
- [ ] Keep Shenzhen raw transfer prohibited and include removal/retention duties on source withdrawal.

### Task 2: Add structured source-use policy

**Files:**
- Create: `db/migrations/007_source_open_data_rights.sql`
- Modify: `db/tests/007_source_open_data_rights.sql`
- Modify: `scripts/test-db.ps1`
- Modify: `scripts/test-db.sh`
- Modify: `scripts/seed-opendata-sources.sql`

- [ ] Add nullable tri-state rights columns for data use, reuse, app display, raw transfer, attribution, platform, provider, dataset page, open condition, and retention restriction without rewriting P1-P5 existing source decisions.
- [ ] Add three independently reviewed source rows with exact permitted fields and `manual_only` access; no credentials or private source data are stored.
- [ ] Preserve the P2 HTTP access gate; local file import is separately authorized only for approved `manual_only` sources.
- [ ] Add SQL assertions for tri-state policy, attribution, and blocked Shenzhen raw transfer.

### Task 3: Implement the reusable official-file adapter

**Files:**
- Create: `services/collector/src/eye_collector/sources/open_data_file.py`
- Modify: `services/collector/src/eye_collector/models.py`
- Modify: `services/collector/src/eye_collector/runner.py`
- Modify: `services/collector/src/eye_collector/policy.py`
- Modify: `services/collector/src/eye_collector/db.py`
- Modify: `services/collector/src/eye_collector/cli.py`
- Modify: `services/collector/pyproject.toml`
- Create: `services/collector/tests/test_open_data_file_adapter.py`
- Modify: `services/collector/tests/test_source_policy.py`
- Modify: `services/collector/tests/test_cli.py`

- [ ] Test CSV, XLS, and XLSX input; exact header mismatch must fail closed, and mapping must be explicit.
- [ ] Map only allowlisted source fields into canonical fields; never infer missing addresses, administrative codes, eye evidence, or coordinates.
- [ ] Use an explicit stable source ID when available and canonical content hash when it is absent.
- [ ] Run source records through the existing import lifecycle with a dataset-page source URL; never fetch a platform page or commit downloaded data.
- [ ] Require explicit CLI source, region, file path, and positive limit; cap one source run at 150 records and never exceed 300 records across this pilot configuration.
- [ ] Keep `manual_only` distinct from automated HTTP adapters and reject any attempt to pass a local-file source through HTTP.

### Task 4: Validate and document limits

**Files:**
- Create: `docs/data-sources/pilot/README.md` updates for source mappings and access operation
- Modify: `services/collector/README.md`
- Create: `docs/operations/pilot-opendata-report.md`

- [ ] Document authenticated official download steps as an operator prerequisite without embedding credentials.
- [ ] Mark ophthalmology unknown unless an approved source supplies explicit department evidence.
- [ ] Document required Shenzhen source attribution, raw-data non-transfer, and deletion on platform withdrawal.
- [ ] Record that no import, manual QA, coordinates, or facility publication can be claimed unless an authorized official file is actually available and processed.

### Task 5: Verify and prepare review

**Files:**
- All files above

- [ ] Run unit tests, Ruff, mypy, full `scripts/test-db.ps1`, and `git diff --check`.
- [ ] Inspect the final diff for source data, secrets, coords, map features, or prohibited P6 scope.
- [ ] Import at most 150 Beijing records per selected dataset only if an authenticated official file can be lawfully obtained; across the complete run keep the aggregate at or below 300.
- [ ] If the required registered account/file cannot be accessed without user identity or a registration action, leave imports at zero and report `P5 STATUS: BLOCKED` with exact evidence.
