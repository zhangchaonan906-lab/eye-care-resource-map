# P3 ETL 与候选处理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** 将不可变 `source_records` 转为可追溯、标准化且可复核的候选记录，不发布或合并正式 facility。

**Architecture:** 在现有 `eye_collector` 包中新增隔离的 `etl` 子包；typed Pipeline 组合解析、规范化、明确眼科证据、确定性设施匹配和数据库持久化。Migration 005 增加 candidate 字段、候选 evidence、ETL 最小权限和数据库不变量，P2 API/精确自动采集准入值保持兼容。

**Tech Stack:** Python 3.12、HTTPX/Psycopg 3（仅沿用）、PostgreSQL/PostGIS、pytest、Ruff、mypy、GitHub Actions。

---

## 文件结构

- 新建 `services/collector/src/eye_collector/etl/{__init__.py,models.py,parser.py,normalization.py,evidence.py,matching.py,repository.py,pipeline.py}`：依次承载 ETL 数据类型、显式字段解析、纯文本规范化、规则证据抽取、确定性匹配、SQL 持久化、流程/统计。
- 新建 `services/collector/tests/etl/{test_parser.py,test_normalization.py,test_evidence.py,test_matching.py,test_pipeline.py,test_etl_cli.py}`：单元测试以真实纯函数/组件验证行为，仅在数据库边界使用测试替身。
- 新建 `db/migrations/005_etl_candidates.sql`、`db/tests/005_etl_candidates.sql`、`scripts/provision-etl-login.sql`；修改 `scripts/seed-fixture-source.sql`、`scripts/test-db.ps1`、`scripts/test-db.sh`、`.github/workflows/collector.yml`。
- 新建 `services/collector/tests/etl/test_etl_database.py`、`docs/etl/README.md`；修改 `services/collector/src/eye_collector/cli.py` 增加 `process` 子命令，并为 `services/collector/README.md` 增加 P3 操作说明。

## Task 1 — P3.1 ETL contracts

**Files:** `etl/models.py`, `etl/parser.py`, `tests/etl/test_parser.py`

- [x] 写 RED 测试：合法 raw payload 映射为不可变 ParsedRecord；缺失/空白 name 被跳过；region 只读取显式行政代码键，不从 address 推测；raw payload 输入不被修改。
- [x] 运行 `py -m pytest services/collector/tests/etl/test_parser.py -q`，确认因模块/接口缺失而失败。
- [x] 实现 frozen dataclass `ParsedRecord`，字段包含 `source_record_id`、原始 name/address/phone、显式行政代码、registration ID、院区、原始字段映射与来源 registration ID 可靠标记；`ParseResult` 可明确表示 skip 原因。
- [x] 重跑 parser 测试、`py -m ruff check services/collector/src services/collector/tests`、`py -m mypy services/collector/src/eye_collector`。
- [x] 提交 `feat: define etl source record contracts`。

## Task 2 — P3.2 normalization

**Files:** `etl/normalization.py`, `tests/etl/test_normalization.py`

- [x] RED 测试覆盖 NFKC 全/半角、首尾与重复空白、常见中英标点统一、原文不变、地址不拆行政区、电话数字/分隔符规范和空值保留。
- [x] 运行 normalization 测试观察预期失败。
- [x] 用纯函数实现 name/address/phone 规范化；名称和地址保留 display 原文；电话删除格式分隔符、统一全角数字，并仅对完整国家码前缀作确定性规范；不补写缺失字段。
- [x] 运行 normalization 测试、Ruff、mypy。
- [x] 提交 `feat: normalize candidate text fields`。

## Task 3 — P3.3 ophthalmology evidence extraction

**Files:** `etl/evidence.py`, `tests/etl/test_evidence.py`

- [x] RED 测试：名称中出现“眼科”仍无证据；显式 `ophthalmology_services`、`departments` 或 `department_text` 含眼科值时生成精确原文证据；未出现明确证据返回 unknown；证据包含 source_record ID 和源字段名。
- [x] 运行 evidence 测试确认失败。
- [x] 实现白名单字段与显式词项规则，不调用 LLM，不对缺失/否定/模糊文本猜测阳性；保留精确来源值和原始 field name。
- [x] 运行 evidence 测试与静态检查。
- [x] 提交 `feat: extract explicit ophthalmology evidence`。

## Task 4 — P3.4 candidate schema and persistence

**Files:** `db/migrations/005_etl_candidates.sql`, `db/tests/005_etl_candidates.sql`, `etl/repository.py`, `tests/etl/test_repository.py`

- [x] RED 测试定义所需列、候选唯一 source_record、candidate_evidence 外键、来源回链、ETL 最小权限和 facilities 无写权限；SQL 断言 source_records UPDATE/DELETE 被拒绝。
- [x] 运行 SQL/ repository 测试确认 migration 和实现缺失时失败。
- [x] 新增 migration：规范化字段/处理版本、`candidate_evidence`、source_records 不可变触发器、`eye_etl` NOLOGIN grants；不授予 facility 写权限。
- [x] 使用参数化 SQL 保存 candidate + evidence；唯一冲突不重复写入；单 candidate 事务失败时不留下部分 evidence。
- [x] 在临时 PostGIS 上应用 001–005 migration 和 SQL tests；提交 `feat(db): persist traced etl candidates`。

## Task 5 — P3.5 deterministic matching

**Files:** `etl/matching.py`, `tests/etl/test_matching.py`, `etl/repository.py`

- [x] RED 测试：只有可信 registration ID 可作为注册号强匹配；名称+显式行政代码 exact match；有院区时必须院区 exact match；缺失行政代码不推测；0 命中 unmatched；1 命中 matched；多命中 needs_review；大小写/模糊相似不自动命中。
- [x] 运行 matcher 测试确认预期失败。
- [x] 以只读 facility 查询实现优先级规则；只写 candidate 的 `match_status` 与 `proposed_facility_id`，不写 facilities；registration ID 可靠性来自来源登记元数据。
- [x] 运行 matcher 单测、Ruff、mypy；提交 `feat: add deterministic facility matching`。

## Task 6 — P3.6 duplicate review queue

**Files:** `etl/matching.py`, `etl/repository.py`, migration 005、SQL/单元测试

- [x] RED 测试：按可靠 registration ID 或完整规范名+行政代码(+显式院区)生成 candidate pair；模糊名称不建案；相同输入 fingerprint 固定；duplicate case 提交时少于两个有效 candidate 失败。
- [x] 运行测试确认失败。
- [x] 为 duplicate cases 增加唯一 fingerprint；candidate membership 冲突幂等；用 deferred constraint triggers 强制未删除 case 至少两个成员；建立待复核案时把相关候选设为 `needs_review`。
- [x] 临时 PostGIS 验证 >=2、不足 2、删除 case cascade、重复提交；提交 `feat: add duplicate review queue`。

## Task 7 — P3.7 pipeline and idempotency

**Files:** `etl/pipeline.py`, `etl/repository.py`, `tests/etl/test_pipeline.py`

- [x] RED 测试：按 source_record 执行 parse→normalize→evidence→persist→match；重复执行不重复 candidate/evidence/case；失败记录计数并继续；统计含读取、创建、已处理、跳过、证据、匹配、待复核、重复案和错误；原 raw JSON 在运行前后完全一致。
- [x] 运行 pipeline 测试观察失败。
- [x] 实现按快照读取的可注入 Pipeline；每个快照在单个数据库事务中完成 candidate/evidence/duplicate 更新；唯一 source_record 冲突计 already_processed；只读取批准来源且未处理快照。
- [x] 运行完整 ETL unit tests、Ruff、mypy；提交 `feat: orchestrate idempotent etl pipeline`。

## Task 8 — P3.8 access policy migration and database integration

**Files:** `db/migrations/005_etl_candidates.sql`, `db/tests/005_etl_candidates.sql`, `scripts/provision-etl-login.sql`, `scripts/seed-fixture-source.sql`, `tests/test_etl_database.py`, `scripts/test-db.ps1`, `scripts/test-db.sh`

- [x] RED 集成测试：P2 旧策略值 automated/manual 保持语义；未知/null 迁移为人工复核且 P2 fail closed；新 CHECK 拒绝未知写入；P2 collector 登录继续运行；ETL 登录不能 update/delete source_records、不能写 facilities。
- [x] 从空 PostGIS 执行迁移和测试确认当前失败。
- [x] Migration 回填 null/未知 policy 为 `manual_review_required`，设置安全默认、NOT NULL、枚举式 CHECK，保留 P2 `automated_access_allowed` 精确值和现有 P2 查询字段；添加可信 registration ID 来源标志默认 false。
- [x] 为 ETL 创建独立 runtime login；用 admin URL 仅准备 synthetic Fixture source_records；用最小权限 ETL URL运行集成测试，验证回链、匹配、重复队列、immutable snapshots 和重复执行。
- [x] 运行 `pwsh -NoProfile -File scripts/test-db.ps1`，确认 P1/P2/P3 SQL 与 DB tests 全通过；提交 `test(db): cover etl permissions and idempotency`。

## Task 9 — P3.9 CLI and CI

**Files:** `services/collector/src/eye_collector/cli.py`, `tests/etl/test_etl_cli.py`, `.github/workflows/collector.yml`, DB scripts

- [x] RED 测试 process 子命令的 limit、region、数据库配置和结果 JSON；Collector run 命令行为保持不变。
- [x] 运行 CLI tests 确认 process 未实现时失败。
- [x] 加入 `eye-collector process --limit N`；从独立 ETL URL 创建 repository，不允许用户传入生产 source URL；结构化输出 pipeline counts。CI 安装后运行 ETL unit、PostGIS/P1/P2/P3 DB tests、lint、typecheck、diff check。
- [x] 本地运行 workflow 相同命令、解析 YAML、Bash syntax，并提交 `ci: verify etl candidate pipeline`。

## Task 10 — P3.10 docs and release verification

**Files:** `docs/etl/README.md`, `services/collector/README.md`, P3 spec/plan

- [x] 文档测试核对 process 用法、来源 policy、规范化映射、证据来源字段、匹配优先级、review 语义和明确禁止项。
- [x] 写清 P2 access policy 回填/默认/枚举兼容行为、迁移执行步骤、ETL 最小权限、dry/limit 限制及合成测试数据范围。
- [x] 运行完整 CI 等价测试，检查迁移空库、权限、source_records 不可变、重复执行、CI 通过、`git diff --check origin/main...HEAD`、干净状态与提交序列。
- [x] 确认没有真实来源采集、facility 发布/合并、LLM、geocoding、地图或 Nearby 逻辑；推送 `p3-etl-normalization` 并创建标题 `建立 P3 ETL 与候选数据处理流水线` 的 main PR。
- [x] 等待 GitHub CI 通过并按 P3 STATUS 模板报告。
