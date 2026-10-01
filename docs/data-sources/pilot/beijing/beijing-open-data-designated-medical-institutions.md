# 北京市公共数据开放平台：定点医疗机构信息

**Decision: APPROVED for bounded local-file import after portal registration.**

This is a separate review from the Beijing health-institution query entry. The first-round query-entry review remains `UNKNOWN` and is unchanged.

## Source metadata

- Source name: `beijing-open-data-designated-medical-institutions`
- Source URL / dataset page: <https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm>
- Platform: 北京市公共数据开放平台
- Data provider: 市医保局
- Open condition: 无条件开放
- Dataset fields: 医院名称、医院地址、医院等级、医院类别、所属区、定点医疗机构编码
- Resource formats: the page lists structured table/file resources and documents CSV/XLSX download; it also exposes a JSON API.
- Published record count: 4,877
- Portal update shown: 2026-08-13; monthly update cycle.
- Agreement: <https://data.beijing.gov.cn/gywm/mzsm/index.htm>
- Reviewed: 2026-10-01

The platform agreement permits free, non-exclusive use and free dissemination/sharing of its government data. Derived applications must identify “北京市公共数据开放平台” and file the application use with the platform. The dataset page labels access “无条件开放.” The platform FAQ says users must register to download datasets or call APIs.

## Explicit field mapping

| Official field | P2/P3 field |
|---|---|
| 医院名称 | `name` |
| 医院地址 | `address` |
| 所属区 | `administrative_context` |
| 医院等级 | `hospital_grade` |
| 医院类别 | `source_category` |
| 定点医疗机构编码 | `registration_id` and stable source key |

Mappings are by exact header name. A missing, duplicate, or unexpected header fails the adapter before records are inserted. The area label is preserved as text; no province/city/district code is inferred. The source's registration code is treated as reliable for exact P3 registration-ID matching.

## Use decision

- Download and API access: allowed after portal registration.
- Database storage: approved as part of the platform's broad free use/reuse rights; the agreement does not separately name database storage, so this is an interpretation.
- Application display: allowed with source attribution and application filing completed before external release.
- Raw-data redistribution: allowed by the platform's free dissemination/sharing clause, subject to applicable law and attribution.
- P5 access method: operator downloads the official file. The collector uses the manual-only file adapter and does not log in, call the platform, scrape HTML, or store credentials.
- P5 import target: 50–150 records after authorized file access; no nationwide/full-city batch import.
- Eye evidence: the listed fields do not include departments, so ophthalmology remains unknown for records without other explicit evidence.
