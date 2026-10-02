# P11 管理员审核台

P11 为单管理员 MVP，提供候选、重复关系、已有坐标、机构发布、导入记录和审计队列。后台不会运行采集、文件导入或地理编码；这些任务编排留给 P12。

## 登录与会话

服务端配置 `ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH`、`ADMIN_SESSION_SECRET`、`ADMIN_ACTOR_ID`、`ADMIN_DATABASE_URL`。`ADMIN_PASSWORD_HASH` 使用 Node `scrypt`，格式为 `scrypt$16384$8$1$<base64url salt>$<base64url 64-byte digest>`；不要配置明文密码。`ADMIN_SESSION_SECRET` 至少 32 个字符。会话 HMAC 签名，有效期 8 小时；HttpOnly、SameSite=Strict，生产环境启用 Secure。会话不包含密码、哈希或数据库凭据。

打开 `/admin/login` 后先取得一次性 pre-login CSRF token。登录、退出和所有写请求都校验 Origin 与 CSRF。登录错误统一返回相同消息。当前应用不提供分布式登录限流；生产部署必须在网关或边缘平台对登录端点启用限流与告警，不能用进程内计数器替代。

密码哈希可由 Node `crypto.scryptSync` 生成，参数固定为 N=16384、r=8、p=1、64 字节输出，并使用随机 16 字节以上 salt。生产密钥应由密钥管理服务注入，不写入 Git、客户端变量或构建产物。

## 数据库隔离

`PUBLIC_API_DATABASE_URL` 与 `ADMIN_DATABASE_URL` 必须使用不同运行角色。`eye_admin_review` 是 NOLOGIN/NOINHERIT 权限组；`eye_admin_review_runtime` 仅继承该组。后台角色只读 `admin_*_review` 投影并调用 `admin_decide`，没有 `source_records` 原始表读取权，也没有设施、候选或审计表直接写权。生产环境以受信任数据库管理员身份运行 role provisioning，再把专用登录凭据配置到服务端。

后台候选投影只返回解析后的名称、地址、行政区代码、登记号、院区字段和明确的眼科 evidence，不返回 `raw_payload`。导入运行与审计视图只读。所有决策在 `013_admin_review.sql` 的 SECURITY DEFINER 函数内锁行、校验状态、写审计并保存幂等结果。

## 队列和状态

- 候选：按状态分页；CREATE 建立 `in_review` facility，MATCH 必须指定已有 facility，REJECT 保留 candidate 与来源快照。
- 重复：查看成员的名称、地址、登记号、地区、来源及匹配上下文；支持 MERGE、SEPARATE、REJECT、REOPEN。MERGE 不删除快照；REOPEN 使用上次决策的 before state 恢复 candidate 关联，新建 facility 保留并回到 `in_review`。
- 坐标：只审核现存 candidate location。VERIFY 仍受 provider 存储策略、WGS84 范围、精度、准确度和行政区代码检查约束。PROMOTE 保留 source record、accuracy 与验证时间；替换已验证位置必须显式确认。
- 机构：`in_review → verified → published`。RETURN 将 verified/published 退回 `in_review`；WITHDRAW 只作用于 published 并保留 `published_at` 历史值。
- 导入运行、审计记录：只读。

破坏性操作要求 5–500 字理由并显示明确操作名称。每个 POST 需要 UUID `Idempotency-Key`。数据库行锁拒绝过期状态决策；审计 UPDATE/DELETE 由触发器拒绝。

## 发布阻塞项

发布只能从 `verified` 开始。数据库会检查机构和眼科状态、验证时间、verified facility location、location source、名称/地址/眼科证据、相关来源状态与字段级展示权、pending duplicate，以及冲突的待复核坐标。`data_use_allowed`、`reuse_allowed`、`app_display_allowed` 必须显式为 true；`retention_restrictions` 不能为 unknown；`permitted_fields` 必须明确包含实际展示字段（name、address、coordinates 及 evidence 对应字段）。空值或不完整权限不通过。发布视图也持续检查来源状态和展示权，因此来源被暂停后公开接口会隐藏对应记录。

## 管理员访问

给审核员分配单独的管理员凭据和会话密钥。轮换密码哈希、会话密钥和数据库凭据后撤销旧值。审核日志只记录 actor、动作、实体、理由、before/after 和幂等 request id；应用日志不记录密码、session/CSRF token、原始载荷、定位信息或数据库 URL。
