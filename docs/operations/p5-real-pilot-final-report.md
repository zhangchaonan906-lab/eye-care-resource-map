# P5 北京与深圳真实数据试点最终报告

**状态：完成（本机持久化 Pilot/Staging 环境）**

**报告日期：2026-10-01**

本报告只记录受控试点的汇总和已核验异常，不包含完整医院数据。真实文件、数据库凭据、SQL 导出和 QA 行样本均未加入 Git。

## 环境与执行范围

- PostgreSQL/PostGIS：独立 Docker Compose 项目 `eye-p5-pilot`，named volume `eye-p5-pilot_eye_pgdata`，仅监听 `127.0.0.1`；已应用 P1–P5 migrations、来源 catalog seeds 及 P5 批次限定 ETL migration 010。
- 实际连接用途：collector 使用 `eye_collector_runtime` 写入获准的文件导入；ETL 使用 `eye_etl_runtime` 读取受限批次并写 candidate/evidence/review；管理员连接仅用于迁移和 QA。密码保存在用户本机 DPAPI 加密状态文件中，未写入仓库。
- ETL 只按两个正式导入的 `import_run_id` 执行。未处理 fixture/test 数据；来源仍保持 `manual_only`。原始 `source_records` 的 canonical SHA-256 全部与数据库内容一致，ETL 登录无 `UPDATE`/`DELETE` 权限。
- 北京 dry-run：`9f1b938b-6395-455f-99d3-9e8086ec9d9f`；正式导入：`34a7aba6-0813-4fbd-aac7-fed1bf5224f6`。
- 深圳 dry-run：`8f3ba273-2113-4b05-8cff-7f8f7133f362`；正式导入：`9f549a6a-7aa7-4d0e-ba0f-6980b293a122`。
- Operator：`zhangchaonan906-lab`。取得时间沿用 Windows 文件创建 metadata，未改成运行时间。

## 文件与 provenance

| Region / source | File fingerprint | Provenance |
|---|---|---|
| Beijing designated medical institutions | `北京市医疗保障局-定点医疗机构信息.xlsx`; SHA-256 `49848ce24856fb28ed542f46c0e5f805c35b19c3fcea0d85d97d0734487fa918`; 493,514 bytes | obtained `2026-10-01T19:06:27.1820713+08:00`; official dataset page and source update date retained in `import_runs` |
| Shenzhen Bao'an hospitals | `宝安区-医院基本信息20261001071251275982.zip`; SHA-256 `9b9554a8553676c906b8b364987ca11d929a204a02fdd3503e23be1cf86348d7`; 35,368 bytes | obtained `2026-10-01T19:12:52.6051500+08:00`; member `宝安区-医院基本信息_2920002800636.xlsx`, SHA-256 `55a06fd088b436506a4c5692424a07e487159300ad6f191fce046bdbcdd1a129`; official dataset page and source update date retained in `import_runs` |

Both staging preflights returned `ready_to_import=true`, `schema_match=true`, the expected fingerprints, and the approved regions. Beijing had 4,876 file rows and imported only the first 50. Shenzhen had 27 rows and all were inspected/imported; no rows were fabricated to meet a larger sample size.

## Import and ETL results

| Metric | Beijing | Shenzhen / Bao'an |
|---|---:|---:|
| Rows received | 50 | 27 |
| New immutable source snapshots | 50 | 24 |
| Exact unchanged source rows | 0 | 3 |
| Import failures | 0 | 0 |
| P3 candidates created | 50 | 22 |
| Terminal placeholder skips | 0 | 2 |
| P3 ETL errors | 0 | 0 |
| Duplicate review cases | 0 | 8 |
| Candidates in pending duplicate cases | 0 | 18 |

Beijing P3 statistics: 50 source records read, 50 candidates created, 0 evidence rows, 0 duplicate cases, 0 errors. All 50 candidates have ophthalmology evidence `unknown`, as expected because this dataset has no explicit department/ophthalmology fields.

Shenzhen P3 statistics: 24 source records read, 22 candidates created, 2 skips, 5 evidence rows, 8 duplicate cases, 10 newly flagged candidates, 0 errors. Those five evidence rows belong to five candidate records and two exact normalized-name groups; this is not a count of five distinct eye hospitals or verified institutions.

## QA findings

### Beijing

- All 50 source rows retained; all 50 names and addresses are non-empty and all 50 administrative codes are six digits.
- `北京中医药大学第三附属医院` (`110105`) is retained and flagged `multi_district_address=true`, `needs_manual_location_review=true`; its source address includes 朝阳区 and 海淀区.
- `北京市隆福医院（北京中西医结合老年医院）北京市东城区景山社区卫生服务中心` (`110101`) is retained and flagged `multi_district_address=true`, `needs_manual_location_review=true`; its address mentions 东城区、昌平区 and 朝阳区.
- `三河中海实业有限责任公司燕郊基地分公司医务室` (`110101`) is retained as a candidate and flagged `region_address_conflict=true`, `needs_manual_review=true`; the address says 三河市燕郊开发区. No source field was rewritten and no 河北 code was inferred.
- None of these records has a verified location. Geocoding was not called.

### Shenzhen

- Both `name = "-"` source snapshots are retained with P3 disposition `terminal_skip / invalid_name_placeholder`; neither generated a candidate.
- Exact repeated rows for source keys `5184056` and `5668097` yielded one snapshot per content hash; the 2 + 1 repeats were counted as unchanged. No duplicate snapshots were created.
- Distinct content versions for keys `5184063` and `766461` were kept as separate snapshots (two hashes per key).
- Key `6184056` retained both hashes: the placeholder snapshot was terminally skipped, while `宝安区慢性病防治院` generated a candidate. A source key is not treated as a permanent facility identity.
- Eight deterministic duplicate cases remain pending review; no candidate or facility was merged. Two observed semantic name pairs need manual review because their names differ and the exact-name queue does not connect them: `深圳市宝安区中心医院简介` / `深圳市宝安区中心医院`, and `深圳市宝安人民医院（集团）一院` / `宝安人民医院（集团）一院`.
- Explicit ophthalmology evidence: five evidence rows across five candidate records and two exact normalized-name groups. These are candidate-level groupings only; no institution deduplication was inferred.

Existing operator QA samples were verified outside the repository: Beijing 50 rows and Shenzhen 27 rows with the required QA columns. The three Beijing location/address anomalies and Shenzhen placeholder, repeated-key, changed-snapshot, source-key conflict, evidence, and semantic-name cases above were checked against the imported snapshots and candidates.

## Database counts and protected boundaries

| Table / state | Before formal import | After import, ETL and replay |
|---|---:|---:|
| `source_records` | 0 | 74 |
| `candidate_records` | 0 | 72 |
| `facilities` | 0 | 0 |
| `facility_locations` | 0 | 0 |
| `duplicate_cases` | 0 | 8 |
| `import_runs` | 2 dry-run audit rows | 6 (2 dry-run, 2 formal, 2 replay) |
| `candidate_locations` | 0 | 0 |

No facility was published. No production coordinates were stored. No geocoder calls were made. No automated duplicate merge was performed.

## Idempotent replay

The same source files, regions, limits, operator, and acquisition times were run again after the formal import:

- Beijing: 50 received, 0 inserted, 50 unchanged, 0 failed.
- Shenzhen: 27 received, 0 inserted, 27 unchanged, 0 failed.
- Database `source_records` remained 74; replay added no snapshots.

## Remaining risks and coverage gaps

- This is a 50-row Beijing sample and the complete 27-row Bao'an dataset, not nationwide coverage or full Beijing coverage.
- Beijing's multi-district addresses and one cross-region address conflict remain unresolved location-review items. They do not block record retention or P3 candidates, but block treating a location as verified.
- Shenzhen semantic duplicates remain human-review work; the current exact deterministic queue intentionally does not fuzzy-match or merge them.
- Eye evidence indicates explicit source text only; it does not establish facility-level ophthalmology status after entity resolution.
- Before any public display, complete the Beijing attribution/application-filing requirements and Shenzhen attribution and withdrawal/retention requirements documented in the source reviews.
- Real geocoding, coordinates, maps, nearby search, facility verification/publication, and national expansion remain out of scope. Recommended next phase: plan P6 only after location QA and source attribution/retention operations are agreed.
