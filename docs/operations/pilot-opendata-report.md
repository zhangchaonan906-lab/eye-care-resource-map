# P5 Official Open-Data Pilot Status

**Status: WAITING_FOR_FILES — source approval and safe file-readiness framework are ready; the official Beijing and Shenzhen exports are not present in the current environment.**

## Current counts

- Beijing selected dataset: `定点医疗机构信息` (市医保局; 4,877 rows; last portal update 2026-08-13).
- Shenzhen selected dataset: `宝安区-医院基本信息` (宝安区人民政府; 27 archived rows; records cover 2017–2024 and the official description says it is no longer updated).
- Beijing real source records imported: 0.
- Shenzhen real source records imported: 0.
- Candidate records produced from real records: 0.
- Manual QA: not performed for either region because no official file was available.
- Total pilot snapshots: 0 of 300 maximum.
- Coordinates: deferred; no real geocoder calls and no production coordinates stored.
- Facilities published: no.
- File preflight: read-only `inspect-file` is implemented; no official export has been inspected yet.
- Provenance: migration 008 records original filename, raw-byte SHA-256, size, obtained-at, approved dataset page/update date, operator, and acquisition method on each import run.

## Why import is blocked

No official CSV/XLS/XLSX for either selected dataset was present in the project or searched user file locations. Unrelated spreadsheets are not treated as source data. No login, registration, account credential, authentication bypass, web scraping, third-party mirror, or proxy was used. The Beijing platform FAQ requires portal registration to download datasets or call APIs. The Shenzhen agreement assigns free access/reuse rights to successful registered users.

The collector now supports read-only inspection and manual official-file import for the approved datasets. The operator must provide both official exports through an authorized portal account, keep them outside the repository, verify the current dataset page and license, inspect them, and review a dry-run before import. Beijing begins with 50 rows and may expand to 150 after review. Shenzhen imports only the actual file rows (about 27) and all are QA-reviewed; no synthetic rows are added. The database enforces the shared pilot record ceiling.

## Required user action

Provide these original files from their official platforms:

1. Beijing `定点医疗机构信息` official CSV/XLS/XLSX.
2. Shenzhen `宝安区-医院基本信息` official CSV/XLS/XLSX.

Keep the original bytes unchanged and outside the repository. After they arrive, run `inspect-file` → dry-run → import → P3 ETL → QA sample/report. No production data has been imported during this readiness work.

## Rights/attribution controls

- The three platform datasets have separate approved `source_catalog` rows and structured terms metadata.
- Beijing permits free use and sharing with “北京市公共数据开放平台” attribution; application filing is still required before release.
- Shenzhen permits registered-user use/reuse and app development with “深圳市政府数据开放平台” attribution. `raw_data_transfer_allowed=false` and `raw_data_redistribution_allowed=false` are enforced for Shenzhen source rows.
- Shenzhen withdrawal requires suspending the source and erasing raw snapshots and derived staging records. The purge leaves a content-free audit event. It stops for manual review if source rows support published facility records.
- The app does not yet exist, so visible attribution has not been implemented in a frontend. The catalog and docs preserve the required source metadata for a later UI.

## Out of scope and prohibitions preserved

No nationwide crawl, no full import of Beijing's 15,191-row “医院” dataset, no Guangdong-wide coverage claim, no geocoder calls, no production coordinates, no map UI, no Nearby API, no automatic facility publication, and no P6 work.
