# P4 坐标与地理编码实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给 P3 candidate 建立合规、可审计、幂等的坐标候选处理链路，并完成两项限定 P3 技术债。

**Architecture:** 新增独立 `geocoding` package，通过 typed provider 合约、FixtureGeocoder、坐标转换/校验及 repository pipeline 完成候选坐标暂存。Migration 006 添加候选坐标层、独立 `eye_geocode` 权限和 ETL terminal disposition；P3 matcher 仅将全表扫描替换为精确数据库候选筛选。

**Tech Stack:** Python 3.12、现有 HTTPX/Psycopg、PostgreSQL/PostGIS、pytest、Ruff、mypy、GitHub Actions。

---

## Task 1 — Geocoding contracts and error model

**Files:** 新建 `services/collector/src/eye_collector/geocoding/{__init__.py,models.py,providers/base.py}`；新建 `services/collector/tests/geocoding/test_models.py`。

- [ ] 先写并运行 failing tests：验证 policy/provider/result、精度、坐标系、状态与八类 error code 的不可变 typed contracts。
- [ ] 实现最小模型和 `GeocodeProvider.geocode(address, administrative_code)` 协议；provider 不接收 repository/connection。
- [ ] 单测、Ruff、mypy 通过后提交 `feat: define geocoding provider contracts`。

## Task 2 — Coordinate conversion and validation

**Files:** 新建 `geocoding/coordinates.py`、`geocoding/validation.py`、`tests/geocoding/test_coordinates.py`、`test_validation.py`。

- [ ] 先写 failing tests：WGS84 passthrough；GCJ02 逆转换已知合成点；转换后值与 GCJ02 不同；未知系统拒绝；世界范围、中国范围、null island、precision 和行政区树一致性。
- [ ] 实现纯函数 converter 和 validator；行政区相关性只读取 region parent graph，不能比较名称或代码前缀；verified 仅限 rooftop/building 且所有检查通过。
- [ ] 运行专项/全单测及静态检查，提交 `feat: validate candidate coordinates`。

## Task 3 — Fixture provider and shared HTTP behavior

**Files:** 新建 `geocoding/providers/fixture.py`、`tests/geocoding/test_fixture_provider.py`；修改 `pyproject.toml` marker/dependencies only if required。

- [ ] 先写 failing tests：provider 收到地址与行政区；fixture 返回 WGS84/GCJ02、ambiguous/no-result、429、timeout；semantic outcomes 不重试；仅使用 `fixture.invalid` transport。
- [ ] 通过现有 `HttpClient` + MockTransport 实现 provider，复用 P2 retry/rate limit/timeout/response size；provider quota 用 policy 限制本次运行请求数。
- [ ] 验证无公网请求、retry attempt 数、structured errors；提交 `feat: add offline fixture geocoder`。

## Task 4 — Migration 006 and geocoder role

**Files:** 新建 `db/migrations/006_geocoding.sql`、`db/tests/006_geocoding.sql`、`scripts/provision-geocode-login.sql`。

- [ ] 先写 SQL/RLS 权限断言：coordinate staging 字段/外键/唯一索引；verified CHECK；`eye_geocode` 最小读写权限；不得写源、facility、facility_locations、published view。
- [ ] migration 创建 `candidate_locations`（candidate/source_record 复合回链、address/result fingerprints、provider policy/result metadata、系坐标/精度/验证状态、时间）和 `etl_source_dispositions`（source_record + pipeline version 唯一）。
- [ ] 补充 SQL 测试：仅高精度且 WGS84 verified；invalid/review 坐标不可 verified；duplicate fingerprints 冲突幂等；terminal disposition；权限否定路径；提交 `feat(db): add candidate geocode staging`。

## Task 5 — P3 terminal skip and facility target query

**Files:** 修改 P3 `etl/pipeline.py`、`etl/repository.py`、`etl/models.py`；新建/修改 P3 单元和 DB integration tests。

- [ ] 先写 failing unit/DB tests：missing_name 只解析一次并留下 disposition；source_records 未变；匹配查询只返回 registration ID 或 exact name+adcode 的目标；原 match statuses/reasons 与旧全量输入一致。
- [ ] 以 migration disposition 排除同 pipeline version 的永久 skip；把全 facility_targets() 改为 `facility_targets_for(record)` SQL 候选集，并保留纯 matcher 逻辑。
- [ ] 对照旧全量查询结果做数据库 parity 和 EXPLAIN；提交 `fix: persist etl skips and bound facility matching`。

## Task 6 — Geocode repository and pipeline

**Files:** 新建 `geocoding/repository.py`、`geocoding/pipeline.py`、`tests/geocoding/test_pipeline.py`、`test_repository.py`。

- [ ] 先写 failing tests：合规 policy 才调用 provider；query 同时用地址/adcode；结果转换、区域/精度/范围检查；所有错误分类状态；dry-run 无写；重复执行唯一 result 不重复、地址变化及 provider-result 变化建立新历史版本。
- [ ] 实现分候选事务 repository，查询含地址/行政区/region hierarchy/evidence；provider 不访问 DB；`persistent_storage_allowed=false` 在请求前拦截且不返回/存储坐标；所有 coordinate 仅写 candidate staging。
- [ ] 运行专项测试、静态检查；提交 `feat: add idempotent candidate geocoding pipeline`。

## Task 7 — CLI and structured stats

**Files:** 修改 `services/collector/src/eye_collector/cli.py`；新建 `tests/geocoding/test_cli.py`。

- [ ] 先写 failing tests：`geocode --provider fixture --limit N [--candidate-id UUID] [--dry-run]` 参数校验、独立数据库 URL、JSON 所有规定计数、policy blocked/error exit codes。
- [ ] 仅支持 fixture provider；dry-run 允许请求/校验/计数但不持久化；更新 `.env.example` 中 `GEOCODE_DATABASE_URL` 使用提示，不添加真实 key。
- [ ] 运行 CLI 与现有 Collector 命令回归；提交 `feat: add geocode cli and statistics`。

## Task 8 — P4 DB integration, scripts, and CI

**Files:** 新建 `services/collector/tests/geocoding/test_geocode_database.py`；修改 DB runner、`db/tests`、`.github/workflows/collector.yml`。

- [ ] 先写 integration tests：migration 001–006，运行 P2 collector→P3 ETL→P4 fixture；least privilege、防 source/facility/facility_locations/view 写入、dry-run 0 行、result idempotency、无正式 publish。
- [ ] 更新 PowerShell 与 Bash runners：临时创建 collector/etl/geocode 登录，按顺序跑全部 migrations/SQL/unit/database tests，并总在 finally 清理数据库。
- [ ] CI 执行完整 P1–P4 unit/DB、Ruff、mypy、YAML 与 diff check；确保 transport 阻断外网。
- [ ] 本地运行完整临时 PostGIS、unit、静态检查和 Bash syntax；提交 `ci: verify p4 geocoding pipeline`。

## Task 9 — Documentation and PR

**Files:** 新建 `docs/geocoding/README.md`；修改 `services/collector/README.md`、本计划。

- [ ] 文档说明 provider policy gate、Fixture-only、WGS84/GCJ02 边界、校验/error 状态、staging lifecycle、CLI/dry-run、权限和迁移顺序；明确无正式 geocoder/批量试点/地图 UI。
- [ ] 复查 P3 matching 行为等价、source_records immutable、没有设施写入、计划无遗漏；全量 CI 等价与 `git diff --check` 通过。
- [ ] 推送 `p4-geocoding`，创建标题 `建立 P4 坐标与地理编码流水线` 的 `main` PR，等待 GitHub CI 成功后按用户的 P4 STATUS 模板汇报。
