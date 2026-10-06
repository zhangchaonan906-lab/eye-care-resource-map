# National Harvest Round 7 Report

**Status:** READY FOR REVIEW
**Branch:** `national-harvest-round7-candidate-enrichment`
**Round 6 merge:** PR #36 squash-merged; main commit `7b43a939e8785d998c6a6bb7ec9e19faf6c21cd2`
**Search date:** 2026-10-06

## Scope and safeguards

Round 7 prioritized explicit eye-candidate evidence and bounded official-page checks. It covered 15 lower-evidence target provinces and focused enrichment in Shanghai, Wuhan, and Jiangsu (Nanjing, Wuxi, Changshu): 18 regional units and 31 cities checked. Search stopped after the prescribed 10–15 high-relevance official results per city when no stronger public source appeared. This is a targeted discovery pass, not a complete nationwide census.

No applications, government outreach, login or CAPTCHA bypass, access-control bypass, or private API reverse engineering occurred. No new raw files were acquired or committed. Existing local source files remained in the quarantine Harvest Store. All 14 previously acquired file fingerprints were rechecked for size and SHA-256 and passed. Rights remain pending; this work does not approve production use.

Production database writes: **0**. Geocoder calls: **0**. Facilities published: **0**.

## Candidate master and traceability

The local candidate master starts from 160 current-verifiable distinct candidates. All 160 baseline candidates trace to a source file fingerprint and row/field evidence or an official page URL; baseline traceability gaps: **0**. Round 7 adds 28 minimized official-page evidence records and 27 distinct candidates, taking the current master to **187**. One new evidence record corroborates an existing candidate; it is not counted as a new candidate. The final current pool has zero traceability gaps.

The local ledger is `candidate-master-ledger.json` under the user-local Harvest Store, outside Git. It preserves the original institution name, normalized key, source keys and URLs, evidence type, known address/registration ID when available, freshness, and campus/match review state. Candidate identity uses registration ID when available and otherwise region plus exact normalized name. Possible campuses and probable aliases are not automatically merged.

## Round 7 results

| Measure | Result |
|---|---:|
| Regional units checked | 18 |
| Cities checked | 31 |
| Search-ledger lead entries | 19 |
| New official-page evidence records | 28 |
| New distinct candidates | 27 |
| Evidence added to an existing candidate | 1 |
| New raw files / historical files reacquired | 0 / 0 |
| New raw rows | 0 |
| Current distinct candidates | 187 |
| Baseline traceable | 160 / 160 |
| Current traceability gaps | 0 |
| Province-level regions with candidates / cities with candidates | 20 / 25 |

### Evidence types

Counts below are source evidence records and can exceed distinct candidate counts when a candidate has corroborating evidence. The candidate coverage JSON separately counts each candidate once per evidence type; types can overlap.

| Evidence type | Current source evidence records | Distinct current candidates |
|---|---:|---:|
| `OPHTHALMOLOGY_LICENSE_SCOPE_EXPLICIT` | 105 | 105 |
| `EYE_SPECIALTY_HOSPITAL_EXPLICIT` | 49 | 45 |
| `OPHTHALMOLOGY_DEPARTMENT_EXPLICIT` | 22 | 21 |
| `EYE_SPECIALTY_CLINIC_EXPLICIT` | 4 | 4 |
| `OFFICIAL_CLINICAL_SPECIALTY_PROGRAM` | 12 | 12 |

The 11 Hunan program entries retain `OFFICIAL_CLINICAL_SPECIALTY_PROGRAM` semantics; they are not reclassified as license scope or department evidence. Explicit department and hospital evidence likewise remain distinct. Three Shenzhen Guangming clinics remain clinic candidates rather than hospitals.

### Cross-source review

- Exact same-name/region corroboration: **4** candidates (the four Wuxi eye hospitals).
- Probable alias review: **2** cases for Shanghai English/Chinese names. Canonical Chinese candidate names are retained; no merge was performed.
- Ambiguous campus review: **1** Jiangyin case; no merge was performed.
- Conflicts: **0**.

These review cases are recorded in the local master ledger. Wuxi corroboration increases evidence-source count, not distinct candidate count.

## Targeted official-page evidence sources

The local evidence ledger stores a minimized field/value summary, source URL, source date where available, and evidence type for each entry. No source page was treated as a complete regional registry without explicit support.

| Source key | Evidence entries | Official source |
|---|---:|---|
| `round7-changshu-clinics-2024` | 3 | [https://www.changshu.gov.cn/zgcs/c100464/202403/ebfb7fce469845d583fbbf70759c723e.shtml](https://www.changshu.gov.cn/zgcs/c100464/202403/ebfb7fce469845d583fbbf70759c723e.shtml) |
| `round7-jilin-list-2026` | 3 | [https://www.jlrd.gov.cn/jlsjk/202406/P020260104582425421250.pdf](https://www.jlrd.gov.cn/jlsjk/202406/P020260104582425421250.pdf) |
| `round7-fuzhou-health-list-2024` | 2 | [https://www.fuzhou.gov.cn/zgfzzt/swjw/fzwj/wjgg/202412/t20241216_4946324.htm](https://www.fuzhou.gov.cn/zgfzzt/swjw/fzwj/wjgg/202412/t20241216_4946324.htm) |
| `round7-baoji-current-2026` | 1 | [https://wjw.baoji.gov.cn/zzzb/xqdt/202603/t20260319_1255134.html](https://wjw.baoji.gov.cn/zzzb/xqdt/202603/t20260319_1255134.html) |
| `round7-datong-eye-hospital-2026` | 1 | [https://sthjj.dt.gov.cn/dtssthjjz/gsl/202609/54a6ae60dc3f4ffaa6bcd3c54503a6b0.shtml](https://sthjj.dt.gov.cn/dtssthjjz/gsl/202609/54a6ae60dc3f4ffaa6bcd3c54503a6b0.shtml) |
| `round7-fuzhou-name-change-2026` | 1 | [https://ybj.fujian.gov.cn/ztzl/ybzx/ggtz_35213/202607/t20260707_7175069.htm](https://ybj.fujian.gov.cn/ztzl/ybzx/ggtz_35213/202607/t20260707_7175069.htm) |
| `round7-gansu-specialty-2025` | 1 | [https://wsjk.gansu.gov.cn/wsjk/c112818/202601/174265276/files/222ce001f74c44a9a27391124ba255ed.pdf](https://wsjk.gansu.gov.cn/wsjk/c112818/202601/174265276/files/222ce001f74c44a9a27391124ba255ed.pdf) |
| `round7-ganzhou-insurer-list-2026` | 1 | [https://ybj.ganzhou.gov.cn/gzsylbzj/c103161/202603/edfef299c8f2498a838ce2350666a016.shtml](https://ybj.ganzhou.gov.cn/gzsylbzj/c103161/202603/edfef299c8f2498a838ce2350666a016.shtml) |
| `round7-harbin-hospital-list-2026` | 1 | [https://www.hrbzx.gov.cn/2026-01/22/content_2881948.htm](https://www.hrbzx.gov.cn/2026-01/22/content_2881948.htm) |
| `round7-hlj-eye-hospital-2026` | 1 | [https://ybj.hlj.gov.cn/ybj/c105387/202601/c00_31904870.shtml](https://ybj.hlj.gov.cn/ybj/c105387/202601/c00_31904870.shtml) |
| `round7-hohhot-insurer-list-2024` | 1 | [https://ylbzj.nmg.gov.cn/xwzx/dtxx/202410/t20241030_2599413.html](https://ylbzj.nmg.gov.cn/xwzx/dtxx/202410/t20241030_2599413.html) |
| `round7-kunming-medical-query` | 1 | [https://ylbz.yn.gov.cn/index.php?c=page&id=4](https://ylbz.yn.gov.cn/index.php?c=page&id=4) |
| `round7-liuzhou-eye-hospital-list` | 1 | [https://wsjkw.gxzf.gov.cn/ggfw_49562/bmxxcx/t17506002.shtml](https://wsjkw.gxzf.gov.cn/ggfw_49562/bmxxcx/t17506002.shtml) |
| `round7-shanghai-huashan-department` | 1 | [https://www.huashan.org.cn/hsdy/linchuang/1259.html](https://www.huashan.org.cn/hsdy/linchuang/1259.html) |
| `round7-shanxi-eye-hospital-2026` | 1 | [https://wjw.shanxi.gov.cn/tzgg/gsgg/202605/t20260521_10131496.shtml](https://wjw.shanxi.gov.cn/tzgg/gsgg/202605/t20260521_10131496.shtml) |
| `round7-urumqi-eye-ent-2025` | 1 | [https://www.wlmq.gov.cn/wlmqs/c121055/202506/fbb25a36e6b54b9e8eb29def91ff8cb5.shtml](https://www.wlmq.gov.cn/wlmqs/c121055/202506/fbb25a36e6b54b9e8eb29def91ff8cb5.shtml) |
| `round7-wuhan-renmin-department` | 1 | [https://rm.rmhospital.com/c/yltdt/page/8.html](https://rm.rmhospital.com/c/yltdt/page/8.html) |
| `round7-wuhan-tongji-department` | 1 | [https://www.tjh.com.cn/channels/197.html](https://www.tjh.com.cn/channels/197.html) |
| `round7-wuhan-union-department` | 1 | [https://www.whuh.com/ppxk/tszk/yk.htm](https://www.whuh.com/ppxk/tszk/yk.htm) |
| `round7-wuhan-zhongnan-department` | 1 | [https://www.znhospital.cn/yk.html](https://www.znhospital.cn/yk.html) |
| `round7-wuxi-second-department` | 1 | [https://www.wx2h.com/kszj/keshidetail/index/id/24/tid/2.html](https://www.wx2h.com/kszj/keshidetail/index/id/24/tid/2.html) |
| `round7-xian-first-hospital-department` | 1 | [https://www.xa.gov.cn/web_files/xian/file/2025/08/12/202508121659367322613.pdf](https://www.xa.gov.cn/web_files/xian/file/2025/08/12/202508121659367322613.pdf) |
| `round7-yinchuan-list-2026` | 1 | [https://www.yinchuan.gov.cn/xxgk/bmxxgkml/ycsylbzj/xxgkml_38315/bmwj_38322/202602/W020260212617708641178.pdf](https://www.yinchuan.gov.cn/xxgk/bmxxgkml/ycsylbzj/xxgkml_38315/bmwj_38322/202602/W020260212617708641178.pdf) |

The final Shanxi search added the 2026 [Datong official project notice](https://sthjj.dt.gov.cn/dtssthjjz/gsl/202609/54a6ae60dc3f4ffaa6bcd3c54503a6b0.shtml) for 大同朝聚安康眼科医院 and corroborating [2026 Shanxi Health Commission roster](https://wjw.shanxi.gov.cn/zfxxgk/fdzdgknr/gggs/202604/P020260421817527926526.pdf). This is point evidence for the named hospital, not a Datong or Shanxi census.

## Candidate coverage

[`eye-candidate-coverage.json`](../data-sources/nationwide/eye-candidate-coverage.json) provides aggregate candidate counts by province and city. The city rows reflect where the current candidates are located; they do not imply source completeness. Hunan program records with no city attribution are labeled `city_unspecified`.

## Data gaps and limits

- The 15 lower-evidence target provinces are a high-yield search subset, not all 31 mainland province-level units.
- Liaoning, Guizhou, and Qinghai did not yield a current, high-confidence candidate in this pass; historical or low-yield leads remain non-current until reverified.
- Many records are point evidence from hospital pages, notices, or clinical program lists, not complete institution registries.
- Current sources remain rights-pending or bounded in scope; this phase did not resolve long-term storage or production display rights.
- Candidate total 187 remains below the 250 goal. The target is not met; no weaker evidence or fuzzy matching was used to inflate it.
- A candidate's eye evidence does not imply an approved facility record or permission to publish it.

## Files and verification

Tracked deliverables:

- `docs/data-sources/nationwide/eye-candidate-coverage.json` — aggregate-only coverage.
- `docs/data-sources/nationwide/harvest-master-manifest.json` — Round 7 summary and official source URL metadata.
- `docs/operations/national-harvest-round7-report.md` — this report.

Local-only ledgers: `candidate-master-ledger.json`, `round7-search-ledger.json`, `round7-evidence-ledger.json`, `round7-state.json`. They and all raw Harvest Store files remain outside Git.
