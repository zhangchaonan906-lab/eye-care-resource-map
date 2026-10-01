# P5 北京与广东受控数据试点：实施记录

## 结果

P5-A 未通过：北京和广东卫健委提供的是在线查询入口，公开页面未明确授权本项目自动采集、长期保存、字段使用及再分发。两地来源均记录为 `UNKNOWN`、数据库状态保持 pending。高德协议没有授予本项目持久化地理编码数据的权利，因此 provider 持久化准入为 BLOCKED。按门禁要求未进入 P5-B。

## 已完成

- 记录北京、广东各自的来源权利审查；保存官方入口、待核实项、责任人和复核日期。
- 建立高德地理编码持久化审查记录和离线 FixtureGeocoder 选择说明。
- 增加只接受北京/广东 adcode、必须显式 `--limit`、且需显式 `PILOT_REAL_DATA=true` 的 `pilot` CLI 防护；来源审批不完整时在连接数据库/建立网络请求之前拒绝运行。
- 将 geocoder 的 `quota_per_run` 和 `requests_per_second` 保护移至 pipeline 外层，确保 provider 实现不能单独绕过数据库 policy。测试 quota=10、输入 100 时最多 10 次调用，以及跨调用速率间隔。
- 写入启动前状态报告、回滚手册和 P6 前必须替换粗边界保护的技术债。
- 未增设真实 adapter、未运行真实来源请求、未导入行政区种子或医院记录；这些属于 P5-B，必须等来源准入批准后进行。

## 未完成的 P5-B 验收

没有合格的两地来源，因此没有 source records、candidate、duplicate cases 或真实 coordinates。真实数据抽检、眼科 precision、重复抽查、错区县率、真实坐标样本、完整 adcode 树、实际异常队列、逐记录核验清单和成功 rollback 演练均未评估。两份报告明确表达“未评估”，没有把未处理当作零错误。

## 离线验证

CI 和本地测试继续只用 synthetic DB 与 fixture/mock transport；P5 新增的安全门禁和 P4 provider-independent 限额保护有单元测试。P1–P4 database test runner 保持原有迁移与权限覆盖。此分支不改 P1–P4 表结构。

## 剩余风险

P4 quota 和速率保护以 pipeline 进程/run 为边界。真实 provider 并发启用前，需串行调度或新增跨进程共享 quota reservation/rate limiter，避免多个进程的额度叠加超过 provider 账户级约束。
