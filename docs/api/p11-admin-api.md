# P11 管理 API

所有响应使用 `{ data, meta, error }` JSON envelope，并设置 `Cache-Control: no-store`。管理接口仅接受同源请求。浏览器不提交 `actor_id`；actor 来自已验签的管理员 session。

## 会话

- `GET /api/admin/session`：无 session 时签发短时 pre-login CSRF challenge；已登录时返回 session 概要和 CSRF token。
- `POST /api/admin/session`：需要同源 Origin、pre-login CSRF cookie 与 `X-CSRF-Token`。正文 `{ username, password }`。成功签发 8 小时 HttpOnly session 与 readable CSRF cookie。
- `DELETE /api/admin/session`：需要已登录、同源、session-bound CSRF；清除两个 cookie。

无效凭据统一返回 `401 INVALID_CREDENTIALS`。未登录管理 API 返回 `401 ADMIN_AUTH_REQUIRED`；CSRF/Origin 失败返回 `403 CSRF_REJECTED`。

## 审核队列

`GET /api/admin/review?type=candidates|duplicates|locations|facilities|imports|audit&limit=25&cursor=<uuid>&status=<value>`

候选队列还支持 `source=<uuid>` 与 `region=<adcode-prefix>`。每页最多 100 条。`GET /api/admin/review/{type}/{id}` 返回单条审核投影；`GET /api/admin/audit` 是只读审计分页别名。任何原始 source payload 都不在 projection 中。

## 决策

`POST /api/admin/{candidates|duplicates|locations|facilities}/{id}/decision`

Headers：`X-CSRF-Token` 与 UUID `Idempotency-Key`。Body 至少包含 `{ "action": "...", "reason": "5–500 字理由" }`。其余字段按动作显式提供；服务端移除 actor 字段并从 session 设置 actor。

候选动作：`CREATE_FACILITY`、`MATCH_EXISTING_FACILITY`、`REJECT_CANDIDATE`。新 facility 需审核员确认 name/address/region/category；可使用 `regionCode` 或内部 `regionId`。重复动作：`MERGE`、`SEPARATE`、`REJECT_DUPLICATE`、`REOPEN_DUPLICATE_CASE`。坐标动作：`VERIFY_LOCATION`、`REJECT_LOCATION`、`PROMOTE_LOCATION`，替换时提供 `replaceVerified: true`。机构动作：`VERIFY_FACILITY`、`PUBLISH`、`RETURN_TO_REVIEW`、`WITHDRAW`。

数据库冲突映射为 `409 REVIEW_STATE_CONFLICT` 或 `409 ACTION_BLOCKED`。PUBLISH 的真实权限判断始终由数据库完成。来源文件导入 API 不在 P11 提供，导入编排延期至 P12。
