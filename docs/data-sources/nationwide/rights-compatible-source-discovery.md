# Rights-Compatible Source Discovery — No-Application Route

Reviewed: 2026-10-05 (Asia/Shanghai)

## Decision rule

This search accepts a source only when all of the following are supported by current official evidence: official provenance; access to core data without registration, login, CAPTCHA, or application; public terms that already permit acquisition, storage, processing, and derived public-app display; and a workable attribution/restriction path. A directory label such as `无条件开放`, government authorship, or a public download link does not by itself establish all of these conditions.

The project will use only institution name, address, administrative region, institution category, level, explicit ophthalmology evidence from source specialties, and the official source link. Unnecessary personal fields are excluded from processing, persistence, and display.

## Outcome

No source checked in this pass met every gate. There are no `READY_NO_APPLICATION` sources and no controlled import is authorized by this review. No application, account registration, permission request, or provider contact was made. The nine previously harvested local files remain `QUARANTINED / INSPECTION ONLY`; their existing hashes and sizes were rechecked against the local Harvest Store on 2026-10-05. They are not production data.

| Status | Count | Meaning in this review |
| --- | ---: | --- |
| `READY_NO_APPLICATION` | 0 | All access and reuse gates passed |
| `PUBLIC_BUT_RIGHTS_UNCLEAR` | 5 | Official lead exists, but one or more terms, access, or dataset-specific facts remain unverified |
| `APPLICATION_REQUIRED` | 1 | The documented acquisition route requires an application/approval |
| `LOGIN_REQUIRED` | 2 | The platform's published instructions require registration/login to obtain/use core resources |
| `BLOCKED_ACCESS` | 1 | Official download flow for this dataset was previously blocked by the portal redirect error |
| `STALE` | 1 | Catalog metadata is newer than the listed downloadable files |

Counts are for the ten catalog leads below; some rows also have secondary concerns noted in the decision column.

## Official catalog leads checked

| # | Dataset / region | Official evidence | Fields / freshness / format | No-application decision |
| ---: | --- | --- | --- | --- |
| 1 | 北京市医保局“定点医疗机构信息” / city | [Dataset detail](https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm); [platform terms](https://data.beijing.gov.cn/grzx/index.htm) | 4,877 records; updated 2026-08-13; monthly; hospital name, address, level, category, district, designated-institution code. | `LOGIN_REQUIRED`: the platform terms say users must register to download or call resources. Terms grant free, non-exclusive use and free use/distribution/sharing, but also require use-case filing and cooperation with surveys. No registration or filing was attempted. |
| 2 | 北京市卫生健康委“医院” / city | [Dataset detail](https://data.beijing.gov.cn/zyml/wnkfsj/5652.htm); same [platform terms](https://data.beijing.gov.cn/grzx/index.htm) | 15,191 records; updated 2024-11-20; annual; source description identifies institution name. | `LOGIN_REQUIRED`: same mandatory registration for core data; source is older and does not expose the required address/category/specialty fields in its public description. |
| 3 | 广州市天河区卫健局备案医疗机构 / district plan lead | [2025 Tianhe public-data plan](https://www.thnet.gov.cn/gzthzs/attachment/7/7931/7931375/10551889.pdf); [Guangzhou open-data portal](https://data.gz.gov.cn/) | Plan lists institution name/address and diagnostic subjects, XLS/XLSX/CSV/JSON/XML/RDF, annual, unconditional open. A live dataset detail/download page was not verified. | `PUBLIC_BUT_RIGHTS_UNCLEAR`: planning metadata is not a current dataset-specific reuse license. No public terms proving storage, processing, and derived app display were found for this item. No application was submitted. |
| 4 | 杭州市萧山区三级医院信息 / district | [Hangzhou open-data portal](https://data.hangzhou.gov.cn/dop/) | The official homepage lists the dataset under 萧山区卫生健康局 with a 2026-02-03 change time. Exact fields, scope, open level, and anonymous file route were not verified. | `PUBLIC_BUT_RIGHTS_UNCLEAR`: the platform [agreement](https://data.hangzhou.gov.cn/dop/pdf/agreement.pdf) requires attribution and application-situation filing; it also reserves review before publishing an app on the platform. Dataset-specific access and whether those obligations fit this project's route remain unverified. |
| 5 | 台州市全市医疗机构名录信息 / city | [Taizhou official dataset catalog](https://data.zjtz.gov.cn/tz/open/table?deptId=babbdaf2e2234c23a684655b9d8a9986) | Official listing says annual update; name, address, category, level, region; XLS/CSV/XML/JSON/RDF. Last catalog sync shown as 2026-08-26. | `PUBLIC_BUT_RIGHTS_UNCLEAR`: current reuse license and whether file download works without login were not verified. No production-use rights inferred from format or catalog visibility. |
| 6 | 达州市医疗机构信息 / city | [Official Dazhou dataset detail and license](https://www.dazhoudata.cn/oportal/catalog/09a85d9a29a34b838ffca98c345fc4da) | Catalog says 64,978 rows, updated 2026-08-14; name/address and two institution identifiers; XLS/CSV/XML/JSON/RDF entries are shown, each file row is dated 2024-10-01. No specialty field is listed. | `STALE`: the current files listed for download date from 2024-10-01 despite newer catalog metadata. The platform license for unconditional data allows free acquisition/use/development/dissemination and requires attribution, but also requires periodic usage feedback to the data owner. The file access flow and a compliant reporting path were not verified; do not import this stale snapshot. |
| 7 | 达州市医疗机构执业登记信息 / city | [Official Dazhou registration catalog search](https://www.dazhoudata.cn/oportal/catalog/index?tagName=%E7%99%BB%E8%AE%B0) | Catalog listing: 4,018 records, updated 2026-08-14; institution name/address/category/level/specialties/registration number; XLS/CSV/XML/JSON/RDF and API listed. | `BLOCKED_ACCESS`: the previously attempted normal official download flow ended in `ERR_INVALID_REDIRECT`. Preserve the lead as file-acquisition blocked; do not retry, guess an endpoint, or classify the dataset as rejected/unavailable. |
| 8 | 宜昌市医院信息 / city | [Official Yichang dataset detail](https://data.yichang.gov.cn/kf/open/table/detail/1001691) | 332 records; updated 2026-07-10; annual/irregular listing; description includes institution name, type, administrative region, level, address, plus contact/personnel fields; XLS/CSV/XML/JSON/RDF. | `PUBLIC_BUT_RIGHTS_UNCLEAR`: item is marked fully public/unconditionally open, but source-specific reuse terms and anonymous download behavior were not verified. Only permitted project fields could be retained if later cleared. |
| 9 | 中山市《医疗机构执业许可证书》医疗机构基本信息 / city | [Official dataset detail](https://zsdata.zs.gov.cn/web/dataServerView?id=4028844958658659015865ea7bf400c0); [platform terms](https://zsdata.zs.gov.cn/web/fwtk) | 1,908 records; updated 2026-07-10; XLS/JSON/CSV; institution name/address/category/level and natural-person name fields. | `PUBLIC_BUT_RIGHTS_UNCLEAR`: the terms grant free non-exclusive use, but prohibit transfer of platform data and require use-case filing; the terms do not clearly settle field-level derived display in this app. No filing or application was made. |
| 10 | 温州市定点医疗机构名单信息 / city API | [Official API detail](https://data.wenzhou.gov.cn/jdop_front/detail/api.do?iid=16980) | 524 records; updated 2026-08-02; name/address/医保区划/收费等级; documented paginated API. | `APPLICATION_REQUIRED`: the documented path requires account registration, creating an application, and API access approval. No account was created and no application submitted. |

The primary labels above are mutually exclusive for counting. Dazhou's stale row also has open-license and access-path questions, but is counted under `STALE` rather than `PUBLIC_BUT_RIGHTS_UNCLEAR`.

## Existing nine-file quarantine

The nine local assets from the prior triage were rechecked by SHA-256 and byte size against the Harvest Store; all nine matched. Keep them `QUARANTINED / INSPECTION ONLY`. Do not change the existing source catalog status or access policy, and do not move these files into the formal database unless a future review finds existing public evidence that clears every gate.

## Import decision

`NO_APPLICATION_ROUTE_CURRENTLY_HAS_NO_IMPORTABLE_SOURCE`.

No source was assigned `READY_NO_APPLICATION`; therefore there was no SHA-verified new import, dry run, controlled import, P3 ETL, replay test, or production database write. No source status was promoted. Applications submitted: **0**. Permission requests sent: **0**. Government contacts made: **0**.

Next: continue technical work independently of source rights (coordinate-provider evaluation, compliant basemap, deployment, and UI polish). Recheck these catalog leads only when official public evidence changes. Import only sources that later meet the complete `READY_NO_APPLICATION` rule.
