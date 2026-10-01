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

运行完整数据库检查（临时启动 PostGIS、应用 P1/P2 migrations、运行 SQL tests、创建临时最小权限登录、运行数据库集成测试并清理 volume）：

```powershell
pwsh -NoProfile -File scripts/test-db.ps1
```

Linux CI 等价入口是仓库根目录的 `scripts/test-db.sh`。两个脚本都生成临时密码；检查完成后删除容器和数据库 volume。要手动长期启动本地 DB 时，先设置 `EYE_MAP_POSTGRES_PASSWORD`，并在 `EYE_MAP_DB_PORT` 选择本机可用端口，再执行 `docker compose up -d --wait`。

手动本地开发时，由管理员应用 migrations，并使用受信任管理员登录创建 collector runtime 登录：

```powershell
$env:EYE_MAP_POSTGRES_PASSWORD = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:EYE_MAP_DB_PORT = "55432"
docker compose up -d --wait
foreach ($migration in @('001_core.sql', '002_evidence_location.sql', '003_published_view.sql', '004_collector_permissions.sql')) {
  docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f "/workspace/db/migrations/$migration"
  if ($LASTEXITCODE -ne 0) { throw "Migration failed: $migration" }
}
$collectorPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "collector_password=$collectorPassword" -f /workspace/scripts/provision-collector-login.sql
docker compose exec -T db psql -U eye -d eye -f /workspace/scripts/seed-fixture-source.sql
$env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:55432/eye"
```

Fixture seed 仅创建合成来源及用于测试拒绝路径的 pending/suspended/blocked 登记。

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

## 测试、lint 与类型检查

```powershell
py -m pytest tests -m "not database" -q
py -m ruff check src tests
py -m mypy src/eye_collector
pwsh -NoProfile -File scripts/test-db.ps1
```

所有网络测试用 `httpx.MockTransport`，CI 不依赖公网真实来源。日志输出结构化字段；不输出请求头、响应体、URL 路径/查询参数或异常原文。
