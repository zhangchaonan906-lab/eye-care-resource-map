# National Harvest Round 4 Report

**Search date:** 2026-10-05 · **Branch:** `national-harvest-round4` · **Round 3 PR:** #28

**Round 3 merge commit / current main baseline:** `daef5652aec673fffa28fb0001a6b06a76435518`

Round 4 prioritized current official sources that expose explicit ophthalmology evidence. Acquired files remain in the operator's local quarantine store; this report does not grant reuse rights or approve production import. Every newly acquired source remains `source_status=UNKNOWN`.

## Results

| Measure | Round 4 | Rounds 2–4 gross / known |
|---|---:|---:|
| Priority regions re-searched | 11 | 11 in this round |
| Recorded official lead entries | 27 | — |
| Newly acquired datasets | 8 | 26 gross datasets |
| Source rows | 4,822 | 19,556 gross source rows |
| Datasets with explicit specialty field | 3 | At least 5 known (2 in Round 3 + 3 in Round 4); Round 2 file-level classification unavailable |
| Explicit eye-evidence rows | 105 | 203 bulk rows in Rounds 3–4, plus 1 dated historical page item from Round 3 |
| Distinct normalized eye names | 105 | Cross-round distinct count unavailable |
| Fresh / stale eye-evidence rows | 105 / 0 | The Round 3 historical page item is dated; cumulative fresh/stale split cannot be fully reconstructed |
| Base-only rows | 4,530 | Round 2/3 split unavailable |
| Stale source rows | 1 (Jiangyin 2025 event) | 6,482 based on Round 3's recorded 6,481 plus this row |
| Cross-source probable matches | 1 | Round 2/3 row-level matching unavailable |
| Ambiguous campus cases | 1 | Jiangyin/Wuxi match lacks Jiangyin address detail |

Gross rows count source rows, not unique institutions. The Rounds 2–3 quarantine files and row-level ledgers are absent from the current workspace, so cumulative entity counts, base-only rows, and cross-round duplicate counts cannot be recomputed. No names or IDs from those missing ledgers have been reconstructed.

## Acquired datasets

| Region | Dataset | Format / rows | Exact specialty field | Explicit eye rows | Coverage / qualification |
|---|---|---:|---|---:|---|
| Guangdong | Guangzhou municipal health commission issued-license file, data through 2026-07-13 | XLSX / 243 | `诊疗科目名称` | 72 | Issuer subset; not a complete Guangzhou census. [Official detail](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908026.html) |
| Guangdong | Guangdong health commission issued-license file in Guangzhou, data through 2026-07-13 | XLSX / 42 | `诊疗科目名称` | 26 | Issuer subset. [Official detail](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908048.html) |
| Guangdong | Guangdong TCM bureau issued-license file in Guangzhou, data through 2026-07-13 | XLSX / 7 | `诊疗科目名称` | 7 | Issuer subset. [Official detail](https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908066.html) |
| Jiangsu | Wuxi medical institutions, data through 2026-07-01 | XLSX / 3,817 | None | 0 | Name, address, category, level and registration identifier are present. Completeness is not asserted. [Official detail](https://wjw.wuxi.gov.cn/doc/2026/07/09/4802972.shtml) |
| Jiangsu | Changshu public medical institutions | XLSX / 226 | None | 0 | Changshu only; not all Suzhou. [Official page](https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml) |
| Jiangsu | Changshu private medical institutions | XLSX / 363 | None | 0 | Changshu only; not all Suzhou. Same official page as above. |
| Jiangsu | Jiangyin Q2 2025 registration events | XLSX / 1 | None | 0 | One event record, not an institution registry. [Official page](https://www.jiangyin.gov.cn/doc/2025/07/25/1343463.shtml) |
| Jiangsu | Nanjing secondary-and-above institutions | HTML / 123 | None | 0 | Excludes military hospitals; the page does not claim a complete all-facility census. [Official page](https://wjw.nanjing.gov.cn/njswshjhsywyh/202605/t20260514_5839731.html) |

The three Guangzhou workbooks are macro-free and contain no external workbook links. Each has exact `机构名称`, `机构地址`, `登记号`, and `诊疗科目名称` columns. They had no empty names or addresses and no within-file duplicate names or registration IDs. The listed `法人姓名` and `负责人姓名` columns were not copied into reports or evidence ledgers; the source workbooks remain quarantined outside Git.

Wuxi has 3,817 rows, one empty address, one duplicate-name group, and 60 duplicate registration-ID groups; 1,475 rows lack a registration ID. These are source QA counts, not entity-resolution outcomes. The workbook also contains personal-name columns; no values from them were copied into reports or ledgers.

The Changshu files have exact fields `机构名称`, `登记号`, `机构地址`, and `机构类别`; neither includes diagnostic subjects. The Jiangyin workbook contains `单位名称` and `统一社会信用代码`, but no address or specialty field.

## Evidence and cross-source review

The evidence ledger records 105 rows where the Guangzhou `诊疗科目名称` field explicitly contains `眼科`, covering 105 distinct normalized institution names within Round 4. All three source files report data through 2026-07-13, which is fresh under the 2025-10-03 cutoff. A name containing “眼科” outside the diagnostic-subject field was not used as evidence.

One Jiangyin row exactly matches a Wuxi row by normalized name and registration identifier. Jiangyin does not provide an address, so campus identity remains unresolved. This is one manual review candidate; no entity was merged. Wuxi's duplicate IDs and duplicate-name group remain source-level QA flags and were not automatically resolved.

Round 3 recorded 98 bulk eye-evidence rows from two Guangzhou XLSX files and one historical Nanjing licensing-page item. Counting only row-level bulk evidence gives 203 known records for Rounds 3–4. Counting the separate historical page item gives 204 recorded evidence items, but there is no cross-round entity deduplication result.

## Search coverage and blockers

Focused official-source searches covered the 11 Round 4 priority regions: Guangdong, Jiangsu, Shandong, Henan, Zhejiang, Hubei, Sichuan, Hebei, Anhui, Shanghai, and Hainan. Target cities included Guangzhou, Shenzhen, Foshan, Dongguan, Zhuhai, Huizhou, Zhongshan; Suzhou, Changzhou, Nantong, Xuzhou, Yangzhou; Jinan, Qingdao, Yantai, Weifang, Linyi; Zhengzhou, Luoyang, Nanyang, Xinxiang; Hangzhou, Ningbo, Shaoxing, Jiaxing; Wuhan, Yichang, Xiangyang; Chengdu, Mianyang, Deyang, Dazhou, Panzhihua; Shijiazhuang, Tangshan, Baoding; Hefei, Wuhu, Fuyang; Shanghai; and Haikou. The city list describes focused search targets, not a claim that every municipal portal or every city dataset was exhaustively enumerated.

| Region / lead | Finding and disposition |
|---|---|
| Guangdong | Acquired three current Guangzhou issuer-specific files with diagnostic-subject fields. Shenzhen's official issuer list exposed 15 entries without specialty fields; Dongguan had a public-list lead but no verified bulk download. Futian page timed out. Haizhu/Tianhe open-data-plan entries remain unverified as current files. |
| Jiangsu | Acquired Wuxi, Changshu public/private, Jiangyin event, and Nanjing sources. Changshu and Nanjing are limited-scope sources; Jiangyin is one event. No other target-city bulk specialty file was verified in this pass. |
| Shandong | Qingdao West Coast approval notices are event notices, Jinan's lead is an older application/review catalog, and the provincial registration query is CAPTCHA gated. No bulk file acquired. |
| Henan | Focused official searches found permit guidance, not a public institutional directory or bulk file. |
| Zhejiang | A provincial secondary-and-above institution dataset requires a use application. Wenzhou Yueqing's district dataset requires login; no access control was bypassed. Wenzhou is not treated as a province-wide blocker. |
| Hubei | The provincial query API detail requires login. Yichang Yiling's 300-row dataset download led to platform license terms; the flow was stopped before accepting them. |
| Sichuan | Panzhihua's 70-row open catalog declares unnecessary legal-representative certificate-number fields and was excluded under data minimization. Dazhou's distinct 64,978-row basic dataset was visible in the official catalog, but the ordinary browser connection closed; no retry, endpoint guessing, or bypass was attempted. This is a file-acquisition blocker, not a dataset rejection. |
| Hebei | Shijiazhuang individual permit announcements include diagnostic-subject text, but no bulk directory was found in the focused pass. |
| Anhui | Focused official searches found permit materials and specialty-specific lists, not a general directory or bulk file. |
| Shanghai | Current catalog page returned HTTP 412; no bypass was attempted. A 2025 open-data plan lead is not yet a verified current file; an older plan is stale. |
| Hainan | No newer public bulk roster was verified. The 2022 roster remains stale-only. A 2026 single-institution approval page is not a bulk roster; its current page returned HTTP 403 during direct access. |

The 27 lead-entry count is defined in the external search ledger as 19 nonempty initial lead strings plus 8 verified acquired dataset entries. It is a count of recorded lead entries, not unique providers or independent portals.

## Cumulative acquisition funnel

| Funnel measure | Recorded result | Limitation |
|---|---:|---|
| Official datasets | 26 gross | 18 Rounds 2–3 plus 8 Round 4; source overlap remains possible |
| Source rows | 19,556 gross | Not distinct institutions |
| Specialty-capable datasets | At least 5 known | Two in Round 3 and three in Round 4; Round 2 source-level file inventory unavailable |
| Explicit eye evidence | 203 bulk rows + 1 historical page item | Round 2 eye evidence not reconstructable from missing row-level files |
| Distinct explicit eye entities | 105 in Round 4 only | Cumulative cross-round exact-name/ID dedup unavailable |
| Base-only records | 4,530 in Round 4 | Round 2–3 source-level specialty split unavailable |
| Stale rows | 6,482 known | Round 3 reported 6,481; Round 4 adds the single 2025 Jiangyin event row under the 2025-10-03 cutoff |
| Cross-source duplicate candidates | 1 in Round 4 | Exact name + registration-ID match; older-round rows unavailable |
| Geographic coverage | 11 Round 4 priority regions searched | Acquisitions do not imply full regional coverage; scopes remain source-specific |

## Safety and status

- Raw source files: local quarantine only; none committed to Git.
- New source statuses: `UNKNOWN`; production import not approved.
- Production database writes: 0.
- Geocoder calls: 0.
- Facilities published: 0.
- Automatic facility merge: none.
- Login, CAPTCHA, application, platform-term consent, and portal errors were not bypassed.

## Verification

This change adds documentation only; no production code or database files changed. Local checks completed: collector unit tests (230 passed), Ruff, mypy, Web unit tests (71 passed), ESLint, TypeScript typecheck, Next.js production build, and `git diff --check`. The database test script and P13 system E2E could not run locally because Docker Desktop's Linux engine was unavailable. PR CI must pass the collector, P13 E2E, accessibility, system E2E, and release-check jobs before the change is reported ready.

## Recommended next step

Round 5 should target the remaining high-value specialty-field and geographic coverage gaps. Then perform centralized rights triage before any controlled import. The missing Round 2/3 row-level files should be restored if cumulative entity dedup is required.
