# 浙江“二级及以上医疗机构基本信息”来源资格审查

审查日期：2026-10-01。只审官方平台页面和官方协议模板。未提交申请、未取得授权、未取得或下载文件。

## 官方证据

| 事实 | Official statement | 项目解释 | 证据 |
|---|---|---|---|
| 候选和流程 | 浙江·数据开放平台精选项显示“数据使用申请—二级及以上医疗机构基本信息”，条目时间显示 2025-01-03 | 必须走数据使用申请。页面未向本次审查提供可验证的 dataset-specific 文件/字段详情 | [浙江·数据开放平台](https://data.zjzwfw.gov.cn/dopServer/index.html)，页面标题“浙江·数据开放网站”，访问日期 2026-10-01 |
| 协议主体和范围 | [受限开放协议](https://data.zjzwfw.gov.cn/dopServer/static/agreement/%E6%B5%99%E6%B1%9F%E7%9C%81%E6%95%B0%E6%8D%AE%E5%BC%80%E6%94%BE%E5%B9%B3%E5%8F%B0%E5%8F%97%E9%99%90%E5%BC%80%E6%94%BE%E5%8D%8F%E8%AE%AE.pdf)是开放主体与利用主体之间的框架；具体数据以申请表和需求清单为准 | 取得资格绑定到具体主体、数据字段/范围和应用方案；通用模板不等于本项目已获权 | 协议第 1 节，PDF 页 1，访问日期 2026-10-01 |
| 具体用途 / 应用 | 协议把使用限定在申请中指定的平台/系统/app 和应用服务，要求进一步约定服务内容；应用项目细节要在方案中确认 | 项目地图必须按真实项目名称、场景、字段和输出方式申请；未获批前不能把数据放入 app 或用于公开展示 | 协议第 1–2 节，PDF 页 1–2，访问日期 2026-10-01 |
| 原始数据转移 | 协议要求不以任何方式把相关原始数据提供给未授权第三方 | 原始数据对外提供/转移/再分发默认禁止，只有授权主体/具体批准条款可改变 | 协议第 2 节“数据安全保障”，PDF 页 3，访问日期 2026-10-01 |
| 期限、终止和销毁 | 协议有效期、终止通知提前期和协议终止后数据销毁期限使用待填字段；协议可终止/续签，违规可关闭访问并终止服务 | 保留期间和撤回后的删除处置必须在项目批准协议中填写，不能从模板假设长期留存 | 协议附则第 3 节，PDF 页 4–5，访问日期 2026-10-01 |
| 署名 | 对论文、专利、出版、软件著作权、应用产品中参考/引用数据，要求注明所引用的公共数据 | 未来应用需使用数据提供方指定的具体 attribution；提供主体和署名格式仍待 dataset-specific application 确认 | 协议第 2 节“数据专项用途”，PDF 页 1，访问日期 2026-10-01 |

## 逐项权利评估

| 项目 | 当前结论 | 官方依据/限制 |
|---|---|---|
| `source_status` | UNKNOWN | 本项目未申请/签约/获批。 |
| `access_policy` | application_required | 数据平台条目显示使用申请，受限开放协议规定具体申请表/需求清单。 |
| application approved | NO | 未提交申请；不代用户拟造用途或自动申请。 |
| `data_use_allowed` | 仅在批准后、申请约定范围内 | 未获批前没有本项目数据使用权。 |
| `internal_processing_allowed` | 需在具体申请/方案中确认 | 框架协议没有预授予任意内部处理或二次加工权。 |
| `long_term_storage_allowed` | UNKNOWN / pending project-specific term | 协议将有效期和终止后销毁时限留空；不能认定长期留存。 |
| `reuse_allowed` | 仅限批准的数据清单和专项用途 | 不能将一个应用审批扩大到其他项目/产品。 |
| `app_display_allowed` | 未批准；需指定 app/service 后审批 | 协议把应用主体、平台和服务作为具体授权内容。 |
| `raw_transfer_allowed` | 未授权第三方：NO | 原始数据不得提供给未授权第三方。 |
| `raw_redistribution_allowed` | NO absent explicit authorization | 框架协议不授予 raw redistribution。 |
| `attribution_required` | YES when using/referencing data in listed outputs | 具体署名文本待数据主体/申请确认。 |
| `commercial_use_restrictions` | UNKNOWN pending project-specific review | 框架协议不是通用商业许可；场景与服务内容需审定。 |
| `retention_restrictions` | YES, case-specific duration must be filled | 终止后应按协议期限销毁数据；模板期限未填写。 |
| `withdrawal_handling` | partly defined, project detail missing | 违规可关闭获取权限/终止服务；协议终止后销毁期限要约定；平台撤回来源时的存量处理还需明确。 |

## 范围与资格决定

- **Official Provider:** 平台条目本次可见为省级平台精选项，但数据提供主体/部门的 dataset-specific detail 未核实。
- **Coverage:** 地域范围未核实；标题只说明“二级及以上”机构类别，不代表浙江所有医疗机构。
- **Source Status:** `UNKNOWN`。
- **Access Policy:** `application_required`。
- **Ready For Pilot:** **NO**。
- 阻塞项：由用户/合法项目主体按真实用途提交申请；获取开放主体书面批准和签署的项目具体协议；确定数据清单、区域、字段、系统/app、展示范围、处理、存储期限、商业用途、原始数据访问边界、归因文本、终止/撤回后的销毁时间和责任人。批准后方可取文件并 inspect。

## 文件/Schema

- `File Obtained: NO`; `Schema Inspected: NO`。
- filename / SHA-256 / size / sheet / headers / rows / source_updated_at：未产生。
- API/格式/登记要求：除“数据使用申请”外均未在 dataset-specific 页面验证；获批前不尝试访问文件或 API。

## 官方页面清单

1. [浙江·数据开放平台](https://data.zjzwfw.gov.cn/dopServer/index.html)，访问日期 2026-10-01。
2. [浙江省数据开放平台受限开放协议](https://data.zjzwfw.gov.cn/dopServer/static/agreement/%E6%B5%99%E6%B1%9F%E7%9C%81%E6%95%B0%E6%8D%AE%E5%BC%80%E6%94%BE%E5%B9%B3%E5%8F%B0%E5%8F%97%E9%99%90%E5%BC%80%E6%94%BE%E5%8D%8F%E8%AE%AE.pdf)，访问日期 2026-10-01。
