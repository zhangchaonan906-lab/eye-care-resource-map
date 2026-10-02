import { Pool, type QueryResultRow } from "pg";

export type ReviewType = "candidates" | "duplicates" | "locations" | "facilities" | "imports" | "audit";
export type SyncReviewType = "policies" | "tasks" | "alerts";
const VIEW_BY_TYPE: Record<ReviewType, string> = {
  candidates: "app_private.admin_candidate_review",
  duplicates: "app_private.admin_duplicate_review",
  locations: "app_private.admin_location_review",
  facilities: "app_private.admin_facility_review",
  imports: "app_private.admin_import_runs",
  audit: "app_private.admin_audit_feed",
};

export class AdminReviewRepository {
  private readonly pool: Pool;

  constructor(connectionString = process.env.ADMIN_DATABASE_URL) {
    if (!connectionString) throw new Error("ADMIN_DATABASE_URL is required");
    const publicUrl = process.env.PUBLIC_API_DATABASE_URL;
    if (!publicUrl || connectionString === publicUrl) throw new Error("ADMIN_DATABASE_URL must be separate from PUBLIC_API_DATABASE_URL");
    try {
      if (new URL(connectionString).username === new URL(publicUrl).username) throw new Error("ADMIN_DATABASE_URL must use a dedicated runtime role");
    } catch (error) {
      if (error instanceof Error && error.message.includes("dedicated runtime role")) throw error;
      throw new Error("ADMIN_DATABASE_URL must be a valid PostgreSQL URL");
    }
    this.pool = new Pool({ connectionString, max: 5, idleTimeoutMillis: 30_000, connectionTimeoutMillis: 5_000 });
  }

  async list(type: ReviewType, options: { limit: number; cursor?: string; status?: string; sourceId?: string; region?: string }): Promise<{ items: QueryResultRow[]; nextCursor: string | null }> {
    const view = VIEW_BY_TYPE[type];
    await this.assertRoleMembership();
    const values: unknown[] = [];
    const where: string[] = [];
    if (options.cursor) { values.push(options.cursor); where.push(`id < $${values.length}::uuid`); }
    if (options.status) {
      const column = type === "candidates" ? "match_status" : type === "duplicates" ? "resolution" : type === "locations" ? "validation_status" : type === "facilities" ? "verification_status" : type === "imports" ? "status" : null;
      if (column) { values.push(options.status); where.push(`${column} = $${values.length}`); }
    }
    if (options.sourceId && type === "candidates") { values.push(options.sourceId); where.push(`source_id = $${values.length}::uuid`); }
    if (options.region && type === "candidates") { values.push(options.region); where.push(`administrative_code LIKE $${values.length} || '%'`); }
    values.push(Math.min(Math.max(options.limit, 1), 100) + 1);
    const result = await this.pool.query(
      `SELECT * FROM ${view}${where.length ? ` WHERE ${where.join(" AND ")}` : ""} ORDER BY id DESC LIMIT $${values.length}`,
      values,
    );
    const hasMore = result.rows.length > options.limit;
    const items = result.rows.slice(0, options.limit);
    return { items, nextCursor: hasMore ? String(items.at(-1)?.id ?? "") || null : null };
  }

  async get(type: ReviewType, id: string): Promise<QueryResultRow | null> {
    await this.assertRoleMembership();
    const result = await this.pool.query(`SELECT * FROM ${VIEW_BY_TYPE[type]} WHERE id=$1::uuid`, [id]);
    return result.rows[0] ?? null;
  }

  async listSync(type: SyncReviewType, options: { limit: number; cursor?: string; status?: string }): Promise<{ items: QueryResultRow[]; nextCursor: string | null }> {
    const views: Record<SyncReviewType, string> = {
      policies: "app_private.admin_sync_policy_review",
      tasks: "app_private.admin_sync_task_review",
      alerts: "app_private.admin_sync_alert_review",
    };
    const statusColumn: Record<SyncReviewType, string> = { policies: "source_status", tasks: "status", alerts: "severity" };
    await this.assertRoleMembership();
    const values: unknown[] = [];
    const where: string[] = [];
    if (options.cursor) { values.push(options.cursor); where.push(`id < $${values.length}::uuid`); }
    if (options.status) { values.push(options.status); where.push(`${statusColumn[type]} = $${values.length}`); }
    values.push(Math.min(Math.max(options.limit, 1), 100) + 1);
    const result = await this.pool.query(
      `SELECT * FROM ${views[type]}${where.length ? ` WHERE ${where.join(" AND ")}` : ""} ORDER BY id DESC LIMIT $${values.length}`,
      values,
    );
    const hasMore = result.rows.length > options.limit;
    const items = result.rows.slice(0, options.limit);
    return { items, nextCursor: hasMore ? String(items.at(-1)?.id ?? "") || null : null };
  }

  async decideSync(input: { sourceId: string; actorId: string; requestId: string; action: "RUN_NOW" | "PAUSE_SYNC" | "RESUME_SYNC"; reason: string }): Promise<unknown> {
    await this.assertRoleMembership();
    const result = input.action === "RUN_NOW"
      ? await this.pool.query<{ result: unknown }>(
        `SELECT app_private.admin_enqueue_source_sync_task($1::uuid,$2::uuid,$3::uuid,$4) AS result`,
        [input.sourceId, input.actorId, input.requestId, input.reason],
      )
      : await this.pool.query<{ result: unknown }>(
        `SELECT app_private.admin_set_source_sync_paused($1::uuid,$2::uuid,$3::uuid,$4,$5) AS result`,
        [input.sourceId, input.actorId, input.requestId, input.reason, input.action === "PAUSE_SYNC"],
      );
    return result.rows[0]?.result;
  }

  async decide(input: { requestId: string; actorId: string; entity: string; entityId: string; action: string; payload: Record<string, unknown>; reason: string }): Promise<unknown> {
    await this.assertRoleMembership();
    const result = await this.pool.query<{ result: unknown }>(
      `SELECT app_private.admin_decide($1::uuid,$2::uuid,$3,$4::uuid,$5,$6::jsonb,$7) AS result`,
      [input.requestId, input.actorId, input.entity, input.entityId, input.action, JSON.stringify(input.payload), input.reason],
    );
    return result.rows[0]?.result;
  }

  async close(): Promise<void> { await this.pool.end(); }

  private async assertRoleMembership(): Promise<void> {
    const result = await this.pool.query<{ allowed: boolean }>(`SELECT pg_has_role(session_user,'eye_admin_review','member') AS allowed`);
    if (result.rows[0]?.allowed !== true) throw new Error("ADMIN_DB_ROLE_REQUIRED");
  }
}

let repository: AdminReviewRepository | undefined;
export function getAdminReviewRepository(): AdminReviewRepository {
  repository ??= new AdminReviewRepository();
  return repository;
}
