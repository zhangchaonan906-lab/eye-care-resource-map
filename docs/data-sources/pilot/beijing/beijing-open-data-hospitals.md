# 北京市公共数据开放平台：医院

**Decision: APPROVED for bounded local-file import after portal registration.**

This is a separate review from the Beijing health-institution query entry. The first-round query-entry review remains `UNKNOWN` and is unchanged.

## Source metadata

- Source name: `beijing-open-data-hospitals`
- Source URL / dataset page: <https://data.beijing.gov.cn/zyml/wnkfsj/5652.htm>
- Platform: 北京市公共数据开放平台
- Data provider: 市卫健委
- Open condition: 无条件开放
- Dataset fields: `机构名称`
- Resource formats: CSV and XLSX are listed on the page; API is also listed.
- Published record count: 15,191
- Portal update shown: 2024-11-20; annual update cycle.
- Agreement: <https://data.beijing.gov.cn/gywm/mzsm/index.htm>
- Reviewed: 2026-10-01

The platform agreement says its government data can be downloaded and that users may obtain resources free of charge, hold non-exclusive use rights, and freely use, disseminate, and share them. It requires products using the data to identify “北京市公共数据开放平台” as the source and to file the application use with the platform. The page says the data is supplied by agencies and its completeness, accuracy, and timeliness are not guaranteed.

## Use decision

- Download: allowed through the portal's registered-user download flow.
- API: allowed through the portal's registered-user API flow.
- Database storage: approved as part of using and reusing the data; the agreement does not separately name database storage, so this is an interpretation of its broad use rights.
- Application display: allowed with source attribution and application filing completed before external release.
- Raw-data redistribution: allowed by the platform's express free dissemination and sharing clause, subject to applicable law and attribution.
- P5 access method: operator downloads the official file and imports no more than 150 records. The collector itself makes no network request for this manual-only source.
- Ophthalmology status: unknown unless separate source evidence establishes it. A name containing “眼科” is only a candidate clue.

The 15,191-row resource is not imported in full. This P5 source is approved but is not selected as the Beijing import dataset while the richer designated-institution dataset is the pilot choice.
