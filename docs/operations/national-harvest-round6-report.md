# National Data Harvest Round 6 — Eye-First Targeted Harvest

**Status:** COMPLETE for the targeted high-yield search pass. This is not a 31-region exhaustive census. The 300+ candidate objective was aspirational; this pass reached 160 current distinct explicit eye candidates.

## Scope and controls

Searches used ordinary public pages and direct official attachments. No account, application, CAPTCHA, access-control workaround, or private API was used. Publicly accessible acquisitions remain `PUBLIC_ACQUIRED_RIGHTS_PENDING` and quarantined outside Git. No source was auto-approved.

- Production database writes/imports: 0
- Geocoder calls: 0
- Facilities published: 0
- Source auto-approvals: 0
- Raw files committed to Git: NO
- Historical Round 2/3 datasets reacquired: 0; the local history has an 18-dataset aggregate but no individual URLs/originals to verify.

## Round 6 results

| Measure | Result |
|---|---:|
| Regions searched | 14 |
| Cities searched | 22 |
| Official lead entries recorded | 21 |
| New files acquired and inspected | 5 |
| Rows acquired this round | 1,107 |
| Cumulative verifiable rows | 6,114 |
| New explicit eye evidence records | 33 (32 current, 1 historical) |
| New current distinct candidates | 28 |
| Current distinct explicit eye candidates | 160 (baseline 132 + 28) |
| Exact cross-source matches | 4 |
| Probable cross-source matches | 2 |
| Ambiguous campus cases | 0 |
| Login/CAPTCHA/access blockers observed | 0 |
| Application required | 0 |

Row totals are source rows/snapshots, not unique facilities. The 14,734-row Round 2/3 historical aggregate is excluded from verifiable totals.

### Evidence-type counts in Round 6

- `EYE_SPECIALTY_HOSPITAL_EXPLICIT`: 5 current evidence records
- `OPHTHALMOLOGY_LICENSE_SCOPE_EXPLICIT`: 1 historical record (Nanjing 2023; not counted as current)
- `OPHTHALMOLOGY_DEPARTMENT_EXPLICIT`: 12 current records
- `EYE_SPECIALTY_CLINIC_EXPLICIT`: 4 current records
- `OPHTHALMOLOGY_SPECIALTY_PROGRAM_EXPLICIT`: 11 current records from a provincial specialty-program result; this is not license-scope evidence

Twelve city labels are represented in Round 6 eye evidence (Shenzhen, Shanghai, Beijing, Wuhan, Chengdu, Jinan, Suzhou, Wuxi, Changsha, Chenzhou, Shaoyang, and Loudi). Some overlap prior-round locations, so this is not a claim that all twelve are new to the project.

## Acquired sources

| Source | Scope / format | Rows | Exact headers | Eye findings | SHA-256 |
|---|---|---:|---|---:|---|
| [Shanghai Municipal Government — Medical Facilities in Shanghai](https://english.shanghai.gov.cn/en-Individuals-Healthcare-Medicalservices/20260805/5559ba9c9e474362b4237f5073c1331b.html) | Listed public and foreign-funded facilities only; HTML | 49 | blank, `Hospital Name`, `Address` | 2 eye-named rows; eye capability separately verified on official facility pages | `89832edaaeb1c70cbaab54aead914333df4c4b260afba70b33d3ac41cd915ba2` |
| [Guangming District Health Bureau — Medical Institution Information](https://www.szgm.gov.cn/132100/152326/ylfwxxgk/700522/700524/content/post_12882699.html) | Guangming District only; HTML | 391 | `序号`, `机构名称`, `机构地址` | 3 eye-clinic names; no separate specialty field | `50a3f71c1a21ac8be8287f0bcd3fdd82cd605d3645c20c0c1457102a66cb14bc` |
| [Hunan Provincial Health Commission — 2025 Provincial Clinical Key Specialty Results](https://wjw.hunan.gov.cn/wjw/xxgk/tzgg/202509/t20250915_33804776.html) | Specialty-program results, not an active-license registry; PDF, 22 pages | 626 | `序号`, `医疗机构`, `申报专科`, `结果` | 11 rows explicitly list `眼科`; 11 distinct institution names | `09e20560b76e8d63e065d646a3bd014394f1356c2800c902f13b5d1f8375278e` |
| [Guangming District Health Bureau — Weekly Licensing Approvals](https://www.szgm.gov.cn/xxgk/xqgwhxxgkml/gzgg/content/post_12882558.html) | Single-week event; XLS/BIFF | 1 | 9 columns; contact-field name omitted from this tracked report | 0; the single institution row is unrelated to ophthalmology | `7e5141285a91ca3373c776a08d39a01ea26e98a417749e9b74c5cf1436c0570f` |
| [Wuxi Municipal Health Commission — 2026 H1 Institution Validation Results](https://wjw.wuxi.gov.cn/doc/2026/05/13/4774787.shtml) | H1 validation results; HTML | 40 | `序号`, `机构名称`, `校验结论` | 4 eye-hospital names; all four exactly match existing Wuxi candidates | `14f2ef84df1eeb740bb71951a1c6bd81182824e9fbc928a445d883cfdf87ad64` |

All originals, metadata, inspections, and checksum files are in the local Harvest Store outside the repository. The weekly Guangming XLS includes a contact-number column; no contact values were copied to inspection summaries, candidate evidence, or Git. It produced no eye candidates.

### Cross-source review

Four Wuxi eye-hospital names exactly matched the existing July 2026 Wuxi institution source by normalized name and region. Two Shanghai names were classified as probable English/Chinese aliases. These are review-only records; no facilities were merged.

## Search coverage and blockers

| Region | Cities checked | Outcome |
|---|---|---|
| Guangdong | Guangzhou, Shenzhen | Guangzhou July 2026 files were unchanged from existing snapshots. Shenzhen public hospital directory offers district/specialty filters but did not render a complete filtered list in the ordinary static page view; no hidden API was inspected. Acquired the Guangming District directory and weekly approval XLS. |
| Shanghai | Shanghai | Acquired the official HTML directory. Coverage is limited to listed public and foreign-funded facilities. |
| Beijing | Beijing | Verified official ophthalmology departments at Beijing Tongren and Peking Union Medical College Hospital; no current bulk eye roster acquired. |
| Hubei | Wuhan | Verified Tongji Hospital ophthalmology page; periodic license notices are event records, not a current registry. |
| Sichuan | Chengdu | Verified West China Hospital ophthalmology department; no bulk roster acquired. |
| Shandong | Jinan, Qingdao | Verified Jinan eye-hospital source. Qingdao searches yielded stale insurance lists and incidental publications, not a current facility roster. |
| Jiangsu | Nanjing, Suzhou, Wuxi, Changzhou, Nantong, Xuzhou | Acquired the Wuxi H1 validation list. Nanjing specialty notice found was from 2023 and remains historical; no new direct eye roster was confirmed for the other three cities. |
| Zhejiang | Hangzhou, Ningbo | No high-value directly accessible eye-specific roster confirmed in these passes. |
| Hunan | Changsha | Acquired the provincial specialty-program PDF; it is not a complete registry. |
| Fujian | Fuzhou | Found a public proposal-stage eye-hospital notice; it was not counted as a current operating facility or acquired. |
| Heilongjiang | Harbin | No high-value direct eye-specific source confirmed in this pass. |
| Anhui | Hefei | No high-value direct eye-specific source confirmed in this pass. |
| Gansu | Lanzhou | No high-value direct eye-specific source confirmed in this pass. |
| Henan | Zhengzhou | Found a proposed cosmetic-hospital registration notice without ophthalmology scope; no eye-specific source confirmed. |

The source ledger records official domains, search dates, leads, acquisition attempts, and blockers city by city. Searches were targeted, not an exhaustive search of every city in each province.

## Remaining gaps and next step

The strongest new specialty-bearing file is Hunan’s provincial clinical specialty-program result, while Guangming’s district roster adds three eye-named clinics and Wuxi provides current corroboration for four existing candidates. Shanghai’s directory has no specialty column. The pilot rights status remains pending for all five acquisitions.

Continue with only high-yield eye-specific public sources, prioritizing Shenzhen district directories and province/city licensing pages with an explicit `眼科` field. Keep all new sources quarantined until a separate rights review; use the existing exact/probable cross-source queue without auto-merging.
