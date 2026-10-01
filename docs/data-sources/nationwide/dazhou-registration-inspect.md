# P6-N2 / P6-N2B 达州医疗机构来源只读检查

检查日期：2026-10-02
状态：P6-N2 原始下载为 `BLOCKED_BY_OFFICIAL_REDIRECT_ERROR`（由用户确认）；P6-N2B 已核验官方详情页与公开 XLS 预览，但原始文件尚未下载，文件级 inspect 受阻。

本页分别记录两个独立数据集，不共享文件、字段核验或眼科统计。

## 官方来源元数据

### A. 达州市医疗机构执业登记信息（P6-N2）

- Acquisition Status：`BLOCKED_BY_OFFICIAL_REDIRECT_ERROR`
- Reason：官方正常下载流程跳转至错误 callback URL，浏览器返回 `ERR_INVALID_REDIRECT`（本项为用户确认的事实）。
- 只标记 file acquisition blocked；不标记 source rejected 或 dataset unavailable。
- 保留本数据集原有 4,018 条等页面元数据，不能与下方 81 条许可证数据集合并统计。

此前 A 项的下载尝试说明、4,018/1,000 页面数据及其数据字典仅属于本节的登记信息来源，不应用到许可证来源。

### B. 达州市医疗机构执业许可证（P6-N2B）

- Dataset Name：达州市医疗机构执业许可证
- Provider：达州市卫生健康委
- Official URL：[达州公共数据开放网数据集详情](https://www.dazhoudata.cn/oportal/catalog/a9865122f8d742c6934783ca92181728)
- Open Status：无条件开放
- Published At：2025-11-04 14:58:28
- Updated At：2026-08-14 16:04:57
- Update Frequency：每年
- Displayed Records：81
- API Available：YES（详情页提供 API 服务入口；本阶段没有调用 API）
- Application Required：页面未显示申请条件；详情页标注无条件开放。
- Login Required：UNKNOWN；页面显示登录/注册入口，但尚未能通过浏览器正常点击下载控件确认是否要求登录。

#### B 官方附件列表

| Filename | Format | File Date | Displayed Size |
|---|---|---|---:|
| `达州市医疗机构执业许可证_0.xls` | XLS | 2023-11-30 | 56 KB |
| `达州市医疗机构执业许可证_0.csv` | CSV | 2023-11-30 | 38.131 KB |
| `达州市医疗机构执业许可证_0.json` | JSON | 2023-11-30 | 58.604 KB |
| `达州市医疗机构执业许可证_0.xml` | XML | 2023-11-30 | 78.223 KB |
| `达州市医疗机构执业许可证_0.rdf` | RDF | 2023-11-30 | 80.355 KB |

页面未列 XLSX。详情页虽称直接文件包最多包含前 1,000 条，但页面总量为 81；未取得文件前不声称本地文件完整或实测 81 行。

#### B 官方数据字典与公开预览

官方数据字典列有 10 项；XLS 预览页可公开访问，显示以下预览列代码。它是官方网页预览，不是已下载原始工作簿，不能据此报告文件行列数、SHA-256 或宏/工作表检查。

| Preview Code | Official Field Name |
|---|---|
| `jgmc` | 机构名称 |
| `djh` | 登记号 |
| `jgdz` | 机构地址 |
| `xzqh` | 行政区划 |
| `syzxs` | 所有制形式 |
| `jglb` | 机构类别 |
| `jyxz` | 经营性质 |
| `cws` | 床位数 |
| `yys` | 牙椅数 |
| `zlkmmc` | 诊疗科目名称 |

- Official Page Key Fields：官网数据字典列出机构名称、机构地址、诊疗科目名称、行政区划、登记号、机构类别、所有制形式等字段。
- Exact Raw Headers：未验证；当前仅有网页预览代码与数据字典。
- Raw Rows With Eye Evidence / Distinct Normalized Eye Names：未统计；不能把网页预览当成下载文件统计。
- File Acquisition Status：下载控件尚未由正常浏览器点击；没有确认成功，也没有观察到 `ERR_INVALID_REDIRECT`。
- Acquisition Status：`FILE_ACQUISITION_NOT_COMPLETED`
- Redirect Error：`UNKNOWN`（未实际完成下载操作，不能归因于 A 来源的重定向错误）
- Portal Login / Application Requirement for Download：未验证。

#### B 浏览器操作限制

当前会话浏览器交互初始化失败，无法对页面可见的 XLS 下载控件执行普通点击。本阶段没有重试 A 来源，也没有猜测或调用隐藏接口、绕过登录/验证码或使用第三方来源。B 来源的下载结果因此保持未验证，不得写成 ERR redirect、门户拒绝或数据集不可用。

- Dataset Name：达州市医疗机构执业登记信息
- Provider：页面显示“市卫健委”
- Official URL：[达州公共数据开放网数据集详情](https://www.dazhoudata.cn/oportal/catalog/40f1da7987464008a6d8da0735360d59)
- Open Status：无条件开放
- Update Frequency：每年
- Published At：2026-03-25 16:14:59
- Dataset Updated At：2026-08-14 16:04:57
- Displayed Record Count：4,018 条
- Preview：数据预览注明全量 4,018 条、仅展示前 30 条
- API Available：YES；页面有“API服务”入口，并提示全量数据通过 API 获取。本阶段未调用 API。
- Application Required：页面未显示申请条件；开放状态标注“无条件开放”。
- Login Required：UNKNOWN；页面可见登录/注册入口，但本次未能通过浏览器点击下载控件，无法验证直接下载是否强制登录。

## A 来源文件列表（P6-N2；仅记录页面元数据）

详情页列出的文件及显示信息如下。页面说明每个直接下载文件包仅包含前 1,000 条；未单独显示每个文件的实际行数。

| Filename | Format | File Date | Displayed Size | Displayed Row Count |
|---|---|---|---:|---|
| `达州市医疗机构执业登记信息_0.xls` | XLS | 2022-07-29 | 202.5 KB | 未单列；文件包仅含前 1,000 条 |
| `达州市医疗机构执业登记信息_0.csv` | CSV | 2022-07-29 | 142.139 KB | 未单列；文件包仅含前 1,000 条 |
| `达州市医疗机构执业登记信息_0.json` | JSON | 2022-07-29 | 246.196 KB | 未单列；文件包仅含前 1,000 条 |
| `达州市医疗机构执业登记信息_0.xml` | XML | 2022-07-29 | 371.814 KB | 未单列；文件包仅含前 1,000 条 |
| `达州市医疗机构执业登记信息_0.rdf` | RDF | 2022-07-29 | 478.338 KB | 未单列；文件包仅含前 1,000 条 |

页面对 XLSX 没有列出附件。按用户规定的优先级，若能够经官方页面正常下载，应优先取 XLS；本次没有下载任何文件。

## A 来源 4,018 与下载包范围

- Displayed Platform Total：4,018
- 官方页面明确：数据集全量为 4,018 条，直接下载文件包仅含前 1,000 条，完整数据需通过 API 获取。
- File Scope：`first_1000_only`（官方明确描述；本地原始文件尚未取得，文件实际行数未核验）
- Downloaded File Rows：N/A
- Difference：若下载包实际为 1,000 行，则与 4,018 条平台总量相差 3,018 条；该差值尚不能作为文件实测结果。
- 文件日期 2022-07-29 早于目录更新时间 2026-08-14；二者不能视为同一数据时点。
- 不调用 API 补齐数据，也不把下载包称为全量。

## A 来源公开数据字典

平台“数据项”列表显示 7 个字段；数据预览表头显示下列信息项代码。当前只记录官网数据字典/预览文字，不将其视为已验证的原始文件 exact headers。

| Preview Code | Official Field Name |
|---|---|
| `JGMC` | 机构名称 |
| `JGDZ` | 机构地址 |
| `JGLB` | 机构类别 |
| `JGJB` | 机构级别 |
| `JGDC` | 机构等次 |
| `ZLKM` | 诊疗科目 |
| `SPJG` | 审批机关 |

页面描述另提及法定代表人、主要负责人、登记号和许可证有效期限，但这些字段不在所列 7 项数据字典中；在原始文件取得前，不将它们视为导出 schema 字段。

- Exact raw headers：未验证（没有下载文件）
- Header row / data start row / sheet count / sheet names / used range / merged cells：未验证
- Specialty field：官方字典明确列有“诊疗科目”，但导出文件字段仍需核实
- Name / Address / Category / Level / Administrative Region：数据字典明确列有机构名称、机构地址、机构类别、机构级别；没有单独的行政区字段
- Official ID：页面描述提及登记号，7 项数据字典未列；原始字段待验证
- Coordinates / Contact / Update Date：7 项数据字典未列

## A 来源官方数据使用许可（只按页面明确文字记录）

详情页展示的《达州公共数据开放平台数据使用许可》说明：

- 平台说明其面向社会提供原始、机器可读、可供社会化再利用的公共数据服务。
- 对“无条件开放”数据，用户可免费、不受歧视地获取平台数据，并可自由利用、自由传播与分享。
- 数据使用须合法、正当，不得损害国家利益、社会公共利益或第三方合法权益。
- 利用公共数据形成数据产品、研究报告、学术论文等成果时，应注明数据来源。
- 使用者应定期向数据责任主体反馈使用情况并配合跟踪管理。
- 许可提到使用者依法获得的开发收益受法律保护；页面未以独立条款明确概括商业使用范围。
- 页面许可未明确长期保存、公开展示及数据撤回后的本地副本处置规则。

因此本项目 `source_status` 仍为 `UNKNOWN`，不能仅据“无条件开放”将来源设为 `APPROVED` 或据此判断所有长期存储/公开展示用途均获准。

## A 来源获取状态与 adapter 备注

用户已确认 A 来源官方正常下载流程返回 `ERR_INVALID_REDIRECT`。不再尝试此来源的下载流程、修复 callback、猜测接口或绕过访问控制。该事实只表示文件获取受阻，不表示来源拒绝或数据集不可用。

- Download：`BLOCKED_BY_OFFICIAL_REDIRECT_ERROR`（用户已确认）
- Original Filename / Full Path / File Size / SHA-256 / Obtained At / File Published At：N/A（未下载）
- Acquisition Method / Operator：N/A（未下载；计划采用 `official_portal_manual_download`，operator `zhangchaonan906-lab`）
- Existing `OpenDataFileAdapter`：`BLOCKED` for this file until downloaded and schema verified. Code supports CSV/XLS/XLSX and includes `xlrd`; however, no Dazhou dataset mapping is configured and actual workbook headers/sheets are unknown.
- Adapter code modified：NO
- In-memory P3 preview：NO
- Production DB writes / persistent pilot DB writes：NO
- Geocoder calls：0
- Facilities published：NO
- Ready For Production Import：NO

## 尚未执行的文件级质量检查

拿到原始文件后再只读核验实际格式、损坏/宏状态、sheet、used range、exact headers、行列数、空名称/地址、重复名称、登记号重复/缺失、日期范围、区县分布、坐标列和诊疗科目中的眼科 evidence。眼科 evidence 只依据原始诊疗科目字段；医院名称、类别不能单独产生 eye evidence。

本地 inspect 不写数据库。若后续以同一 XLS 文件运行 adapter，先验证是否小于 10 MiB（现有 adapter 限制），再配置严格 exact-header dataset mapping；不为来源临时绕开格式/schema 校验。

## 当前结果

```text
P6-N2 DAZHOU REGISTRATION INFO:
Acquisition Status: BLOCKED_BY_OFFICIAL_REDIRECT_ERROR
Reason: ERR_INVALID_REDIRECT in official normal download flow (user-confirmed)
Source Rejected: NO
Dataset Unavailable: NO

P6-N2B DAZHOU LICENSE STATUS: BLOCKED
Dataset: 达州市医疗机构执业许可证
Provider: 达州市卫生健康委
Official Page: https://www.dazhoudata.cn/oportal/catalog/a9865122f8d742c6934783ca92181728
Displayed Records: 81
Updated At: 2026-08-14 16:04:57
Open Status: 无条件开放
Formats Listed: XLS, CSV, JSON, XML, RDF
File Date: 2023-11-30
Normal Download Click: NOT COMPLETED (browser interaction unavailable)
Redirect Error: NOT OBSERVED; download behavior remains unknown
Downloaded File: NO
Raw Exact Headers: NOT VERIFIED (official preview codes are documented above)
Eye Evidence Counts: NOT COMPUTED FROM DOWNLOADED FILE
Coverage: city_only by dataset title; actual coverage not verified
Existing Adapter: BLOCKED pending local file/schema
P3 Preview: NO
Source Status: UNKNOWN
Ready For Production Import: NO
```

## Sources

- [A. 达州市医疗机构执业登记信息详情页](https://www.dazhoudata.cn/oportal/catalog/40f1da7987464008a6d8da0735360d59)
- [B. 达州市医疗机构执业许可证详情页](https://www.dazhoudata.cn/oportal/catalog/a9865122f8d742c6934783ca92181728)
- [B. 官方 XLS 预览页](https://www.dazhoudata.cn/oportal/catalog/viewExcel?excel_type=xls&file_id=eCwwVVtEPJWJztu6jyAKOpoWxZKKKpBZGaDpz42YREJTjBDKB+lRZfRYbwx9QKgJ)；该预览页不等于原始文件下载。
