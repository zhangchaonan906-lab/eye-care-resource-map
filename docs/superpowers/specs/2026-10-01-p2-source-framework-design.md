# P2 数据来源采集框架设计

**状态：** 已按 P2 执行请求确定；本阶段不接入真实生产来源。

## 目标与边界

建立安全、可审计、可重试、可幂等的数据采集核心。流程为：已登记来源 → 策略准入 → 创建 `import_runs` → 适配器分页取原始记录 → canonical SHA-256 → `source_records` 快照 → 结构化统计与终态。Fixture 是唯一内置适配器。没有来源适配器负责清洗、标准化、实体匹配、眼科判断、地址处理、坐标或发布。

## 组件

- `services/collector` 是独立 Python 3.12 包；同步接口便于 CLI 与测试控制中断和依赖注入。
- `SourceAdapter` 暴露稳定 adapter key、目录元信息、请求限速配置、分页 fetch/record iteration 和原始 record key/URL/payload。网络适配器只依赖统一 `HttpClient`。
- `SourcePolicy` 从 P1 `app_private.source_catalog` 读取来源。必须同时满足 `status=approved`、有 `use_basis`、非空 `permitted_fields`、`access_policy=automated_access_allowed`；否则在创建 run 前拒绝。记录字段超出许可集合时整条拒绝，不裁剪原始 payload。原始详情 URL 必须与已批准目录 URL 使用同一 HTTPS origin。验证码、登录、付费墙、明确禁止自动访问或 robots 不允许均视为阻断；不尝试绕过。
- `PostgresRepository` 集中执行 SQL。串行化事务先读取和验证来源，再以 `INSERT ... SELECT ... WHERE status='approved'` 创建 `import_runs`；这样不要求 collector 具有修改来源审批状态的权限。`source_records` 使用 P1 唯一约束和 `ON CONFLICT DO NOTHING RETURNING` 实现幂等。run 只允许从 `running` 转到 `succeeded`、`failed` 或 `cancelled`。
- canonical hash 用 JSON UTF-8、排序键、紧凑分隔符、拒绝 NaN/Infinity 进行 SHA-256。原始 payload 不经业务字段变换。
- `HttpClient` 使用 HTTPX，同一来源独立限速；超时、连接错误、429、500/502/503/504 最多重试 4 次，指数退避加 jitter；其他 4xx 不重试。sleep、clock、random、transport 可注入。响应大小、timeout、User-Agent 均受配置限制。
- Fixture adapter 使用本地 JSON fixture 和 HTTPX mock transport，覆盖多页、重复快照、可变 snapshot、429、500、timeout；不会请求公网。
- CLI 提供 `run --source fixture --region 110000 [--dry-run] [--limit N]`。Dry run 会执行批准检查并创建/关闭审计 run，但不写 `source_records`；counts 的 `inserted` 表示预估新快照数。
- 日志为结构化字段，包含 run/source/region/source key、请求尝试、HTTP 状态和事件；禁止记录请求头、响应体、URL 路径/查询参数、异常原文和 secrets；异常摘要经过脱敏后才写日志和数据库。

## Schema 与权限

不修改 P1 业务模型：使用 `source_catalog`、`import_runs`、`source_records` 及其既有外键、约束和唯一键。P2 添加只包含 collector 所需表权限的 `NOLOGIN` 数据库角色，并给运行时连接预留单独登录角色；数据库测试经最小权限角色执行 collector SQL，源登记由测试管理员准备。不会把运行时 repository 绑定到 PostgreSQL superuser。

## 验证

单元测试覆盖准入状态、字段许可、规范 hash、重试/不重试、限速时序、日志脱敏、Fixture 分页和 runner 失败/中断关闭。PostGIS 集成测试使用临时数据库与非 superuser collector 连接，验证 run 状态、快照外键和相同/变化内容的幂等。CI 无公网数据源，运行 unit、lint、typecheck、P1/P2 数据库检查和 diff check。

## 风险与限制

P1 将 `access_policy` 存为自由文本；P2 采用精确值 `automated_access_allowed` 作为 fail-closed 机器判定，其他文本均阻断。具体真实来源的许可、robots 与频率仍须人工审核，本阶段不作法律许可推断。没有实现 P3 及之后任何医院生产处理或地图功能。
