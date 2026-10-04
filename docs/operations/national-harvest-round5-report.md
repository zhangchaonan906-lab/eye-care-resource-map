# National Harvest Round 5 Report

Search date: 2026-10-05

Branch: `national-harvest-round5`

Round 4 PR #30 merge commit: `832c014275270f2f85c233819c896e91ba97e899`

## Result

Round 5 completed the final bounded official-source pass for the ten first-priority regions and ten second-priority regions. The search ledger also retains the Tianjin reference pattern. The pass recorded 21 region entries, 58 target-city entries, 57 official domains, and 25 lead entries. These counts describe recorded searches and leads, not unique datasets.

One new public source was acquired: the Wuhan Municipal Health Commission's “武汉地区二、三级医疗机构名单” HTML page. Its table contains 185 institutions and eight fields. Thirteen rows have the exact category `眼科医院`, which supports `EYE_SPECIALTY_HOSPITAL` evidence. It does not prove that those institutions expose an ophthalmology department, and it is not a complete Wuhan institution census. [Official Wuhan list](https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml)

No other Round 5 bulk file was acquired. Yichang's download required accepting platform terms; the attempt stopped before acceptance. Panzhihua's catalog included legal-representative certificate numbers that were unnecessary for this project, so no file was acquired. The Dazhou public page timed out once and was not retried. No hidden APIs, login, CAPTCHA, or access restrictions were bypassed.

## Cumulative counts

| Measure | Result | Notes |
| --- | ---: | --- |
| Round 2–3 historical datasets | 18 | Files and row-level ledgers are unavailable locally. |
| Round 4 acquired datasets | 8 | All eight original files remain available and were rehashed. |
| Round 5 acquired datasets | 1 | Wuhan public HTML. |
| Cumulative datasets | 27 | 18 historical-only + 9 locally verifiable. |
| Historical raw source rows | 14,734 | Round 2–3 aggregate only. |
| Round 4 raw rows | 4,822 | Rechecked against inspection records. |
| Round 5 raw rows | 185 | Parsed from the Wuhan HTML table. |
| Cumulative gross raw rows | 19,741 | Source rows are not unique facilities. |
| Specialty-capable current datasets | 3 | All have the explicit `诊疗科目名称` field in the three Guangzhou files. |
| Eye-evidence records in current files | 132 | 105 diagnostic-subject rows + 27 explicit eye-hospital category rows. |
| Distinct current eye candidates | 132 | NFKC name normalization and region code; not deduplicated across unavailable R2/R3 files. |
| Historical eye evidence | 99 | Round 3 bulk evidence 98 + one historical official-page record. |
| Cumulative known eye-evidence records | 231 | Evidence records, not a count of unique hospitals. |

Known specialty-capable sources from Round 3 raise the historical cumulative count to at least five. The 18 Round 2–3 datasets cannot be fully reclassified because their individual files and ledgers are missing.

## Durable Harvest Store

Local store: `%LOCALAPPDATA%\EyeCareResourceMap\HarvestStore\`.

- The eight Round 4 originals were copied from the old Round 4 quarantine, not moved. Their source SHA-256 and byte size matched the original provenance before copying and matched again after copying.
- The Wuhan HTML was saved directly into the durable store. Its SHA-256 and byte size are in the local and Git metadata manifests.
- Each acquired dataset has `original/`, `metadata.json`, `inspection.json`, and `sha256.txt` under a versioned source directory.
- The local master manifest contains nine acquired files and one aggregate historical record for Round 2–3.
- The Git mirror at [`harvest-master-manifest.json`](../data-sources/nationwide/harvest-master-manifest.json) contains metadata only. It excludes raw rows, individual personal data, and local absolute paths.
- The local evidence ledger records 105 `OPHTHALMOLOGY_DEPARTMENT` entries and 27 `EYE_SPECIALTY_HOSPITAL` entries. Address values are omitted while rights remain pending.
- Store verification checks all nine acquired files. It returns `PARTIAL` solely because the 18 historical Round 2–3 datasets have no local originals or verifiable hashes.

All nine acquired sources remain `UNKNOWN` / `ACQUIRED_RIGHTS_PENDING`; none is approved for production import. No database, geocoder, or publication action occurred.

## High-value sources and coverage

### Acquired and specialty-capable

1. Guangzhou municipal health-license list, data through 2026-07-13: 243 rows, `诊疗科目名称`, 72 eye-evidence rows. [Official page](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908026.html)
2. Guangzhou institutions licensed by Guangdong Health Commission, data through 2026-07-13: 42 rows, `诊疗科目名称`, 26 eye-evidence rows. [Official page](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908048.html)
3. Guangzhou institutions licensed by Guangdong TCM Bureau, data through 2026-07-13: 7 rows, `诊疗科目名称`, 7 eye-evidence rows. [Official page](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908066.html)
4. Wuhan secondary-and-tertiary medical-institution list: 185 rows; 13 exact `眼科医院` categories. The scope excludes any claim of full-city completeness. [Official page](https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml)

### Other locally retained Round 4 sources

5. Wuxi medical-institution list: 3,817 rows; basic name/address/category data, no diagnostic-subject field. [Official page](https://wjw.wuxi.gov.cn/doc/2026/07/09/4802972.shtml)
6. Changshu public medical-institution list: 226 rows. [Official page](https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml)
7. Changshu private medical-institution list: 363 rows. [Same official page](https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml)
8. Nanjing secondary-and-above institution list: 123 HTML rows; seven exact eye-hospital categories. [Official page](https://wjw.nanjing.gov.cn/njswshjhsywyh/202605/t20260514_5839731.html)
9. Jiangyin Q2 2025 registration events: one row; this is an event notice, not an institution registry. [Official page](https://www.jiangyin.gov.cn/doc/2025/07/25/1343463.shtml)

### New leads not acquired

- Zhongshan's official open-data catalog lists a 1,908-row medical-institution license basic dataset with XLS/JSON/CSV formats, but no diagnostic-subject field was confirmed. [Official catalog](https://zsdata.zs.gov.cn/web/dataServerView?id=4028844958658659015865ea7bf400c0)
- Changzhou's official catalog describes five files for WJW-issued medical institutions. The downloadable state was not independently confirmed, so no file was acquired. [Official catalog](https://www.changzhou.gov.cn/opendata/open/index/datadetail/1813-city)
- Guangzhou's WJW search UI has an ophthalmology filter, but no bulk export was confirmed in this pass. [Official search page](https://wjw.gz.gov.cn/fwcx/yycx/index_17.html)
- Haizhu and Guangzhou Tianhe open-data plans mention diagnostic-subject datasets, but current downloadable files were not confirmed.
- Hubei periodic permit notices can contain diagnostic scopes, but they are incremental notices rather than a stable full registry. [Hubei WJW notice](https://wjw.hubei.gov.cn/bsfw/spgs/202605/t20260513_5935718.shtml)
- Tianjin's previously inspected 36-row registration file remains scoped as `municipality_source_scope_unknown`; it is not represented as a complete Tianjin directory. [Official dataset page](https://open.data.tj.gov.cn/sjj/8e3f7e670ea9492dbc480e2c68683ce5.htm)

## Cross-source review

The review used exact normalized name + region and exact registration ID when available. No fuzzy matching, duplicate scoring, or automatic merge was used.

- Exact cross-source matches ready to resolve: 0.
- Probable matches: 0.
- Ambiguous campus cases: 1, Wuxi/ Jiangyin `江阴敔山湖护理院`. Name and registration identifier match exactly, but the Jiangyin event source has no address; retain for manual review.
- Round 5 Wuhan has no overlapping Round 4 region/source for comparison.

## Search gaps and blockers

High-priority first pass: Shandong, Henan, Hebei, Anhui, Hubei, Sichuan, Zhejiang, Shanghai, Guangdong, Jiangsu.

Second-priority final pass: Heilongjiang, Liaoning, Jilin, Shanxi, Guangxi, Chongqing, Guizhou, Yunnan, Shaanxi, Xinjiang.

The recorded region and city/domain searches are in the local `ledgers/search-ledger.json`. No official bulk specialty file was verified for several regions; in others, only basic lists, query pages, individual permit notices, stale plans, or application-based catalog entries were found.

Recorded access blockers include CAPTCHA-gated Shandong registration lookup, login/application-gated Zhejiang and Hubei API details, Yichang download terms, an HTTP 412 Shanghai portal response, one Dazhou connection timeout, and one Guangxi official-page internal error. These access conditions were not bypassed. Panzhihua's certificate-number fields were excluded under data minimization.

## Safety and next step

- Raw data committed to Git: **NO**.
- Production database writes: **0**.
- Geocoder calls: **0**.
- Facilities published: **0**.
- Source approval changes: **0**.

Stop broad national harvesting. Begin centralized rights triage and controlled import planning for the current high-value files, starting with the three Guangzhou license datasets and the Wuhan city-only list. Keep all records unpublished until rights and scope are reviewed.
