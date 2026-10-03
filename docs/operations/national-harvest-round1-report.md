# National Data Harvest Round 1 — Report

**Status: PARTIAL — no new persistent imports; national coverage not established**

**As of:** 2026-10-03 (Asia/Shanghai)

**Base:** `main` after PR #26 squash merge `4d1737d14214b583a27469365642bfec543917f6`
**Branch:** `national-data-harvest-round1`

## Scope and execution boundary

The pass reviewed the existing P6 national source matrix and its 31 mainland planning units, re-fingerprinted four local official files, performed read-only schema/aggregate checks, refreshed selected official source pages, and recorded unresolved acquisition/rights/runtime blockers. It did not perform nationwide production crawling. The existing P6 matrix is a first-pass discovery document, not proof that all city/county sources have been found.

The local P11 application database is not staging or production. This worktree has no current-schema staging credentials or configured least-privilege collector/ETL runtime. The older local P11 container lacks the current migration/runtime-role setup required for safe imports. Therefore this pass created no import run, `source_records`, candidate, duplicate case, location, facility, or publication. Historical P5 pilot rows were not moved or modified.

No login, CAPTCHA, application, payment, access-control bypass, hidden/private API, unauthorized scraping, geocoder, direct published-facility SQL, or automatic facility publication was used. Download of the Dazhou XLS was not completed: computer-use browser initialization failed before a download click; the page was inspected normally via public web content and the page's public XLS preview only. The prior Dazhou registration-info `ERR_INVALID_REDIRECT` remains a file-acquisition blocker and is not source rejection/unavailability.

## National funnel

| Stage | Round-one result | Interpretation |
|---|---:|---|
| Mainland province planning units | 31 | All have terminal first-pass state in `harvest-state.json`; this is not full coverage. |
| Tracked distinct P5/P6 source leads | 19 | Includes separately tracked Tianjin municipal and Xiqing leads, both Dazhou datasets, both Guangzhou plan datasets, the separate Guangzhou attachment, city/district leads, and the two previously approved bounded P5 sources. |
| Original official files re-fingerprinted/schema inspected | 4 | Beijing, Shenzhen Bao'an, Tianjin municipal, Guangzhou TCM-issued subset. Dazhou preview is a page view, not a downloaded file. |
| Raw rows across those files | 4,946 | 4,876 + 27 + 36 + 7 source rows. Counts are not cross-source deduplicated. |
| In-memory P3 parsed / skipped | 4,944 / 2 | Shenzhen's two placeholder-name rows were skipped; there were no persistent P3 candidate writes. |
| Distinct normalized name groups in local inspections | 4,931 | Within-source exact normalized names only; not facility/entity counts. |
| Explicit ophthalmology-evidence rows | 16 | 5 Shenzhen preview rows, 4 Tianjin rows, and 7 Guangzhou rows; Beijing has no specialty field. Only explicit source fields/text were used. |
| Source-local exact-name groups with explicit eye evidence | 13 | Two Shenzhen groups, four Tianjin groups and seven Guangzhou groups; no cross-source entity matching. |
| Newly created immutable snapshots / candidates / duplicate cases | 0 / 0 / 0 | No new DB write in this round. |
| Historical isolated P5 state | 74 snapshots / 72 candidates / 8 duplicate cases | Separate 2026-10-01 pilot; unchanged and not part of current P11 application DB. |
| Verified-coordinate candidates / publication-eligible facilities | 0 / 0 in the current app DB | No geocoder or publication workflow was run. |

## Four file records

Detailed SHA-256, byte sizes, exact headers, workbook sheets, acquisition metadata and minimized QA aggregates are in [`harvest-manifest.md`](../data-sources/nationwide/harvest-manifest.md). Originals remain outside the repository. No local absolute paths or personal-name values are committed.

- **Beijing:** 4,876 rows, 10 columns, zero empty names/addresses, no duplicate registration-key or exact normalized-name groups in the file, no explicit ophthalmology field. A historical P5 import used only 50 rows; this harvest made no new import.
- **Shenzhen Bao'an:** 27 rows, 17 columns, 2 rows without a usable name, 25 parsed in a read-only preview, 5 explicit eye-evidence rows across two normalized-name groups. The prior pilot had 22 candidates and 8 duplicate review cases; this pass did not transfer or re-import them.
- **Tianjin municipal registration:** 36 rows, 7 columns, 4 explicit eye-evidence rows. SHA matches P6-TJ1. Keep coverage `municipality_source_scope_unknown`; this is not verified full Tianjin coverage and its source remains `UNKNOWN`.
- **Guangzhou TCM-bureau-issued attachment:** 7 rows, 14 columns, 7 explicit evidence rows in `诊疗科目名称`. It is a licensing-authority subset and not all Guangzhou. Raw columns include `法人姓名` and `负责人姓名`; neither was mapped or persisted.

## Province checkpoints

`harvest-progress.md` carries the 31 region-by-region checkpoint rows and concrete next actions. Current terminal-state counts are **7 `COMPLETE_FIRST_PASS`, 22 `PARTIAL`, and 2 `BLOCKED`**. “Complete first pass” means the already documented P6 discovery record was reviewed; it does not mean a region has complete hospital data. City/district/issuer-specific subsets remain explicitly scoped.

The main blockers are application-required Zhejiang access, unavailable Hebei source portal, no current-schema least-privilege DB runtime, unresolved rights/scope for UNKNOWN sources, and missing/old attachments or unverified ordinary download behavior for several official leads. The Guangzhou and Shenzhen/Tianjin records do not establish province-wide coverage.

## Top 20 data and operational gaps (ranked by impact)

Ranking method: first the gaps that block safe persistence/publication, then those that most constrain geographic coverage or explicit eye-evidence quality. This is an operational ordering, not a subjective source-quality score.

1. No isolated current-schema staging database/runtime credentials for safe collector + ETL execution.
2. No source-complete coverage evidence for any nationwide register; current candidate sources are bounded or non-exhaustive.
3. `UNKNOWN` source rights remain unresolved for long-term storage, app display, commercial use, and withdrawal handling.
4. Most of the 31 units have no verified downloadable health-authority register with exact current schema.
5. Zhejiang's best province-level candidate is application-required and not approved.
6. Hebei's identified catalog route was unavailable; exact source detail/terms unknown.
7. Dazhou's 4,018-record source has an official callback redirect acquisition error; do not repair/guess or call the full-data API without authorization.
8. Dazhou's 81-record license dataset has a 2023 file date despite 2026 catalog metadata; the XLS file download is still unverified.
9. Tianjin municipal file coverage is `municipality_source_scope_unknown`; the 36-row sample cannot stand for Tianjin.
10. Tianjin tertiary-hospital attachment was not acquired; Xiqing has only a 2023 plan lead.
11. Guangzhou's 7-row inspected attachment covers only Guangdong TCM-bureau-issued institutions in Guangzhou.
12. Guangzhou's two plan-listed registration datasets have not been tied to current downloadable detail pages/files.
13. Shenzhen Bao'an approval is district-only and carries delete-on-withdrawal and no raw transfer/redistribution.
14. Beijing's approved designated-provider list is an insurance subset, lacks specialty evidence, and only 50 rows were in the P5 pilot.
15. Historical P5 pilot data lives in a separate local DB, not the current P11 app DB; no migration/transfer has been authorized here.
16. Current official Yichang/Yiling lead detail, public-download behavior, and schema were not newly verified in this pass.
17. Panzhihua's `许可内容` semantics and actual file columns remain unverified.
18. Shanghai's medical-institution registration source is a stale historical directory lead.
19. Multiple provinces have only query pages/permit notices/technical documents; these do not establish bulk reuse rights or current full snapshots.
20. Source ownership, update cadence, withdrawal/deletion procedures, attribution operations, and periodic feedback duties need a repeatable per-source review record before a public map release.

## P14 release gate evidence

`PRODUCTION_SOURCE_COVERAGE` remains `PENDING`. Evidence is updated to reference this first-round source and file ledger while stating zero new P11 writes, bounded samples, and missing region-wide coverage. Production launch remains **NO-GO**. No other release gate status was promoted.

## Review and verification

- Existing P5 source files were checked by the project's read-only `inspect_open_data_file`; the Guangzhou and full-file aggregate checks used read-only workbook access and existing pure P3 parse/normalize/evidence functions.
- Source status values were not changed; no source was automatically promoted from `UNKNOWN` to `APPROVED`.
- P1–P14 disposable database checks: **PASS** (migrations 001–015, P1–P13 SQL regression, Collector DB/ETL/geocode DB tests, Web DB tests and P14 backup/restore drill).
- Collector CI unit tests: **225 passed**; Collector DB groups ran in the disposable harness; Ruff and mypy: **PASS**.
- Web unit tests: **71 passed**; lint, typecheck and production build: **PASS**.
- P13 system E2E: **3 passed** (Chromium, real Next.js routes and disposable PostGIS).
- Initial unfiltered `pytest -q` was also run and included a database-only sync-system test without `DATABASE_ADMIN_URL`, resulting in one expected environment-configuration failure. The official CI unit selection passed, and the isolated P13 harness then passed that database/system path.
- `git diff --check`: **PASS** at final review; remote GitHub Actions status is reported separately after PR creation.

## Recommended second pass

1. Provision an isolated current-schema staging database and least-privilege service credentials, separately from P11 and the historical P5 pilot DB.
2. Resolve the exact rights/retention/withdrawal and environment-transfer basis for Beijing and Shenzhen before any movement of historical pilot data.
3. Continue ordinary public attachment inspection for high-value known leads, starting with accessible registration datasets and current files; stop when a portal requires user authentication, approval, CAPTCHA, or non-public access.
4. Ask providers for current, versioned, machine-readable registry snapshots in each region; record coverage, schema, data date, source attribution and withdrawal terms.
5. For each approved file, use the existing source adapter/dry run/import/ETL process with scoped batch limits; do not batch-import P6 leads based solely on metadata.
6. Keep geocoding and publication blocked until provider terms, coordinate QA, source evidence and P11 human review gates are satisfied.
