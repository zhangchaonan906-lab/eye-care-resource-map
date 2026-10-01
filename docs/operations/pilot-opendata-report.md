# P5 Official Open-Data Pilot Status

**Status: FILES READY FOR REVIEW — both official exports passed read-only `inspect-file`; no real records have been imported.**

## Current readiness

- Beijing selected dataset: `定点医疗机构信息` (北京市医疗保障局; 4,876 data rows; portal update 2026-08-13).
- Beijing official workbook: `北京市医疗保障局-定点医疗机构信息.xlsx`; SHA-256 `49848ce24856fb28ed542f46c0e5f805c35b19c3fcea0d85d97d0734487fa918`; exact 10-column official schema; first pilot cap 50.
- Shenzhen selected dataset: `宝安区-医院基本信息` (宝安区人民政府; 27 data rows; portal update 2025-04-15).
- Shenzhen official archive: `宝安区-医院基本信息20261001071251275982.zip`; SHA-256 `9b9554a8553676c906b8b364987ca11d929a204a02fdd3503e23be1cf86348d7`; member `宝安区-医院基本信息_2920002800636.xlsx`, SHA-256 `55a06fd088b436506a4c5692424a07e487159300ad6f191fce046bdbcdd1a129`; data sheet `数据集1`; exact 17-column schema.
- Both CLI inspections returned `schema_match=true` and `ready_to_import=true` against the approved source catalog and remaining pilot capacity.
- Shenzhen read-only adapter scan retained all 27 rows, including 2 `-` placeholder names; it found 5 repeated source keys across 11 rows (6 excess repeated-key rows), 14 excess repeated-name rows, and 5 rows with explicit `眼科` evidence.
- Beijing real source records imported: 0. Shenzhen real source records imported: 0. Candidate records from real records: 0. Manual QA: not performed.
- Coordinates: deferred; no real geocoder calls and no production coordinates stored. Facilities published: no. P6 not started.
- These files remain in Downloads, unchanged and outside Git.

## File handling and next action

The collector supports read-only `inspect-file` for the Beijing XLSX and Shenzhen's approved single-XLSX ZIP. The inspection reads original bytes, reports raw-file SHA-256 and size, validates the configured workbook sheet and exact header schema, and checks approval and pilot capacity in a read-only database transaction. It does not create an import run, snapshot, or candidate.

Do not import data in this compatibility change. After this PR is merged and a separate import is authorized, rerun `inspect-file`, perform and review the bounded dry-run, then import only the approved pilot batch. Beijing starts at 50 rows and may expand to 150 after review. Shenzhen has 27 actual rows; do not pad the sample. Review every Shenzhen record. Run P3 ETL and the QA checklist only after an authorized import. Placeholder names are retained as source snapshots and terminally skipped by P3. Exact duplicate snapshots remain idempotent; changed snapshots with a repeated source key remain separate and are routed to duplicate review. Eye evidence is recorded only for the explicit `眼科|ophthalmolog` match; other rows remain unknown.

Required QA fields: hospital name, address, district, source category, registration/reference ID, source URL, raw field mapping, duplicate status, and ophthalmology evidence status. Inspect at least 50 Beijing records and all Shenzhen records. Record the file SHA-256 and import run in the QA report.

## Rights and attribution controls

- The three platform datasets have separate approved `source_catalog` rows and structured terms metadata.
- Beijing permits free use and sharing with “北京市公共数据开放平台” attribution; application filing is still required before release.
- Shenzhen permits registered-user use/reuse and app development with “深圳市政府数据开放平台” attribution. `raw_data_transfer_allowed=false` and `raw_data_redistribution_allowed=false` are enforced for Shenzhen source rows.
- Shenzhen withdrawal requires suspending the source and erasing raw snapshots and derived staging records. The purge leaves a content-free audit event. It stops for manual review if source rows support published facility records.
- The app does not yet exist, so visible attribution has not been implemented in a frontend. The catalog and docs preserve the required source metadata for a later UI.

## Scope controls

No nationwide crawl, no full import of Beijing's 15,191-row `医院` dataset, no Guangdong-wide coverage claim, no geocoder calls, no production coordinates, no map UI, no Nearby API, no automatic facility publication, and no P6 work.
