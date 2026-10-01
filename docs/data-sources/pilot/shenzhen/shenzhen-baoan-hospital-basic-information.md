# 深圳市政府数据开放平台：宝安区-医院基本信息

**Decision: APPROVED for bounded local-file import by a registered platform user.**

This is a Shenzhen sample within Guangdong. It does not represent Guangdong-wide coverage. The first-round Guangdong health-institution query review remains `UNKNOWN` and is unchanged.

## Source metadata

- Source name: `shenzhen-open-data-baoan-hospital-basic-information`
- Source URL / dataset page: <https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636>
- Platform: 深圳市政府数据开放平台
- Data provider: 宝安区人民政府
- Open condition: 无条件开放
- Current record count shown by the official metadata endpoint: 27
- Data time range: 2017–2024; the dataset description says Bao'an no longer publishes these hospital basic-information records and the data will not be updated.
- Metadata update shown by the official endpoint: 2025-04-15; detail page publication date: 2025-07-16.
- Official field metadata endpoint: `POST https://opendata.sz.gov.cn/data/dataSet/getPreviewDataItem` with `resId=29200/02800636`.
- Agreement: <https://opendata.sz.gov.cn/maintenance/forward/toTermOfService>
- Reviewed: 2026-10-01

The current service terms state that successful registered users may freely access, acquire, use, utilize, and reuse data resources, while any paid or unpaid transfer of platform data resources is prohibited. Products using the data must attribute “深圳市政府数据开放平台.” Applications may be developed from platform data. If a dataset is taken offline for legal, policy, privacy, or other reasons, users may no longer save or use it. The platform may update its terms at any time.

## Explicit field mapping and minimization

The official metadata lists 17 fields. The adapter requires that exact header set, but stores only these approved fields:

| Official field | Official description | P2/P3 field |
|---|---|---|
| ID | 文档ID | `source_reference_id` and stable source key |
| NAME | 名称 | `name` |
| LOCAL | 所在区县 | `administrative_context` |
| ADDRESS | 详细地址 | `address` |
| LEVELS | 级别 | `hospital_level` |
| STEP | 等级 | `hospital_grade` |
| PROPERTY | 性质 | `source_category` |
| ADVANTAGE | 医疗优势与特长 | `specialties` evidence field |

Contact information, email, website, and other text are not retained. `ADVANTAGE` can supply explicit eye-related evidence only when its text itself mentions ophthalmology; the P3 evidence gate then stores the field and text. Hospital names alone never establish ophthalmology. A source row without explicit eye evidence remains `unknown`.

## Use decision and operational restrictions

- Data use, reuse, and app display: allowed for registered users, with attribution.
- Database storage: approved for the pilot as necessary to use/reuse the resource; the terms do not separately mention database storage, so this is an interpretation.
- Raw-data transfer/redistribution: **blocked**. Do not offer raw CSV/XLS dumps, dataset mirrors, resale, or raw database export APIs. Keep source payloads in a private project database; never commit downloaded rows or files to GitHub.
- Attribution: `深圳市政府数据开放平台` must remain attached to displayed records and details.
- Retention: if the platform removes the dataset, suspend the source and invoke the source-erasure workflow; raw snapshots, candidate derivatives, evidence, and candidate locations are removed, with only a non-content audit event retained.
- Access method: operator-downloaded official CSV/XLS/XLSX, then local import. No platform scraping, login automation, credential storage, or direct raw download endpoint calls.
- Coverage: Bao'an district only; 27 records is below the requested 50-record minimum, so all rows would require manual QA if officially downloaded.
- Freshness: archived content through 2024; current facility validity must be checked before any future publication.
