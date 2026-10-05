import { Pool } from "pg";
import type { CorrectionInput } from "./validation";

export class CorrectionRepository {
  private readonly pool: Pool;
  constructor(connectionString = process.env.CORRECTION_DATABASE_URL) {
    if (!connectionString) throw new Error("CORRECTION_DATABASE_URL is required");
    try {
      if (new URL(connectionString).username !== "eye_correction_runtime") throw new Error("CORRECTION_DATABASE_URL must use the dedicated submit-only role");
    } catch (error) {
      if (error instanceof Error && error.message.includes("dedicated submit-only role")) throw error;
      throw new Error("CORRECTION_DATABASE_URL must be a valid PostgreSQL URL");
    }
    if (connectionString === process.env.PUBLIC_API_DATABASE_URL || connectionString === process.env.ADMIN_DATABASE_URL) {
      throw new Error("CORRECTION_DATABASE_URL must use a dedicated runtime role");
    }
    this.pool = new Pool({ connectionString, max: 3, idleTimeoutMillis: 30_000, connectionTimeoutMillis: 5_000 });
  }
  async submit(input: CorrectionInput): Promise<string> {
    const result = await this.pool.query<{ id: string }>(
      "SELECT app_private.submit_correction_report($1::uuid,$2,$3) AS id",
      [input.facilityId ?? null, input.type, input.description],
    );
    const id = result.rows[0]?.id;
    if (!id) throw new Error("CORRECTION_SUBMISSION_FAILED");
    return id;
  }
  async close(): Promise<void> { await this.pool.end(); }
}

let repository: CorrectionRepository | undefined;
export function getCorrectionRepository(): CorrectionRepository {
  repository ??= new CorrectionRepository();
  return repository;
}
