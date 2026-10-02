# P11 发布门禁与运行说明

## 发布前条件

后台只显示 `admin_publication_checklist` 的结果作提示；最终门禁由数据库 `admin_decide(..., 'PUBLISH', ...)` 再次计算。必须同时满足：

1. facility 为 verified、眼科状态为 verified、具有 `last_verified_at`。
2. facility location 为 verified 且有 `verified_at`。
3. 坐标来源已 approved，并且 data use、reuse、app display 均为 true，retention 不为 unknown，`permitted_fields` 含 `coordinates`。
4. 当前 facility name/address 各有相同值的来源 evidence；对应来源 approved、权利完整且字段分别在 `permitted_fields` 中。
5. 有来源字段明确命中的 ophthalmology evidence；不能通过医院名称创建。evidence 对应来源 approved、权利完整且其原始字段在 `permitted_fields` 中。
6. 没有与该 facility 关联的 pending duplicate case。
7. 没有与当前 facility location 存在行政区或 100 米以上距离冲突的 needs_review candidate location。

任何来源状态被暂停、许可字段缺失、或 rights metadata 为 NULL/unknown 都阻断发布；公开视图也根据来源状态和展示权即时重新过滤。RETURN/WITHDRAW 更新同一设施状态，不写公开数据副本，因此 map、search、nearby 和 detail 共用相同可见性边界。

## 幂等和审计

所有决策需要 request UUID。数据库保存请求与第一次结果；相同 actor/entity/action 的重放返回首次结果，不重复执行副作用。重复使用该 UUID 执行另一动作会拒绝。决策行使用 `FOR UPDATE`，过期状态转换返回冲突。审核理由和完整 before/after 写入 append-only `audit_events`；重复 case 重开另写一条恢复审计。

## 数据库部署

依次迁移 `001–013`。`scripts/test-db.sh` 会创建一次性 `eye_admin_review_runtime` 登录并只供测试使用。生产部署应由数据库管理员按受控流程执行 `scripts/provision-admin-review-login.sql`，生成新的随机强密码，之后将登录 URL 通过部署密钥管理配置到 `ADMIN_DATABASE_URL`。禁止复用 `PUBLIC_API_DATABASE_URL`。

用服务端密钥注入 `ADMIN_USERNAME`、`ADMIN_PASSWORD_HASH`、`ADMIN_SESSION_SECRET` 与 `ADMIN_ACTOR_ID`。生产环境对 `/api/admin/session` 在网关限流，并开启失败登录告警；应用本身不宣称提供分布式限流。验证 dashboard 登录、各队列分页和决策 API 的 CSRF 后再开放 `/admin`。

## 明确延期

P11 不导入真实来源，不改变 source approval，不调用 geocoder，不发布真实医院。Admin import execution、定时任务、增量抓取和来源变化检测延期到 P12。
