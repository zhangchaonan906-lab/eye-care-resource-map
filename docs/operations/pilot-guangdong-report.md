# 广东 P5 受控试点状态报告

**状态：BLOCKED（P5-A 来源准入未通过；P5-B 未运行）**  
**统计范围：真实试点数据；Fixture 不纳入本报告。**  
**生成/审查日期：2026-10-01**

本文件是启动前门禁报告，不是实际数据质量结论。广东省卫健委医疗机构查询来源的自动采集、允许字段、保存和再分发权限均为 `UNKNOWN`，因此没有发起真实来源请求、导入 source record、运行 ETL 或调用地理编码器。以下 0 表示没有进行试点处理，不代表来源中不存在数据。

| 指标 | 数量 | 说明 |
| --- | ---: | --- |
| Source Records | 0 | 试点未运行 |
| Candidates Created | 0 | 试点未运行 |
| Skipped | 0 | 未读取来源数据 |
| Ophthalmology Evidence Found | 0 | 未读取来源数据 |
| No Ophthalmology Evidence | 0 | 未读取来源数据 |
| Matched | 0 | 未运行 P3 |
| Unmatched | 0 | 未运行 P3 |
| Needs Review | 0 | 未运行 P3 |
| Duplicate Cases | 0 | 未运行 P3 |
| Coordinates Requested | 0 | 未运行 P4 |
| Coordinates Verified | 0 | 未运行 P4 |
| Coordinates Needs Review | 0 | 未运行 P4 |
| Coordinates Rejected | 0 | 未运行 P4 |
| Region Mismatch | 0 | 未运行 P4 |
| Low Precision | 0 | 未运行 P4 |
| No Result | 0 | 未运行 P4 |
| Errors | 0 | 未运行 P4 |

## 来源覆盖与局限

- 已知来源：广东省卫健委“医疗机构查询”入口。获准记录数/可获取总数：未建立分母；覆盖率不可计算。
- 总现实世界覆盖率：UNKNOWN。不得表述为“覆盖广东省全部眼科医院”。
- 来源限制：官方入口不等同于批量 API；许可、字段、自动访问、存储、再分发和速率尚未明确。
- 已知缺口：没有真实医院记录，没有对眼科证据、院区重复、地址、地市/区县或坐标进行人工验证。

## 异常队列

`missing_name`、`missing_address`、`missing_adcode`、`no_eye_evidence`、`duplicate`、`region_mismatch`、`low_precision`、`no_geocode_result`、`source_conflict` 均为 **未评估**；不能把未处理误报为零异常。

## 人工抽检清单

未生成记录级清单：没有获准导入的真实候选。抽样数 0；质量阈值 `NOT EVALUATED`。取得来源授权并完成受控导入后，生成至少 50 条或全部记录（不足 50 条时）的核验清单，字段包含名称、来源及 URL、地址、候选类别、眼科证据、adcode、坐标状态/坐标和审核备注。
