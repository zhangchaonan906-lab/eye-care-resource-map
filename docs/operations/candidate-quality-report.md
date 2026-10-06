# Candidate Quality Report — National Harvest Round 8

**Snapshot date:** 2026-10-06
**Scope:** locally retained verified candidate pool; source-level lineage is in the local Harvest Store ledger and is not committed.
**Data boundary:** inspection and candidate analysis only. No production database write, coordinate lookup, facility publication, or automatic merge occurred.

## Current pool

| Measure | Result |
|---|---:|
| Round 8 opening baseline | 187 candidates; 187 traceable; 0 gaps |
| Current distinct candidates | 193 |
| New distinct candidates in Round 8 | 6 |
| Name present | 193/193 (100%) |
| Address present | 38/193 (19.7%) |
| City present | 182/193 (94.3%) |
| Trusted coordinates | 0/193 |
| Candidate records with source verification date | 182/193 |
| Candidate records without a freshness date | 11 |
| Freshest evidence date represented | 2026-10-06 |
| Oldest non-empty evidence date | 2023 |
| Traceability gaps | 0 |

Address and city completeness are based on recorded values only; absent values remain null. The Round 8 file-backed exact-name enrichment added 31 address values, 27 institution-category values and 4 registration identifiers. Fourteen local original-file fingerprints were rechecked: 14 PASS, 0 FAIL, 0 missing/ambiguous.

## Evidence types

Counts are candidates carrying each evidence class and may overlap when a candidate has multiple sources.

| Evidence class | Candidates |
|---|---:|
| `EYE_SPECIALTY_CLINIC_EXPLICIT` | 4 |
| `EYE_SPECIALTY_HOSPITAL_EXPLICIT` | 47 |
| `OFFICIAL_CLINICAL_SPECIALTY_PROGRAM` | 12 |
| `OPHTHALMOLOGY_DEPARTMENT_EXPLICIT` | 24 |
| `OPHTHALMOLOGY_LICENSE_SCOPE_EXPLICIT` | 106 |

The 2026 Wuhan health-commission administrative notice explicitly records a diagnostic-scope change adding ophthalmology for 武汉仲景东西湖中医医院; this supplied one new candidate, with the individual official-page fact retained and no personal fields copied. [Official Wuhan notice](https://wjw.wuhan.gov.cn/zwgk_28/fdzdgknr/xkfw/spgg/202609/t20260903_2843036.shtml).

## Region and city coverage

- Regions with at least one candidate: **23/31** (上海、云南、内蒙古、北京、吉林、四川、宁夏、安徽、山东、山西、广东、广西、新疆、江苏、江西、河南、浙江、湖北、湖南、甘肃、福建、陕西、黑龙江). No coverage is inferred from neighboring areas.
- Candidate-bearing cities: **28**.
- Focus cities:

| City | Candidates |
|---|---:|
| 北京市 | 2 |
| 上海市 | 5 |
| 深圳市 | 7 |
| 杭州市 | 1 |
| 成都市 | 2 |
| 武汉市 | 18 |
| 南京市 | 7 |
| 合肥市 | 1 |
| 济南市 | 2 |
| 郑州市 | 1 |


These are candidate counts, not estimates of each city’s complete provider population. For example, Wuhan’s official 2026 secondary/tertiary roster includes facility addresses and categories, but its published scope is limited to the named grades. [Wuhan roster](https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml).

## Source accessibility and freshness

There are **54 unique official source URLs** and **200 candidate-to-source URL links** in the local master ledger. In Round 8, seven new official lead URLs were checked; six were confirmed through direct page open or official search results. The Zhengzhou Puri hospital contact page could not be directly opened by the browser tool and remains unresolved at URL level; its identity was separately corroborated by a Zhengzhou health-commission 2024 advertising-approval entry. The other **47 inherited URLs were not rechecked during this round**, so an overall live accessibility rate is not claimed. Search/index availability is not treated as reuse permission.

Examples of current first-party evidence include the Sichuan Provincial People’s Hospital ophthalmology department [department page](https://www.samsph.cn/eyes_intro/), Hangzhou First People’s Hospital [ophthalmology department](https://www.hz-hospital.com/service/deptment_details/id/35), and Hefei’s USTC First Affiliated Hospital [ophthalmology department](https://www.ahslyy.com.cn/jyb/col1193/13684). The first-party pages establish department evidence; multi-campus pages do not justify selecting one address.

## Matching and campus review

- Cross-source exact corroborations: **4**; these reinforce existing candidates and did not create new entities.
- Probable aliases requiring review: **2**.
- Ambiguous-campus cases requiring review: **1**.
- Conflicts: **0**.
- Candidate flags: **4** possible multi-site; **1** ambiguous-campus.

Probable aliases and campus conflicts remain separate review cases. No fuzzy matching or automatic entity merge was performed. Multi-site evidence was retained without inventing a single facility address.

## Remaining issues

1. **Addresses:** 155 candidates have no address recorded; keep those values empty until an exact official fact is verified.
2. **Freshness:** 11 candidates have no freshest evidence date.
3. **Coordinates:** no candidate has verified map coordinates. No geocoder was called and no placeholder points were generated.
4. **Coverage:** the 250-candidate target was not met (193 present); it remains a non-mandatory goal. The pool is not a national complete census.
5. **Use rights:** current public availability and university competition context do not by themselves establish display rights; see the Round 8 competition assessment.

The full record-level ledger and verification notes are local only at `C:\Users\72343\AppData\Local\EyeCareResourceMap\HarvestStore\round8\candidate-master-ledger.json`.
