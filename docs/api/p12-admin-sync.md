# P12 Admin Sync API

These endpoints use the existing P11 signed administrator session and the dedicated `ADMIN_DATABASE_URL` runtime role. Responses are `no-store`; the API does not run collection or ETL.

## Read sync queues

`GET /api/admin/sync?type=policies|tasks|alerts&limit=25&cursor=<uuid>&status=<value>`

Requires an authenticated administrator. The response uses the existing `{ data, meta, error }` envelope and cursor pagination. Policy rows include the approved source status and access policy; task rows keep `source_sync_task` separate from their related `import_run`; alert rows contain only safe summary messages.

## Mutate a sync policy

`POST /api/admin/sync/{sourceId}/decision`

Requires a valid session cookie, same-origin `Origin`, matching CSRF cookie and `X-CSRF-Token`, and a UUID `Idempotency-Key`. The request body is:

```json
{"action":"RUN_NOW","reason":"Operator requested a controlled sync"}
```

Supported actions are `RUN_NOW`, `PAUSE_SYNC`, and `RESUME_SYNC`. A reason must contain 5–500 characters. Actor identity always comes from the verified session, not from the request body. Mutations are recorded in `audit_events`.

`RUN_NOW` only enqueues a task and returns HTTP 202 with its task ID. Replaying the same key and action returns the stored result. A `manual_only` source returns HTTP 409 with `MANUAL_FILE_REQUIRED`. It does not trigger a file download. Pause/resume return the durable policy action result; they do not alter source approval.

The API never accepts adapter keys, URLs, source rights, approval status, payloads, or an actor ID from the client.
