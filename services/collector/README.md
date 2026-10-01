# Eye Care Source Collector

P2 collector 提供受来源审批门控的采集框架。当前唯一 adapter 是使用内置合成 JSON 的 Fixture；它使用 HTTPX mock transport，所有请求都留在本地，不访问公网，也不包含生产医院数据。

## 安装

需要 Python 3.12+、Docker Compose 和 PostgreSQL/PostGIS image pull 能力。

```powershell
cd services/collector
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install -e ".[dev]"
```

Linux/macOS 激活方式为 `source .venv/bin/activate`。

## 配置与数据库

运行时从环境读取 `DATABASE_URL`、HTTP timeout、最大响应体、最多尝试次数、backoff base 和 User-Agent。缺少或非法的 `DATABASE_URL` 会在创建数据库连接前失败。`.env.example` 仅给出变量名和占位密码；程序不会自动读取 `.env`。请在本机 shell/secret manager 设置环境变量，不要提交 `.env`。

`DATABASE_URL` 应使用单独登录角色，该登录角色只继承数据库角色 `eye_collector`。migration `004_collector_permissions.sql` 只授予读取来源登记、有限读写 `import_runs`、写入/读取 `source_records` 的权限。collector 不能写 `facilities`、`candidate_records`、证据、位置、重复案件或发布视图。

运行完整数据库检查（临时启动 PostGIS、应用 P1–P4 migrations、运行 SQL tests、创建临时最小权限登录、运行数据库集成测试并清理 volume）：

```powershell
pwsh -NoProfile -File scripts/test-db.ps1
```

Linux CI 等价入口是仓库根目录的 `scripts/test-db.sh`。两个脚本都生成临时密码；检查完成后删除容器和数据库 volume。要手动长期启动本地 DB 时，先设置 `EYE_MAP_POSTGRES_PASSWORD`，并在 `EYE_MAP_DB_PORT` 选择本机可用端口，再执行 `docker compose up -d --wait`。

手动本地开发时，由管理员应用 migrations，并使用受信任管理员登录创建 collector runtime 登录：

```powershell
$env:EYE_MAP_POSTGRES_PASSWORD = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:EYE_MAP_DB_PORT = "55432"
docker compose up -d --wait
foreach ($migration in @('001_core.sql', '002_evidence_location.sql', '003_published_view.sql', '004_collector_permissions.sql', '005_etl_candidates.sql', '006_geocoding.sql')) {
  docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f "/workspace/db/migrations/$migration"
  if ($LASTEXITCODE -ne 0) { throw "Migration failed: $migration" }
}
$collectorPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "collector_password=$collectorPassword" -f /workspace/scripts/provision-collector-login.sql
docker compose exec -T db psql -U eye -d eye -f /workspace/scripts/seed-fixture-source.sql
$env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:55432/eye"
$etlPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "etl_password=$etlPassword" -f /workspace/scripts/provision-etl-login.sql
$env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$etlPassword@127.0.0.1:55432/eye"
$geocodePassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "geocode_password=$geocodePassword" -f /workspace/scripts/provision-geocode-login.sql
$env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$geocodePassword@127.0.0.1:55432/eye"
```

Fixture seed 仅创建合成来源及用于测试拒绝路径的 pending/suspended/blocked 登记。

P3 ETL 使用隔离的 `ETL_DATABASE_URL` 和 `eye_etl_runtime` 最小权限账号。先按 migration 005 升级数据库，并用 `scripts/provision-etl-login.sql` 创建登录；`scripts/test-db.ps1` 会演示完整合成数据测试流程。详见 [`docs/etl/README.md`](../../docs/etl/README.md)。

## 运行 Fixture

在仓库根目录启动本地数据库、应用 migrations、创建 runtime 登录并 seed Fixture 后：

```powershell
cd services/collector
py -m eye_collector.cli run --source fixture --region 110000 --limit 5
py -m eye_collector.cli run --source fixture --region 110000 --dry-run --limit 5
```

CLI 必须能在 `source_catalog` 精确找到匹配的来源名称和目录 URL，且该来源 `status=approved`、有 `use_basis`、`permitted_fields` 非空，并且 `access_policy=automated_access_allowed`。拒绝发生在创建 `import_runs` 之前。

Dry-run 仍会创建并结束 `import_runs`，用于记录审计与 requested/received 统计，但不会写 `source_records`。`counts.inserted` 是尚未写入时预计新增的快照数；已存在的内容计入 `unchanged`。`requested` 是请求页数，`received` 是页中返回的原始记录数。

Fixture 包含 7 个唯一 key、分页重复记录、可更新版本，以及 429、500、timeout mock 场景。`--fixture-revision updated` 用于验证同一来源 key 的内容变更形成新历史 snapshot。`--limit` 限制处理的记录数；网络层仍只访问 Fixture mock transport。

## P3 ETL 处理

在完成迁移和设置独立 ETL 登录后，运行：

```powershell
$env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:<password>@127.0.0.1:55432/eye"
py -m eye_collector.cli process --limit 100
```

命令只读取已批准并允许自动采集的来源快照，输出 JSON 处理统计。它不修改原始快照、不写正式医院表，也不发布或合并医院。无名称快照以当前 pipeline version 记录为终态跳过；重新执行不会反复读取这些快照，也不会重复创建已处理候选。

## P4 候选坐标处理

P4 只提供离线 `fixture` geocoder。provider 通过现有受限 HTTP client，因此使用相同的超时、响应体上限、重试和速率控制。真实地图/地理编码 provider 尚未获准接入；CLI 不接受其他 provider，集成测试只使用 mock transport。

配置独立的 `GEOCODE_DATABASE_URL`，登录角色只继承 `eye_geocode`。该角色可读取候选、证据、行政区与 provider policy，并只可向 `candidate_locations` 插入记录；不能修改 source/facility、正式位置或发布视图。数据库 provider policy 缺失时处理失败；持久化许可关闭时不调用 provider，仅写入不含 provider 返回数据的 `POLICY_BLOCKED` review 结果。

```powershell
$env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:<password>@127.0.0.1:55432/eye"
py -m eye_collector.cli geocode --provider fixture --dry-run --limit 20
py -m eye_collector.cli geocode --provider fixture --limit 20
py -m eye_collector.cli geocode --provider fixture --candidate-id 123e4567-e89b-12d3-a456-426614174000 --dry-run
```

Dry-run 会请求离线 fixture 并执行坐标、精度和 `regions.parent_id` 层级校验，但不写入结果。正式运行只写 `candidate_locations` staging，原始 provider 坐标系和转换后的 WGS84 坐标分别记录；未验证、低精度或区域不明的结果进入 review，坐标不进入 `facility_locations`。地址/结果使用 canonical SHA-256 指纹，provider/version 下已有结果的候选不会重复请求。

WGS84 保持原值，GCJ-02 使用本地逆转换后转存 WGS84，UNKNOWN 系统不能成为 verified 坐标。已验证精度仅 rooftop/building，且要求中国范围、非 Null Island、行政区层级一致及 provider accuracy 0–100m。P4 没有真实 provider 授权、没有真实坐标记录、没有北京/广东试点或 facility 发布流程。

## 测试、lint 与类型检查

```powershell
py -m pytest tests -m "not database and not etl_database and not geocode_database" -q
py -m ruff check src tests
py -m mypy src/eye_collector
pwsh -NoProfile -File scripts/test-db.ps1
```

所有网络测试用 `httpx.MockTransport`，CI 不依赖公网真实来源。日志输出结构化字段；不输出请求头、响应体、URL 路径/查询参数或异常原文。
