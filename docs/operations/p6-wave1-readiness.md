# P6 Wave 1 来源就绪审查

审查日期：2026-10-01。Wave 1 为优先做来源审查的候选，不代表来源已批准。当前所有候选 `Ready For Pilot: NO`；未完成权利评审前不得下载导入或自动访问。

## Wave 1: 天津

- **Source:** 天津市信息资源统一开放平台，“三级医疗机构基本信息”；[数据集页](https://open.data.tj.gov.cn/sjj/1be22c6e54be4f3e85989bc60ae28bd8.htm)
- **Legal/Policy Status:** 页面标注“无条件开放”；该标签不充分证明长期存储、产品展示、原始转移/再分发。需检查平台声明、数据集协议以及署名要求。
- **Acquisition:** 页面列 XLS 下载项；目前不自动请求或下载。核实是否要求账户、下载条款和可复现下载后，由操作员按许可取得。
- **Expected Schema:** 官方摘要明确名称、地址、邮编、区（县）；附件可见“基本信息”2026-08-20及旧版本。实际 headers、行政区代码、机构类别、行数和空值需 inspect。
- **Expected Records:** 官方页面未显示行数；不预估。
- **Pilot Size:** 权利/文件/schema 审核通过后优先 50–150 行；若文件总量少于 50 则使用全部真实记录。
- **QA Size:** 至少人工 QA 50 条；总行数小于 50 时检查全部。
- **Special Risks:** 仅三级医疗机构，不能代表所有医院/诊所；行政区县字段可能是文本；最新附件新旧更新内容需确认；坐标信息不作为可信边界来源。
- **Attribution:** 数据集/平台要求待审；导入前记录官方要求。
- **Retention:** 待具体协议复核；来源撤回或下线后的处置待确认。
- **Adapter Needed:** 现有 `OpenDataFileAdapter` 已支持 CSV/XLS/XLSX。附件为 XLS 时使用现有解析/预检路径；不新写 adapter，除非真实文件格式/schema 暴露已批准的必要缺口。
- **Ready For Pilot:** **NO** — 缺少权利审查、官方文件与 schema inspect。

## Wave 1: 河北

- **Source:** 协同目录列出的“定点医疗机构信息表”，提供方河北省医疗保障局；[京津冀公共数据协同目录](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm)
- **Legal/Policy Status:** 目录中出现下载入口，但本次未定位到权威源平台的具体数据集协议/条款；所有存储、再使用、产品展示、转移、归因和保留条件未知。
- **Acquisition:** 先定位河北省数据平台或医保局源页；不可把北京聚合目录作为足够授权。未找到源页前不下载。
- **Expected Schema:** 未核实。不得从数据集名称推断机构名、地址、等级、行政区、医保编码等字段。
- **Expected Records:** 未核实。
- **Pilot Size:** 获得许可且通过 schema inspect 后 50–150 条；数据总量少于 50 则用全部真实行。
- **QA Size:** 至少 50 条；小于 50 条则全量 QA。
- **Special Risks:** 医保定点资格不是医疗机构全集；源平台与协同目录的记录同步/更新时间未知；可能需要注册或申请。
- **Attribution:** 未核实。
- **Retention:** 未核实；需明确来源撤回后的快照、派生候选及 QA 记录处置。
- **Adapter Needed:** 暂不判断。文件确定为 CSV/XLS/XLSX 可复用现有适配器；分页 API/其他封装只提交设计审查。
- **Ready For Pilot:** **NO** — 缺少原始来源页面、许可与 schema。

## Wave 1: 浙江

- **Source:** 浙江省公共数据开放平台精选项“二级及以上医疗机构基本信息”；[官方平台](https://data.zjzwfw.gov.cn/dopServer/index.html)
- **Legal/Policy Status:** 条目明确显示“数据使用申请”。平台提供[受限开放协议](https://data.zjzwfw.gov.cn/dopServer/static/agreement/%E6%B5%99%E6%B1%9F%E7%9C%81%E6%95%B0%E6%8D%AE%E5%BC%80%E6%94%BE%E5%B9%B3%E5%8F%B0%E5%8F%97%E9%99%90%E5%BC%80%E6%94%BE%E5%8D%8F%E8%AE%AE.pdf)，要求具体申请且可约束成果使用/提供；尚未获批。
- **Acquisition:** 按平台正式流程提交用途申请；获得数据提供主体书面批准后，由获准用户下载。不得自动申请、复用账号或绕过限制。
- **Expected Schema:** 当前页面搜索项没有完整字段字典；名称、地址、行政代码、医院级别、注册号、眼科字段和坐标均待批准后检查。
- **Expected Records:** 未核实。
- **Pilot Size:** 申请批准、文件 inspect 与 dry-run 审核后 50–150 条；如文件少于 50 则全部真实记录。
- **QA Size:** 至少人工 QA 50 条；不足 50 全量 QA。
- **Special Risks:** “二级及以上”不含低级别机构；具体地域是否省级全域未核实；申请协议可能限制数据存储、派生、展示、对外提供及保留。
- **Attribution:** 以获批的具体协议为准，导入前写入 source review。
- **Retention:** 以具体申请协议为准，确认撤回、期限、下线及删除要求。
- **Adapter Needed:** 暂无。审批后优先检查下载格式是否被已有 CSV/XLS/XLSX 适配器支持；不提前实现。
- **Ready For Pilot:** **NO** — 尚未申请/取得批准，字段、覆盖和文件均未核实。

## 统一导入闸门

每个 Wave 1 来源独立完成下列材料后再申请进入 pilot：

1. 官方源平台/主体和数据集具体页面；当前协议及逐项权利决定（自动/人工获取、处理、持久化、应用展示、原始转移/再分发、归因、保留和撤回）。
2. 经允许取得的原始文件及 SHA-256、文件大小、取得时间、获取人/方法、数据集页面、源更新时间和 import run provenance。
3. 本地 inspect：格式、headers、行数、批准地区、预期 schema、schema match 和限额；inspect 不写数据库。
4. dry-run 结果经人工审阅后才可另行授权真实导入。无权利依据、schema 不匹配、越区、超限或需绕过访问控制时 fail closed。
5. P3 ETL 保留原始记录不可变和来源可追溯；QA 抽样逐行检查名称、地址、区县、来源分类、注册/参考 ID、source URL、原始字段映射、重复状态、眼科证据状态。证据不足为 `unknown`。

## 通用阶段约束

- P6-A 没有真实数据导入；不运行新 pilot、不调用真实 geocoder、不存 production coordinates、不发布 facility。
- 全国名录、国家医保定点查询和卫健委分类查询不可直接视为完整/等价来源。
- 未来 coverage 汇报必须以“地区+来源+具体 import run+QA 状态”为粒度；不能因有来源页而显示已导入或已 QA。
