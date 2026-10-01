# 广东医疗机构查询：P5 来源评审

| 字段 | 审查记录 |
| --- | --- |
| source_name | 广东省卫生健康委员会医疗机构查询 |
| source_url | https://cx.gdswjw.cn/ （由广东省卫健委官网“数据开放”栏目链接） |
| source_owner | 广东省卫生健康委员会（查询服务技术运营主体未核实） |
| jurisdiction | 广东省 |
| data_scope | 医疗机构查询；医院清单、眼科字段、院区覆盖范围和可导出字段未核实 |
| permitted_fields | UNKNOWN；未找到明确字段许可 |
| update_frequency | UNKNOWN |
| public_access_method | 卫健委官网链接至在线查询入口；未确认批量导出或开放 API |
| robots policy | UNKNOWN；未获取并评估 robots.txt |
| terms / use basis | 官方网站提供查询入口；未找到适用于自动采集、数据库保存和再分发的明确许可。公开可访问不构成此类许可 |
| authentication required? | UNKNOWN；未执行查询或探测 |
| captcha required? | UNKNOWN；未执行查询或探测 |
| automated collection allowed? | UNKNOWN |
| long-term storage allowed? | UNKNOWN |
| redistribution allowed? | UNKNOWN |
| attribution required? | UNKNOWN |
| rate limit | UNKNOWN |
| reviewer | P5 source qualification review |
| reviewed_at | 2026-10-01 |
| decision | UNKNOWN |

## 决策

保持 `source_catalog.status=pending`。不得将 `access_policy` 设为 `automated_access_allowed`，不得启用 adapter 或采集真实数据。需向数据所有者取得涵盖自动访问、允许字段、保存期限及展示/再分发的书面答复后重新评审。

审查依据：广东省卫健委[官网](https://wsjkw.gd.gov.cn/zwgk/index.html)将该入口列在“数据开放”栏目，并链接到上述查询服务；栏目名和可查询性本身不构成对自动采集、保存或再分发的明确授权。此次仅核对公开页面和链接，没有执行查询、批量导出或自动请求。
