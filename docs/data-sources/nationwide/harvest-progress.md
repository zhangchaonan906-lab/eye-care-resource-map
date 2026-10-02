# National Harvest Round 1 — Province Checkpoints

As of 2026-10-03. Province status meanings are defined in [`harvest-state.json`](harvest-state.json). `COMPLETE_FIRST_PASS` means the prior P6 official discovery record was reviewed for this pass only; it never means regional coverage is complete. All counts below are this harvest's new persistent writes unless explicitly labeled historical.

## Shared checkpoint metrics

- Existing P6 first-pass matrix covers 31 mainland planning units; it remains discovery evidence, not exhaustive source search.
- 19 distinct source leads are tracked across P5/P6 (including separate Tianjin municipal/Xiqing entries, two Dazhou datasets, Guangzhou plan entries and the independent Guangzhou attachment). A lead is not a source approval.
- Four original official local files were re-fingerprinted and inspected: 4,946 source rows total across distinct bounded datasets; 4,944 parsed by a read-only/in-memory path, 2 Shenzhen name placeholders skipped, and 16 rows contained explicit ophthalmology evidence in specialty/description fields. These are not 4,946 eye hospitals.
- New persistent source snapshots/import runs/candidates/review cases: 0 / 0 / 0 / 0. Existing historical P5 pilot totals remain 74 snapshots, 72 candidates, 8 duplicate review cases; they are in a separate local pilot database and were not changed or counted as round-one writes.
- Geocoder calls: 0. Facility publications: 0. Source status changes: 0.
- The local P11 database is not staging/production and has no current least-privilege collector/ETL runtime configured in this worktree; no production/staging credentials are configured. This blocked safely connecting the harvest CLI to the current P14 schema.
- Verification: P1–P14 disposable DB checks PASS; Collector CI unit tests 225 PASS; Web unit tests 71 PASS; Collector Ruff PASS; Collector mypy PASS; Web lint/typecheck/build PASS; P13 system E2E 3 PASS; `git diff --check` is run at final review.

## Province ledger

| Province unit | Round-one state | Official leads / bounded result | Imported rows / snapshots / candidates | Explicit eye-evidence rows | Blocking gap / next operator action |
|---|---|---|---:|---:|---|
| Beijing | `PARTIAL` | Approved designated-medical-institutions source; full file 4,876 rows, historical P5 sample was 50 | 0 / 0 / 0 new | 0 (source has no specialty field) | Current-schema isolated DB/runtime and transfer review for historical P5 sample; keep 50-row cap. |
| Tianjin | `PARTIAL` | Municipal registration file, 36 rows; separate tertiary dataset and Xiqing plan lead | 0 / 0 / 0 | 4 | Municipal rights and scope unresolved; tertiary file not acquired; Xiqing current detail/file absent. |
| Hebei | `BLOCKED` | Cooperative directory entry for designated medical institutions | 0 / 0 / 0 | 0 | Exact source portal was unavailable in prior P6 check; locate official detail/export. |
| Shanxi | `PARTIAL` | Official query/licensing trail only | 0 / 0 / 0 | 0 | No reuse-authorized bulk file confirmed. |
| Inner Mongolia | `PARTIAL` | Official query and tertiary-hospital list trail | 0 / 0 / 0 | 0 | No full current schema with name/address/specialty confirmed. |
| Liaoning | `PARTIAL` | Official practice-permit query trail | 0 / 0 / 0 | 0 | No authorized bulk file/API confirmed. |
| Jilin | `PARTIAL` | 2023 public hospital list / official query trail | 0 / 0 / 0 | 0 | Stale and scope-limited; locate current catalog. |
| Heilongjiang | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official provincial/municipal catalog search. |
| Shanghai | `PARTIAL` | Historical registration-open-data catalog entry | 0 / 0 / 0 | 0 | Current dataset page and terms not found; stale lead only. |
| Jiangsu | `PARTIAL` | Nanjing city directory and provincial query trails | 0 / 0 / 0 | 0 | City lead cannot imply province-wide coverage; no register file confirmed. |
| Zhejiang | `BLOCKED` | “二级及以上医疗机构基本信息” application-restricted lead | 0 / 0 / 0 | 0 | Application not filed/approved; no data access. |
| Anhui | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Fujian | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Jiangxi | `PARTIAL` | Jiujiang open-directory/standard-field lead | 0 / 0 / 0 | 0 | Exact dataset page/export not confirmed. |
| Shandong | `PARTIAL` | Official medical-institution registration query trail | 0 / 0 / 0 | 0 | No bulk reuse dataset confirmed. |
| Henan | `PARTIAL` | Medical-insurance public-service query trail | 0 / 0 / 0 | 0 | Query page is not bulk collection permission. |
| Hubei | `PARTIAL` | Yichang city/district leads; province health authorization notices | 0 / 0 / 0 | 0 | No files acquired this pass; city/district scope only. |
| Hunan | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Guangdong | `PARTIAL` | Approved Bao'an source (27 rows); independent Guangzhou TCM-issued subset (7 rows); two separate Guangzhou plan leads | 0 / 0 / 0 new | 12 in local file previews (5 Bao'an, 7 Guangzhou) | No full Guangzhou or Guangdong coverage; Guangzhou remains `UNKNOWN`; do not map personal-name fields. |
| Guangxi | `PARTIAL` | Health-commission permit announcement batches | 0 / 0 / 0 | 0 | Not a full institution snapshot; no structured bulk source. |
| Hainan | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Chongqing | `PARTIAL` | Chongqing High-Tech Zone licensing service-guide trail | 0 / 0 / 0 | 0 | Service guide is not a dataset. |
| Sichuan | `PARTIAL` | Two Dazhou datasets plus Panzhihua registration-permit dataset | 0 / 0 / 0 | 0 from local files | Dazhou 4,018-record dataset's prior normal download redirect error remains; 81-record license page and preview rechecked, but browser tool did not allow ordinary file click; no API call. |
| Guizhou | `PARTIAL` | Provincial medical-insurance query trail | 0 / 0 / 0 | 0 | No health register file/reuse terms confirmed. |
| Yunnan | `PARTIAL` | Provincial medical-insurance institution query trail | 0 / 0 / 0 | 0 | No health register file/reuse terms confirmed. |
| Tibet | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Shaanxi | `PARTIAL` | Yangling district registration notice | 0 / 0 / 0 | 0 | Single district notice is not a provincial register. |
| Gansu | `COMPLETE_FIRST_PASS` | No matching bulk source confirmed in existing P6 record | 0 / 0 / 0 | 0 | Second-pass official catalog search. |
| Qinghai | `PARTIAL` | Government-service designated-institution query trail | 0 / 0 / 0 | 0 | Scope and reuse rights unverified. |
| Ningxia | `PARTIAL` | Health data-exchange field/interface specification | 0 / 0 / 0 | 0 | Technical documentation does not grant access. |
| Xinjiang | `PARTIAL` | Limited-category National Health Commission query lead | 0 / 0 / 0 | 0 | Separate Xinjiang/Bingtuan coverage and source discovery required. |

## P6 lead checkpoint notes

- **Dazhou registration info (4,018 displayed records):** retain `BLOCKED_BY_OFFICIAL_REDIRECT_ERROR` from the earlier ordinary download flow. No callback repair, API call, or retry was made here.
- **Dazhou medical-institution license (81 displayed records):** [official detail page](https://www.dazhoudata.cn/oportal/catalog/a9865122f8d742c6934783ca92181728) and its public XLS preview were readable. The page lists ten official fields and XLS/CSV/JSON/XML/RDF attachments dated 2023-11-30; the file itself was not downloaded. The page notes that full data requires API, which this pass did not call. Source remains `UNKNOWN`.
- **Yichang / Yiling:** existing official evidence retained as city/district leads; no source page click/download or file was completed in this harvest. The city hospital dataset has 332 displayed records and no declared specialty field; it cannot produce explicit ophthalmology evidence.
- **Panzhihua:** official city dataset lead remains uninspected at file level; `许可内容` cannot be assumed to be a complete specialty field.
- **Guangzhou:** the 7-row TCM-bureau-issued attachment is an independent licensing-authority subset, not either of the two 2025 plan datasets and not all Guangzhou. All 7 rows have explicit eye evidence in `诊疗科目名称`; that does not imply publication authorization.
- **Tianjin:** current SHA and structure match the previously inspected 36-row municipal file; municipal scope stays unknown. Xiqing remains only a separate district-level 2023 plan lead.
