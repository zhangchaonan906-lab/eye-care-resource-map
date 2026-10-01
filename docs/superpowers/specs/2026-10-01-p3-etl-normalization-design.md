# P3 ETL 与候选处理设计

**状态：** 按用户给出的 P3 范围执行；仅处理合成 Fixture 快照，不采集生产数据。

## 目标和边界

从 P2 `source_records` 构建可重复、可审计的 ETL：解析原始字段、规范化文本、从来源明确字段提取眼科证据、生成与原快照关联的 `candidate_records`，执行确定性设施匹配，并把候选间可能重复的关系放入人工复核队列。任何步骤都不创建、合并、更新或发布 `facilities`。原始 `source_records` 在数据库层禁止 UPDATE/DELETE。

## 组件与数据流

- `services/collector/src/eye_collector/etl/` 提供 typed records、Parser、Normalizer、EvidenceExtractor、DeterministicMatcher、ETL repository 和 `Pipeline`。Pipeline 逐快照处理，在每个快照的事务中写 candidate 与 evidence；同一 `source_record_id` 通过数据库唯一约束保持一条 candidate。
- Repository 只读取获准来源的 `source_records` 和必要的 facility 匹配字段。candidate 与 evidence 保存原文、规范化字段、来源快照 ID、处理版本和匹配结论。证据保存在独立 `candidate_evidence`，字段包含 candidate ID、source_record ID、源字段名、精确摘录与证据类型。
- Parser 只读显式映射字段，不改 raw JSON。缺少名称时跳过并统计，不猜字段、不从地址补全行政区。
- 名称规范化使用 Unicode NFKC、trim、连续空白折叠和显式常见标点映射；原文另存。地址仅做相同文本清洗，不解析地址组件、不推断地区、不调用地图/地理服务。电话仅规范数字和分隔符，并保留原值。
- EvidenceExtractor 只检查明确的 `ophthalmology_services`、`departments`、`department_text` 等被许可来源字段；精确来源字段和值存证。医院名称不参与证据抽取。无证据为 unknown，不推断阴性或阳性；无 LLM。
- Matcher 的优先级为：来源明确标记可信的 registration ID 精确匹配；规范名称+显式行政代码精确匹配；当来源提供院区时再要求院区精确一致。仅唯一命中时设置 `matched` 和 `proposed_facility_id`。零命中为 unmatched，多命中或候选碰撞为 needs_review。没有模糊分数、相似度或自动合并。
- 候选间以可信 registration ID 或完全相同的规范名称+显式行政代码(+来源提供的院区)形成确定的 review pair。duplicate case 指纹由规则和候选 ID 排序后计算，保证重复执行不重复建案。延迟约束在提交时保证每个存在的 case 至少关联两个候选。
- 结构化结果统计读取、创建、已处理、跳过、证据、唯一匹配、待复核、重复案、错误数量。`process` CLI 限制到批准来源和可选 limit；不触及 P2 ingest 流程。

## Schema 与访问策略

- Migration 005 添加 candidate 规范化列/处理版本、`candidate_evidence`、duplicate case 指纹和最少两个成员的延迟约束、`eye_etl` NOLOGIN 权限角色，并拒绝修改/删除 `source_records`。ETL runtime 不获得 facilities 写权限或来源审批权限。
- `source_catalog.access_policy` 目前允许自由文本，P2 只对精确 `automated_access_allowed` 放行。Migration 将空值和未知旧值保守改为 `manual_review_required`，为列设置同一默认值、NOT NULL 和已知值 CHECK。保留 P2 使用的列名及 `automated_access_allowed` 字符串；该字符串的含义不变，其他值仍被 P2 拒绝。已有 `manual_only` 保持不变。
- 原始值仍由 P2 collector 写入，P3 ETL 是独立最小权限 runtime；数据库集成测试用 admin URL 准备合成快照，再用非 superuser ETL 连接运行 pipeline。

## 幂等和失败处理

每条 snapshot 独立处理；已存在 candidate 只计为 already_processed，不重复写 evidence/duplicate memberships。任何单条失败回滚该快照事务并计入错误，处理继续；明确保存错误类型/记录 ID，不将原始 payload 或 secrets写入日志。候选、evidence 和新 review memberships 在事务中一致提交。source_records 保持不变。

## 验证

Unit tests 覆盖 Unicode/全半角、空白/标点、电话、原文保留、不推断行政区、名称不能触发眼科证据、明确字段证据、匹配优先级/歧义、case 指纹和结果统计。PostGIS 集成测试验证 source_record 外键、candidate 唯一、原始快照不可修改、最小权限、facility 不可写、确定性匹配、复核队列两个成员、重复运行不产生新增 candidate/evidence/case。CI 同时运行 P1/P2 与 P3 测试及静态检查，数据只来自 Fixture。

## 明确不做

不连接真实生产数据源、不做全国批量采集、不做 P4 facility 发布/合并审核、不使用 LLM、不做模糊匹配、geocoding、WGS84/GCJ-02、地图或 Nearby API。
