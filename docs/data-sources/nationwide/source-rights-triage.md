# Source Rights Triage

Reviewed: 2026-10-05T20:43:30+08:00
Round 5 merge: `7142c34d9aedf51b70bbf90e4f4447026ab4a317`

## Decision rule

No reuse permission is inferred from public availability or government authorship. A source is not import/display approved without explicit source-specific evidence covering storage, processing, and derived public-app use.

Public access and an observed download describe acquisition only. They do not establish durable storage, processing, public display, or redistribution rights. All local raw files remain outside Git.

## Summary

| Decision | Count |
| --- | ---: |
| `sources_reviewed` | 9 |
| `approved_for_controlled_import` | 0 |
| `approved_for_display` | 0 |
| `inspection_only` | 0 |
| `rights_review_required` | 8 |
| `blocked_rights` | 0 |
| `stale` | 1 |
| `tier_a_sources` | 3 |
| `tier_a_approved` | 0 |
| `historical_reacquire_required` | 18 |

All nine current local files passed existence, SHA-256, byte-size, sidecar, schema/header, row-count, source URL, region, and scope checks. No source is approved for import or display. The 18 historical-only datasets are `REACQUIRE_REQUIRED` and excluded from this review.

## Source decisions

### 1. 广州市卫生健康委员会发证的医疗机构信息 (`guangzhou-municipal-license-2026-07`)

- **Tier / decision:** A / `RIGHTS_REVIEW_REQUIRED` — The current official page publishes the dated workbook as an attachment, and the WJW separately says issued medical-institution information is publicly disclosed under the information-disclosure rules. Neither page grants this project a source-specific right to durably store, process derived fields, or use them in a public app. The schema also contains natural-person name fields.
- **Owner / region:** 广州市卫生健康委员会 / Guangdong (`440100`)
- **Official domain:** `wjw.gz.gov.cn`
- **Dataset / download page:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908026.html / https://wjw.gz.gov.cn/attachment/8/8050/8050355/10908026.xlsx
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T01:22:29.899673+08:00 / 2026-07-13
- **Scope:** Guangzhou institutions issued by the municipal health commission; not a complete city census.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 243 data rows; 57961 bytes; SHA-256 `24176cc7c96681d8924411320549ea224fe304cfd94a178642afaa8a4501277c`
- **Headers:** 序号; 机构名称; 登记号; 机构第二名称; 机构地址; 行政区划; 机构类别; 机构级别; 经营性质; 床位数; 牙椅数; 诊疗科目名称 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Workbook schema contains two natural-person-name fields. They are unnecessary and excluded from the public rights metadata and any future mapping, candidate/evidence persistence, and display.
- **Specialty / freshness:** 诊疗科目名称 / `CURRENT`
- **Evidence:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908026.html; https://wjw.gz.gov.cn/xxgk/jytablgz/szxtabljggk/content/post_9222976.html
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 2. 广州市内广东省卫生健康委员会发证的医疗机构信息 (`guangzhou-provincial-health-license-2026-07`)

- **Tier / decision:** A / `RIGHTS_REVIEW_REQUIRED` — The official page publishes a dated XLSX attachment for Guangzhou institutions licensed by the provincial health commission. Public disclosure is evidenced, but no source-specific reuse grant covers this project’s storage, processing, or public-app display; person-name fields require minimization.
- **Owner / region:** 广东省卫生健康委员会 / Guangdong (`440100`)
- **Official domain:** `wjw.gz.gov.cn`
- **Dataset / download page:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908048.html / https://wjw.gz.gov.cn/attachment/8/8050/8050355/10908048.xlsx
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T01:22:30.274696+08:00 / 2026-07-13
- **Scope:** Guangzhou institutions issued by the Guangdong health commission; not a complete city census.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 42 data rows; 23566 bytes; SHA-256 `77aa2cbfdd87f47b8549fca647171543cf0f2ad020b5416013e7484913ec4f6b`
- **Headers:** 序号; 机构名称; 登记号; 机构第二名称; 机构地址; 行政区划; 机构类别; 机构级别; 经营性质; 床位数; 牙椅数; 诊疗科目名称 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Workbook schema contains two natural-person-name fields. They are unnecessary and excluded from the public rights metadata and any future mapping, candidate/evidence persistence, and display.
- **Specialty / freshness:** 诊疗科目名称 / `CURRENT`
- **Evidence:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908048.html; https://wjw.gz.gov.cn/xxgk/jytablgz/szxtabljggk/content/post_9222976.html
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 3. 广州市内广东省中医药局发证的医疗机构信息 (`guangzhou-provincial-tcm-license-2026-07`)

- **Tier / decision:** A / `RIGHTS_REVIEW_REQUIRED` — The official page publishes a dated XLSX attachment for Guangzhou institutions licensed by the provincial TCM authority. The disclosed information and public download do not expressly authorize secondary storage, processing, or derived public-app use; person-name fields require minimization.
- **Owner / region:** 广东省中医药局 / Guangdong (`440100`)
- **Official domain:** `wjw.gz.gov.cn`
- **Dataset / download page:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908066.html / https://wjw.gz.gov.cn/attachment/8/8050/8050355/10908066.xlsx
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T01:22:30.613526+08:00 / 2026-07-13
- **Scope:** Guangzhou institutions issued by the Guangdong TCM bureau; not a complete city census.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 7 data rows; 14478 bytes; SHA-256 `001c36e76d3656849d1858e69a987b98b9fdf7079edf09ff621d89b8adda1dfd`
- **Headers:** 序号; 机构名称; 登记号; 机构第二名称; 机构地址; 行政区划; 机构类别; 机构级别; 经营性质; 床位数; 牙椅数; 诊疗科目名称 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Workbook schema contains two natural-person-name fields. They are unnecessary and excluded from the public rights metadata and any future mapping, candidate/evidence persistence, and display.
- **Specialty / freshness:** 诊疗科目名称 / `CURRENT`
- **Evidence:** https://wjw.gz.gov.cn/fwcx/yljgcx/content/post_10908066.html; https://wjw.gz.gov.cn/xxgk/jytablgz/szxtabljggk/content/post_9222976.html
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 4. 2026年常熟市民营医疗机构名录 (`changshu-private-medical-institutions-2026`)

- **Tier / decision:** B / `RIGHTS_REVIEW_REQUIRED` — The Suzhou-hosted page labels public/private Changshu list attachments and is dated 2026-03-04. It contains no dataset-specific license or permission for secondary storage, processing, or app display. Its scope is private institutions only.
- **Owner / region:** 常熟市卫生健康委员会 / Jiangsu (`320581`)
- **Official domain:** `www.suzhou.gov.cn`
- **Dataset / download page:** https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml / https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T01:22:31.305659+08:00 / 2026-03-04
- **Scope:** Changshu private institutions only.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 363 data rows; 34643 bytes; SHA-256 `0607acc4d46b1a322f8d9ede78c110b6b6ac94fd12a428e4e0c244af8167c5af`
- **Headers:** 序号; 机构名称; 登记号; 机构地址; 机构类别 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Inspected five-column schema contains institution name, registration ID, address, and category; no natural-person-name columns observed.
- **Specialty / freshness:** No explicit diagnostic-subject field / `CURRENT`
- **Evidence:** https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 5. 2026年常熟市公立医疗机构名录 (`changshu-public-medical-institutions-2026`)

- **Tier / decision:** B / `RIGHTS_REVIEW_REQUIRED` — The Suzhou-hosted page labels public/private Changshu list attachments and is dated 2026-03-04. It contains no dataset-specific license or permission for secondary storage, processing, or app display. Its scope is public institutions only.
- **Owner / region:** 常熟市卫生健康委员会 / Jiangsu (`320581`)
- **Official domain:** `www.suzhou.gov.cn`
- **Dataset / download page:** https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml / https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T01:22:31.018668+08:00 / 2026-03-04
- **Scope:** Changshu public institutions only.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 226 data rows; 22800 bytes; SHA-256 `c869c2e3ac043a465831aed1fcabafb794628734be16bac22f3aadfcfc289d4e`
- **Headers:** 序号; 机构名称; 登记号; 机构地址; 机构类别 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Inspected five-column schema contains institution name, registration ID, address, and category; no natural-person-name columns observed.
- **Specialty / freshness:** No explicit diagnostic-subject field / `CURRENT`
- **Evidence:** https://www.suzhou.gov.cn/szsrmzf/yljgmdml/202603/020cbba9e2df4d21ab52bc43bdcefcaa.shtml
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 6. 2025年度江阴市医疗机构执业注册登记情况（4-6月） (`jiangyin-registration-q2-2025`)

- **Tier / decision:** C / `STALE` — The source is a single, stale Q2 2025 registration event, not a directory. The official site copyright statement requires prior authorization for copying/republication of covered content and source attribution; whether this XLSX is covered is unresolved. Do not import or republish.
- **Owner / region:** 江阴市卫生健康委员会 / Jiangsu (`320281`)
- **Official domain:** `www.jiangyin.gov.cn`
- **Dataset / download page:** https://www.jiangyin.gov.cn/doc/2025/07/25/1343463.shtml / https://www.jiangyin.gov.cn/doc/2025/07/25/1343463.shtml
- **Policy evidence:** https://www.jiangyin.gov.cn/doc/2019/07/19/955915.shtml; https://www.jiangyin.gov.cn/doc/2021/11/24/995253.shtml
- **Retrieved / source updated:** 2026-10-05T01:24:33.566967+08:00 / 2025-Q2 (title scope; page published 2025-07-25)
- **Scope:** Single Q2 2025 registration event; not a registry.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 1 data rows; 11559 bytes; SHA-256 `512ae38f4c46e25bd9d0b2a8e68d7f7bc8137d3c073d59172a3469250e54cbfb`
- **Headers:** 序号; 单位名称; 统一社会信用代码; 决定时间; 文     号 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** NO_WITHOUT_PRIOR_AUTHORIZATION / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** The site copyright statement requires source attribution for covered reproduction; applicability to XLSX and derived records is unresolved. / No dataset-specific retention period or durable-storage permission located. / Privacy statement describes individual information rights; it does not establish a dataset-level withdrawal or retention process.
- **Personal-data risk:** Five-column inspected workbook is one Q2 2025 registration event and not a registry; no natural-person-name/address field was identified in the inspection schema.
- **Specialty / freshness:** No explicit diagnostic-subject field / `STALE`
- **Evidence:** https://www.jiangyin.gov.cn/doc/2025/07/25/1343463.shtml; https://www.jiangyin.gov.cn/doc/2019/07/19/955915.shtml; https://www.jiangyin.gov.cn/doc/2021/11/24/995253.shtml
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 7. 南京市二级及以上医疗机构名单 (`nanjing-secondary-medical-institutions-2026-05`)

- **Tier / decision:** B / `RIGHTS_REVIEW_REQUIRED` — The official page remains accessible and the published list is scoped to secondary-and-above institutions, excluding military hospitals; completeness is not asserted. No source-specific license or permission for secondary use or app display was located.
- **Owner / region:** 南京市卫生健康委员会 / Jiangsu (`320100`)
- **Official domain:** `wjw.nanjing.gov.cn`
- **Dataset / download page:** https://wjw.nanjing.gov.cn/njswshjhsywyh/202605/t20260514_5839731.html / https://wjw.nanjing.gov.cn/njswshjhsywyh/202605/t20260514_5839731.html
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** not recorded / 2026-05-08 (coverage cutoff stated in page)
- **Scope:** Nanjing secondary-and-above institutions; excludes military hospitals; completeness is not asserted.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; HTML; 123 data rows; 103194 bytes; SHA-256 `33beeba7eb79c8aeb9fcef2919099d8eb20ce61874b7e1db77e3cba10441640a`
- **Headers:** 序号; 机构名称; 行政区划; 机构类别; 机构级别; 机构等次; 机构性质 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Inspected seven-column HTML schema contains institution name, district, category, level, grade, and nature; no natural-person-name column observed.
- **Specialty / freshness:** No explicit diagnostic-subject field / `CURRENT`
- **Evidence:** https://wjw.nanjing.gov.cn/njswshjhsywyh/202605/t20260514_5839731.html
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 8. 无锡市医疗机构信息（截至2026年7月1日） (`wuxi-medical-institutions-2026-07`)

- **Tier / decision:** B / `RIGHTS_REVIEW_REQUIRED` — The official attachment is public. The WJW information-disclosure guide explains proactive disclosure and excludes information involving personal privacy, but does not grant this project rights to retain/process the spreadsheet or display derived records in a public app. The file includes natural-person name fields.
- **Owner / region:** 无锡市卫生健康委员会 / Jiangsu (`320200`)
- **Official domain:** `wjw.wuxi.gov.cn`
- **Dataset / download page:** https://wjw.wuxi.gov.cn/doc/2026/07/09/4802972.shtml / https://wjw.wuxi.gov.cn/uploadfiles/202607/09/2026070918561322639472.xlsx
- **Policy evidence:** https://wjw.wuxi.gov.cn/zfxxgk/index.shtml
- **Retrieved / source updated:** 2026-10-05T01:17:54.849133+08:00 / 2026-07-01
- **Scope:** Wuxi source list; completeness is not asserted.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; XLSX; 3817 data rows; 425460 bytes; SHA-256 `a9d95b2091cf64ac6c561701376e423e1c8b6416ba09aa01e84bb252d4057e1b`
- **Headers:** 机构名称; 机构第二名称; 机构地址; 登记发证机关; 机构类别; 机构级别; 经营性质; 床位数; 牙椅数; 统一社会信用代码 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Workbook schema contains two natural-person-name fields. They are excluded from this public rights metadata and must be excluded from any future mapping, candidate/evidence persistence, and display.
- **Specialty / freshness:** No explicit diagnostic-subject field / `CURRENT`
- **Evidence:** https://wjw.wuxi.gov.cn/doc/2026/07/09/4802972.shtml; https://wjw.wuxi.gov.cn/zfxxgk/index.shtml
- **Reviewed:** 2026-10-05T20:43:30+08:00

### 9. 武汉地区二、三级医疗机构名单 (`wuhan-secondary-tertiary-medical-institutions-2026-01`)

- **Tier / decision:** B / `RIGHTS_REVIEW_REQUIRED` — The public WJW HTML table identifies Wuhan secondary-and-tertiary institutions, not all Wuhan institutions. The page supplies no source-specific reuse license or permission for derived public-app use. Its eye-related field is institution category (眼科医院), not diagnostic-subject evidence.
- **Owner / region:** 武汉市卫生健康委员会 / Hubei (`420100`)
- **Official domain:** `wjw.wuhan.gov.cn`
- **Dataset / download page:** https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml / https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml
- **Policy evidence:** No dataset-specific reuse policy located in the reviewed official material.
- **Retrieved / source updated:** 2026-10-05T03:17:43+08:00 / 2026-01-22
- **Scope:** Wuhan secondary and tertiary institutions only; not all medical institutions in Wuhan.
- **Current status / access:** `UNKNOWN` / manual_only; no automated-access permission established
- **Local file:** verified=True; HTML; 185 data rows; 439356 bytes; SHA-256 `0ff8b653f891a48e37f3d8f6fc1e2bc836d12ec82b89ca4437c75b58eedac2b2`
- **Headers:** 序号; 行政区划; 机构名称; 地址; 经济类型; 机构类别; 机构级别; 营利性质 (natural-person field labels omitted where present)
- **Access / automated access:** YES_FOR_OBSERVED_PUBLIC_FETCH; access is distinct from reuse permission; automated access authorized=False
- **Storage / processing / derived display:** NOT_CLEARED_FOR_DURABLE_SECONDARY_STORAGE; current user-local quarantine retained for triage only / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW / NOT_CLEARED_PENDING_SOURCE_RIGHTS_REVIEW
- **Raw redistribution / commercial public-app use:** UNKNOWN; no explicit grant found / UNKNOWN; no source-specific authorization found
- **Attribution / retention / withdrawal:** If reuse is authorized, follow any source-specific requirements; none found for data reuse. / No dataset-specific retention period or durable-storage permission located. / No dataset-specific withdrawal/deletion procedure located.
- **Personal-data risk:** Inspected eight-column HTML table contains institution name, address, region, type and operational categories; no natural-person-name field observed.
- **Specialty / freshness:** No explicit diagnostic-subject field / `CURRENT`
- **Evidence:** https://wjw.wuhan.gov.cn/bsfw_28/bjcx/yljgmd/202601/t20260122_2716488.shtml
- **Reviewed:** 2026-10-05T20:43:30+08:00

## Import decision

No source-specific evidence found in this review expressly authorizes the combination required for controlled import: durable secondary storage, processing, and use of derived institution fields in this public-facing application. The three Tier A Guangzhou license datasets therefore remain `RIGHTS_REVIEW_REQUIRED`; do not change their `source_catalog` status or access policy. The Jiangyin event file is additionally `STALE`, has a single-row event scope, and its portal copyright statement requires prior authorization for covered copying/republication.

No real-data dry run, import, P3 ETL, duplicate detection, candidate persistence, source approval change, or isolated real-data database write was performed. Under the active **NO-APPLICATION ROUTE**, these nine files remain in the local Harvest Store as `QUARANTINED / INSPECTION ONLY`. Do not contact data providers, submit applications, or wait for written permission. Sources without sufficient existing public reuse terms are `SKIP_FOR_PRODUCTION`; see [Rights-Compatible Source Discovery](rights-compatible-source-discovery.md) for the current search and source decisions.
