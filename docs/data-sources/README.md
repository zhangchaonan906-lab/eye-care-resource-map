# 来源登记与采集准入

P2 只提供采集框架和合成 Fixture 来源，没有接入任何生产数据源。适配器只能在 `app_private.source_catalog` 中存在且经过准入的来源上运行。

## Source Adapter 规范

每个 adapter 提供稳定的 `source_key`、与登记项一一对应的来源名称和目录 URL、保守的每来源限速设置，以及分页 fetch。原始记录包含来源内唯一 key、HTTPS 原始 URL 和未经业务转换的原始 JSON 对象。Adapter 的所有 HTTP 请求必须通过 `eye_collector.http.HttpClient`；禁止创建自己的 `requests`、HTTPX 或 urllib 客户端。

Adapter 不得标准化名称/地址、匹配实体、识别眼科服务、合并记录、做地理编码或发布数据。字段超出来源 `permitted_fields` 时整条记录拒绝并关闭 run；不得静默删字段后继续。

## 来源准入

登记至少包含来源名称、HTTPS URL、主体、明确的使用依据、逐字段的 `permitted_fields`、访问政策、复核时间和状态。申请阶段使用 `pending`。只有人工核验来源许可、服务条款、robots.txt、授权范围、频率限制及可保存字段后，才由管理员更新为 `approved`，并将 `access_policy` 精确设为 `automated_access_allowed`。其他任意值均 fail closed。

P2 collector 登录只拥有读取 `source_catalog` 的权限，不能自行批准或恢复来源。失去授权、站点禁止自动访问、robots 不允许、要求登录/验证码/付费，或使用范围不清楚时，管理员应将来源改为 `suspended` 或保持 `pending`。遇到 401/403/404 或站点挑战，框架不重试、不绕过、不使用代理池；记录失败并由管理员复核。

`automated_access_allowed` 是人工审核结论的机器门闩，不代表系统已自动解析 robots.txt，也不替代法律/合同审查。Fixture 来源使用 `.invalid` 域名和合成内容，不代表任何真实网站许可。

## 登记示例

由受信任管理员连接数据库后登记 pending 来源。以下示例只展示字段结构，不能直接用于真实网站：

```sql
INSERT INTO app_private.source_catalog
  (name, url, owner, use_basis, permitted_fields, access_policy, status)
VALUES
  ('待复核示例', 'https://source.example.test/directory', '来源主体',
   '待补充明确许可依据', ARRAY['name', 'address'], 'manual_review_required', 'pending');
```

复核完毕后，管理员根据可证明的授权范围更新记录；不能只因网页可打开就批准自动采集。

## 新增适配器步骤

1. 完成来源主体、许可、robots、访问方式、允许字段、更新频率与责任人的书面复核。
2. 在 `source_catalog` 登记并审核，列出明确允许保存的字段。
3. 在 `services/collector/src/eye_collector/sources/` 实现 `SourceAdapter`，保留原始 payload，使用 P1 的 source key 与 content hash 快照约束。
4. 所有请求经共享 HTTP client；adapter 使用串行请求，来源配置默认 1 request/second，只有明确许可时才调整。
5. 用离线 mock transport 测分页、错误和限速；不在 CI 请求真实网站。
6. 用小 limit 与 dry-run 做人工授权后的连接验证；单独评审数据保存与再展示依据后再进入后续阶段。

## Retry 与限速

HTTP timeout、连接错误、429、500、502、503、504 最多尝试 4 次，指数退避加 jitter，遵守有上限的数值 `Retry-After`。400、401、403、404 和其他非重试状态立即停止。每个 adapter key 有独立限速器；同步 runner 单来源串行、最大并发为 1。限速和 retry 的时间函数可以注入，测试不做实际等待。

## 数据合法使用原则

- 公开可见不自动等于可批量抓取、可长期存储或可再发布。
- 不绕过登录、验证码、访问控制、付费墙、频率限制或 robots 规则。
- 不通过代理池轮换身份以避开封禁。
- 许可不明确时保持 pending/suspended，使用 Fixture 完成开发验证。
- 原始记录保存来源 key、HTTPS URL、采集时间、来源 ID、run ID 和 canonical SHA-256；不得把错误/缺失字段猜测成真实值。
- collector 的最小权限角色不能写医院实体、候选、证据、坐标、去重或发布表。
