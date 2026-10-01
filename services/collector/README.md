# Eye Care Source Collector

P2 collector 提供受来源审批门控的采集框架。当前包括离线合成 Fixture adapter，以及 P5 的官方数据本地文件 adapter。Fixture 使用 HTTPX mock transport，不访问公网；文件 adapter 只读取操作员从官方门户合法取得的本地 CSV/XLS/XLSX，不登录门户、不抓网页、不下载数据，也不包含生产医院数据。

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

运行完整数据库检查（临时启动 PostGIS、应用 P1–P5 migrations、运行 SQL tests、创建临时最小权限登录、运行数据库集成测试并清理 volume）：

```powershell
pwsh -NoProfile -File scripts/test-db.ps1
```

Linux CI 等价入口是仓库根目录的 `scripts/test-db.sh`。两个脚本都生成临时密码；检查完成后删除容器和数据库 volume。要手动长期启动本地 DB 时，先设置 `EYE_MAP_POSTGRES_PASSWORD`，并在 `EYE_MAP_DB_PORT` 选择本机可用端口，再执行 `docker compose up -d --wait`。

手动本地开发时，由管理员应用 migrations，并使用受信任管理员登录创建 collector runtime 登录：

```powershell
$env:EYE_MAP_POSTGRES_PASSWORD = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:EYE_MAP_DB_PORT = "55432"
docker compose up -d --wait
foreach ($migration in @('001_core.sql', '002_evidence_location.sql', '003_published_view.sql', '004_collector_permissions.sql', '005_etl_candidates.sql', '006_geocoding.sql', '007_source_open_data_rights.sql')) {
  docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f "/workspace/db/migrations/$migration"
  if ($LASTEXITCODE -ne 0) { throw "Migration failed: $migration" }
}
$collectorPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "collector_password=$collectorPassword" -f /workspace/scripts/provision-collector-login.sql
docker compose exec -T db psql -U eye -d eye -f /workspace/scripts/seed-fixture-source.sql
docker compose exec -T db psql -U eye -d eye -f /workspace/scripts/seed-opendata-sources.sql
$env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:55432/eye"
$etlPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "etl_password=$etlPassword" -f /workspace/scripts/provision-etl-login.sql
$env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$etlPassword@127.0.0.1:55432/eye"
$geocodePassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
docker compose exec -T db psql -U eye -d eye -v "geocode_password=$geocodePassword" -f /workspace/scripts/provision-geocode-login.sql
$env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$geocodePassword@127.0.0.1:55432/eye"
```

Fixture seed 仅创建合成来源及用于测试拒绝路径的 pending/suspended/blocked 登记。

Open-data source seed 只写入来源审查元数据，不包含真实医院数据。北京“医院”和“定点医疗机构信息”及深圳宝安医院名录分别登记为 `manual_only`；该设置只允许从操作员合法下载的本地文件导入，不授予 HTTP 抓取权限。深圳来源的原始数据转让和再分发均被禁止；平台下架后需暂停来源并调用受限来源清除流程。见 [`docs/data-sources/pilot/README.md`](../../docs/data-sources/pilot/README.md)。

P3 ETL 使用隔离的 `ETL_DATABASE_URL` 和 `eye_etl_runtime` 最小权限账号。先按 migration 005 升级数据库，并用 `scripts/provision-etl-login.sql` 创建登录；`scripts/test-db.ps1` 会演示完整合成数据测试流程。详见 [`docs/etl/README.md`](../../docs/etl/README.md)。

## 运行 Fixture

在仓库根目录启动本地数据库、应用 migrations、创建 runtime 登录并 seed Fixture 后：

```powershell
cd services/collector
py -m eye_collector.cli run --source fixture --region 110000 --limit 5
py -m eye_collector.cli run --source fixture --region 110000 --dry-run --limit 5
```

CLI 必须能在 `source_catalog` 精确找到匹配的来源名称和目录 URL，且该来源 `status=approved`、有 `use_basis`、`permitted_fields` 非空。HTTP adapter 只接受 `access_policy=automated_access_allowed`；本地文件 adapter 只接受 `access_policy=manual_only`。拒绝发生在创建 `import_runs` 之前。

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

## P5 官方开放数据文件导入

数据文件必须由获授权的操作员在官方平台获取，并放在仓库之外。CLI 不登录平台、不下载文件、不存储账号密钥，也不抓取网页。

### 文件预检与来源追溯

拿到官方原始导出文件后，先运行只读预检。预检只读取本地文件，并以只读数据库事务检查来源准入、数据集页面和试点剩余容量；不会创建 import run、snapshot 或其他数据库记录。原始文件保持不变，SHA-256 由原始字节计算。

```powershell
py -m eye_collector.cli inspect-file `
  --source beijing-open-data-designated-medical-institutions `
  --file C:\secure\beijing-designated-medical-institutions.xlsx

py -m eye_collector.cli inspect-file `
  --source shenzhen-open-data-baoan-hospital-basic-information `
  --file C:\secure\shenzhen-baoan-hospital-basic-information.zip
```

JSON 结果包含文件名、SHA-256、文件大小、格式、表头、完整数据行数、准入来源/预期 schema、schema 匹配结果、试点上限与剩余容量、单次运行上限、允许地区和 `ready_to_import`。支持 CSV/XLS/XLSX，最大 10 MiB。仅显式允许 ZIP 的来源可读取 ZIP；深圳适配器只接受单个安全路径下的 XLSX member，直接从内存读取，不解压到磁盘，并报告 member 名称、SHA-256 和大小。实际导入前还会再次核对原始文件指纹。行数上限为每次 150 条，试点来源组的累计上限由数据库实施。检查返回非零或 `ready_to_import=false` 时不得导入。

每次文件导入的 `import_runs.id` 即 `import_run_id`。该记录通过 `source_id` 关联 `source_catalog`，并保存原始文件名（仅 basename）、原始字节 SHA-256、文件字节数、取得时间、数据集页面、目录记录的数据更新时间、操作员和固定采集方式 `official_portal_manual_download`。操作员与取得时间必须由实际下载人员提供，不能猜测；可用 `--operator` / `--obtained-at`，或设置 `PILOT_OPERATOR` / `PILOT_FILE_OBTAINED_AT`（ISO-8601 且带时区）。同一个文件可以重复运行；每次运行均保留 provenance，而 source snapshot 仍按 `(source_id, source_key, content_hash)` 幂等去重。

确认预检、平台当前许可及 schema 后，先执行 dry-run 并审核输出：

```powershell
$env:PILOT_REAL_DATA = "true"
$env:PILOT_OPERATOR = "<实际操作员标识>"
$env:PILOT_FILE_OBTAINED_AT = "<实际下载时间，例如 2026-10-01T10:00:00+08:00>"
py -m eye_collector.cli pilot `
  --source beijing-open-data-designated-medical-institutions `
  --region 110000 `
  --file C:\secure\beijing-designated-medical-institutions.xlsx `
  --limit 50 `
  --dry-run

py -m eye_collector.cli pilot `
  --source shenzhen-open-data-baoan-hospital-basic-information `
  --region 440306 `
  --file C:\secure\shenzhen-baoan-hospital-basic-information.xlsx `
  --limit 27 `
  --dry-run
```

北京首批导入范围为 50–150 条；先用 `--limit 50` 做审核样本，再依据 dry-run 和人工审核决定是否正式运行。深圳数据集约 27 条，不能为凑足 50 条而复制或合成记录；正式运行按官方文件的实际记录数设置 limit，并在导入后检查全部记录。审核 dry-run 后，删除 `--dry-run` 才会写入。正式导入结果中的 `run_id` 可传给 P3 作精确批次处理：`process --import-run-id <run_id>` 只接受成功且来源仍为 approved + `manual_only` 的批次，并只读取该批次；不指定 ID 时仍只处理 `automated_access_allowed` 来源。migration 010 只给 ETL 运行时增加 `import_runs` 只读权限，不改变来源权限。运行后按 QA 清单人工检查记录；眼科证据不足时必须保持 `unknown`。没有真实文件时，不运行上述导入命令，不以 fixture 代替。

QA 清单：医院名称、地址、区、来源分类、注册/参考 ID、来源 URL、原始字段映射、重复状态和眼科证据状态。北京至少人工抽样 50 条；深圳少于 50 条时检查全部实际记录。检查结果需标明数据文件 SHA-256 与 import run，便于回溯。

可选来源为 `beijing-open-data-hospitals`、`beijing-open-data-designated-medical-institutions` 和 `shenzhen-open-data-baoan-hospital-basic-information`。深圳必须使用 `--region 440306`。北京定点医疗机构文件必须匹配官方 10 列表头，但只映射获准的医院名称、地址、六位所属区行政代码、医院等级、类别和定点机构编码。深圳文件必须匹配官方 17 列表头且选择 `数据集1` sheet；只映射获准业务字段。额外列只参与 schema 校验，不会自动进入 canonical payload。额外、缺失或重复的表头会拒绝整个导入。CSV/XLS/XLSX 都支持；深圳还支持经配置批准的单 XLSX ZIP。文件上限 10 MiB、每次导入上限 150 条，且数据库对本试点三项来源累计最多允许 300 条 source records。深圳原始数据不允许放入 GitHub、原始下载镜像、导出接口或转售。

`OpenDataApiAdapter` 提供通用 JSON API 接口，要求显式配置响应 envelope、完整字段映射、稳定记录键、有界分页以及与数据集页面同源的 HTTPS endpoint；网络请求复用统一 HTTP client 的重试、速率限制、响应体上限和安全日志。它不会自行授予 API 权限，仍须通过现有 Source Approval Gate。当前审核的 P5 数据源都是 `manual_only`，所以 API adapter 尚未启用，也没有配置未经核验的接口或凭据。

北京官方协议要求署名，并要求应用情况备案；深圳要求在成果中注明“深圳市政府数据开放平台”，并在数据被平台下架时停止保存和使用。前端尚未开发时，应把发布前完成署名和相关备案作为发布门禁。眼科状态只有在明确的诊疗科目/科室或 `specialties` 证据文本命中时才记录证据，否则保持 unknown。

## 测试、lint 与类型检查

```powershell
py -m pytest tests -m "not database and not etl_database and not geocode_database" -q
py -m ruff check src tests
py -m mypy src/eye_collector
pwsh -NoProfile -File scripts/test-db.ps1
```

所有网络测试用 `httpx.MockTransport`，CI 不依赖公网真实来源。日志输出结构化字段；不输出请求头、响应体、URL 路径/查询参数或异常原文。
