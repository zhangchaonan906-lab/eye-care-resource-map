import { Pool, type QueryResultRow } from "pg";
import type { FacilityListInput, NearbyFacility, NearbySearchInput, Page, PublicFacility, PublicFacilityRepository, SearchInput } from "./types";
import { encodeCursor } from "./validation";

type FacilityRow = QueryResultRow & {
  id: string;
  name: string;
  category: PublicFacility["category"];
  address: string;
  region_adcode: string;
  region_name: string;
  hospital_level: string | null;
  hospital_grade: string | null;
  longitude_wgs84: number;
  latitude_wgs84: number;
  ophthalmology_evidence_count: number;
  attribution: Array<{ name: string; url: string; updatedAt: string | null }>;
  last_verified_at: Date | string;
  normalized_name: string;
  distance_meters?: number;
};

const SELECTION = `
  id, name, normalized_name, category, address, region_adcode, region_name,
  hospital_level, hospital_grade, longitude_wgs84, latitude_wgs84,
  ophthalmology_evidence_count, attribution, last_verified_at
`;

function mapFacility(row: FacilityRow): PublicFacility {
  return {
    id: row.id,
    name: row.name,
    category: row.category,
    address: row.address,
    region: { adcode: row.region_adcode, name: row.region_name },
    hospitalLevel: row.hospital_level,
    hospitalGrade: row.hospital_grade,
    longitude: Number(row.longitude_wgs84),
    latitude: Number(row.latitude_wgs84),
    ophthalmology: { status: "verified", evidenceCount: Number(row.ophthalmology_evidence_count) },
    attribution: row.attribution ?? [],
    lastVerifiedAt: new Date(row.last_verified_at).toISOString(),
  };
}

export class PostgresPublicFacilityRepository implements PublicFacilityRepository {
  private readonly pool: Pool;

  constructor(connectionString = process.env.PUBLIC_API_DATABASE_URL) {
    if (!connectionString) throw new Error("PUBLIC_API_DATABASE_URL is required");
    this.pool = new Pool({ connectionString, max: 10, idleTimeoutMillis: 30_000, connectionTimeoutMillis: 5_000 });
  }

  async list(input: FacilityListInput): Promise<Page<PublicFacility>> {
    const values = [...input.bbox, input.category ?? null, input.region ?? null, input.cursor ?? null, input.limit + 1];
    const result = await this.pool.query<FacilityRow>(
      `SELECT ${SELECTION} FROM public.query_published_facilities_bbox($1, $2, $3, $4, $5, $6, $7::uuid, $8)`,
      values,
    );
    return this.page(result.rows, input.limit, (row) => ({ kind: "id", id: row.id }));
  }

  async getById(id: string): Promise<PublicFacility | null> {
    const result = await this.pool.query<FacilityRow>(`SELECT ${SELECTION} FROM public.published_facility_api WHERE id = $1::uuid`, [id]);
    return result.rows[0] ? mapFacility(result.rows[0]) : null;
  }

  async countPublished(): Promise<number> {
    const result = await this.pool.query<{ count: number }>("SELECT count(*)::integer AS count FROM public.published_facility_api");
    return Number(result.rows[0]?.count ?? 0);
  }

  async search(input: SearchInput): Promise<Page<PublicFacility>> {
    const values: unknown[] = [input.q];
    const clauses = [input.match === "exact" ? "normalized_name = $1" : "left(normalized_name, char_length($1)) = $1"];
    if (input.category) { values.push(input.category); clauses.push(`category = $${values.length}`); }
    if (input.region) { values.push(input.region); clauses.push(`region_adcode LIKE $${values.length} || '%'`); }
    if (input.cursor) {
      values.push(input.cursor.name, input.cursor.name, input.cursor.id);
      clauses.push(`(normalized_name > $${values.length - 2} OR (normalized_name = $${values.length - 1} AND id > $${values.length}::uuid))`);
    }
    values.push(input.limit + 1);
    const result = await this.pool.query<FacilityRow>(
      `SELECT ${SELECTION} FROM public.published_facility_api WHERE ${clauses.join(" AND ")} ORDER BY normalized_name, id LIMIT $${values.length}`,
      values,
    );
    return this.page(result.rows, input.limit, (row) => ({ kind: "search", name: row.normalized_name, id: row.id }));
  }

  async nearby(input: NearbySearchInput): Promise<{ items: NearbyFacility[]; truncated: boolean }> {
    const result = await this.pool.query<FacilityRow & { distance_meters: number }>(
      `SELECT * FROM public.query_published_facilities_nearby($1, $2, $3, $4, $5)`,
      [input.latitude, input.longitude, input.radiusMeters, input.category ?? null, input.limit + 1],
    );
    const truncated = result.rows.length > input.limit;
    return {
      items: result.rows.slice(0, input.limit).map((row) => ({ ...mapFacility(row), distanceMeters: Number(row.distance_meters) })),
      truncated,
    };
  }

  async close(): Promise<void> {
    await this.pool.end();
  }

  private page<T extends FacilityRow>(rows: T[], limit: number, cursor: (row: T) => Parameters<typeof encodeCursor>[0]): Page<PublicFacility> {
    const hasMore = rows.length > limit;
    const selected = rows.slice(0, limit);
    return {
      items: selected.map(mapFacility),
      nextCursor: hasMore && selected.length ? encodeCursor(cursor(selected[selected.length - 1])) : null,
    };
  }
}

let repository: PostgresPublicFacilityRepository | undefined;
export function getPublicFacilityRepository(): PostgresPublicFacilityRepository {
  repository ??= new PostgresPublicFacilityRepository();
  return repository;
}
