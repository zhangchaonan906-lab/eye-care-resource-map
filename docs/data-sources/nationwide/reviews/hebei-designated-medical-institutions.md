# 河北“定点医疗机构信息表”来源资格审查

审查日期：2026-10-01。P6-B2 补充检索记录时间为 2026-10-01 21:27（Asia/Shanghai）。结论维持 `UNKNOWN`；未取得或下载文件，未导入数据。

## 官方证据

| 事实 | Official statement | 项目解释 | 证据 |
|---|---|---|---|
| 候选数据目录记录 | 京津冀公共数据协同页列出“河北省医疗保障局—定点医疗机构信息表”，页面有数据下载入口，并展示河北省公共数据开放平台入口 | 这是政府开放平台协同目录中的候选线索，不是河北源数据集详情页；不能单凭目录下载操作给当前项目授予权利 | [京津冀公共数据协同目录](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm)，页面标题“京津冀协同发展公共数据开放专区”，访问日期 2026-10-01 |
| 河北数据平台 | 协同页展示河北省公共数据开放平台名称并链接到 `http://hebdata.hebyun.gov.cn/home` | 2026-10-01 21:27（Asia/Shanghai）对 HTTP 首页发普通 HEAD 请求返回 502；HTTPS 首页 TLS/SSL 握手失败，未获得 HTTP 状态码。没有获取到页面标题/主体、当前 dataset detail 或条款。未尝试绕过访问限制 | 协同目录同上；直接首页可用性检查日期/时间见记录 |
| 搜索到的目录线索 | 河北政府、河北省数据和政务服务局、河北省医保及公共数据开放平台的公开索引检索未定位到该具体数据集的河北官方详情页；京津冀目录仍列有候选项 | 外省协同目录可证明存在候选记录，不能证明河北原始发布位置、下载权或项目使用权。已准备人工询问函 | [来源位置询问函](../outreach/hebei-source-location-request.md)，检索和可用性记录截至 2026-10-01 |
| 数据开放审批背景 | 河北省数据和政务服务局关于公共数据资源授权运营场景的官方通知要求按场景提供所需数据名称/字段等，并由主管部门评审；同时描述河北授权运营模式 | 该通知证明部分公共数据利用需按场景审批，但未明确此候选目录项适用哪种开放类别，也不能替代该数据集自己的协议 | [河北省数据和政务服务局公告](https://gxt.hebei.gov.cn/main/policy/sbtzdetail?id=a73c8df1-e5ae-4432-920f-992355706415)，标题“关于征集第二批公共数据资源授权运营应用场景及经营主体的公告”，访问日期 2026-10-01 |
| 医保定点语义 | 国家政务公开内容将定点医疗机构描述为与医保部门签订服务协议、医保服务可结算的机构 | 即使未来确认是省级目录，也只表示医保定点类别；不等于河北所有依法执业医疗机构 | [国务院客户端说明](https://app.www.gov.cn/govdata/gov/202207/04/486859/article.html)，标题“医保定点医院、定点药店，一键查询”，访问日期 2026-10-01 |

## 权利与获取评估

| 项目 | 评估 | 依据/不确定性 |
|---|---|---|
| `source_status` | UNKNOWN | 官方协同目录虽列来源名和提供方，但源平台的该数据集页面、开放属性和协议未确认。 |
| `access_policy` | unknown | 未确认是公开直接下载、需注册、申请开放、查询服务还是其他授权路径。 |
| `data_use_allowed` | UNKNOWN | 没有找到该具体数据集的官方授权/开放协议。 |
| `internal_processing_allowed` | UNKNOWN | 未找到具体政策依据。 |
| `long_term_storage_allowed` | UNKNOWN | 未找到保留期限或已获取副本处理约定。 |
| `reuse_allowed` | UNKNOWN | 目录入口不等于再使用授权。 |
| `app_display_allowed` | UNKNOWN | 没有适用于项目地图的展示许可。 |
| `raw_transfer_allowed` / `raw_redistribution_allowed` | UNKNOWN | 未找到条款。 |
| `attribution_required` | UNKNOWN | 具体 attribution text 未找到。 |
| `commercial_use_restrictions` | UNKNOWN | 未找到具体条款；省级授权运营通知不能直接套用为此数据集许可。 |
| `retention_restrictions` / `withdrawal_handling` | UNKNOWN | 未找到。 |

## 范围与资格决定

- **Authoritative source found: NO（数据集的河北原始发布详情页未定位/不可访问）。** 已发现的北京协同目录只是官方目录转引，不能取代河北来源页。
- `coverage: unknown`。目录列出的来源是“定点医疗机构”，范围/统计口径/更新时间和字段都未取得。医保定点机构不等于全体医疗机构。
- `source_status: UNKNOWN`；`access_policy: unknown`；`Ready For Pilot: NO`。
- Blocking issues：取得可访问的河北官方源平台详情页；由河北医疗保障局/平台确认 dataset scope、协议、字段、格式、记录数、更新频率、注册/申请步骤、存储/应用展示/归因/保留和撤回处理。不得以第三方镜像补齐。

## 文件/Schema

- `File Obtained: NO`; `Schema Inspected: NO`。
- filename / SHA-256 / size / sheet / headers / rows / source_updated_at：未产生。
- 目录下载按钮不作为批准依据；本阶段不从北京协同目录下载。

## 官方页面清单

1. [京津冀公共数据协同目录](https://data.beijing.gov.cn/jjjxtsjkfzt/index.htm)，北京市公共数据开放平台，访问日期 2026-10-01。
2. [河北数据和政务服务局授权运营场景征集公告](https://gxt.hebei.gov.cn/main/policy/sbtzdetail?id=a73c8df1-e5ae-4432-920f-992355706415)，河北省数据和政务服务局，访问日期 2026-10-01。
3. [医保定点医院、定点药店，一键查询](https://app.www.gov.cn/govdata/gov/202207/04/486859/article.html)，国务院客户端，访问日期 2026-10-01。
