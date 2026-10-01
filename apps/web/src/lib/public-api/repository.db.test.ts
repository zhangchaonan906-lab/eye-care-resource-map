import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Pool } from "pg";
import { PostgresPublicFacilityRepository } from "./repository";
import { decodeCursor } from "./validation";

const ids = {
  regionBeijing: "00000000-0000-4000-8000-000000000201",
  regionShanghai: "00000000-0000-4000-8000-000000000202",
  source: "00000000-0000-4000-8000-000000000203",
  importRun: "00000000-0000-4000-8000-000000000204",
  facilities: [
    "00000000-0000-4000-8000-000000000211",
    "00000000-0000-4000-8000-000000000212",
    "00000000-0000-4000-8000-000000000213",
    "00000000-0000-4000-8000-000000000214",
  ],
  records: [
    "00000000-0000-4000-8000-000000000221",
    "00000000-0000-4000-8000-000000000222",
    "00000000-0000-4000-8000-000000000223",
    "00000000-0000-4000-8000-000000000224",
  ],
};

const samples = [
  { name: "测试眼科医院A", normalized: "测试眼科医院A", category: "eye_specialty_hospital", region: ids.regionBeijing, lon: 116.4, lat: 39.9 },
  { name: "测试综合医院B", normalized: "测试综合医院B", category: "general_hospital_ophthalmology", region: ids.regionBeijing, lon: 116.5, lat: 39.8 },
  { name: "测试眼科诊所C", normalized: "测试眼科诊所C", category: "eye_clinic", region: ids.regionShanghai, lon: 116.6, lat: 39.7 },
  { name: "测试院外医院D", normalized: "测试院外医院D", category: "ophthalmology_center", region: ids.regionShanghai, lon: 120.0, lat: 40.0 },
];

let admin: Pool;
let runtimeRole: Pool;
let repository: PostgresPublicFacilityRepository;

async function cleanup(): Promise<void> {
  const client = await admin.connect();
  try {
    await client.query("BEGIN");
    await client.query("SELECT set_config('app.allow_source_erasure', 'true', true)");
    await client.query("DELETE FROM app_private.facility_evidence WHERE facility_id = ANY($1::uuid[])", [ids.facilities]);
    await client.query("DELETE FROM app_private.facility_locations WHERE facility_id = ANY($1::uuid[])", [ids.facilities]);
    await client.query("DELETE FROM app_private.facilities WHERE id = ANY($1::uuid[])", [ids.facilities]);
    await client.query("DELETE FROM app_private.source_records WHERE id = ANY($1::uuid[])", [ids.records]);
    await client.query("DELETE FROM app_private.import_runs WHERE id = $1", [ids.importRun]);
    await client.query("DELETE FROM app_private.source_catalog WHERE id = $1", [ids.source]);
    await client.query("DELETE FROM app_private.regions WHERE id = ANY($1::uuid[])", [[ids.regionBeijing, ids.regionShanghai]]);
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}

beforeAll(async () => {
  const adminUrl = process.env.DATABASE_ADMIN_URL;
  const apiUrl = process.env.PUBLIC_API_DATABASE_URL;
  if (!adminUrl || !apiUrl) throw new Error("DATABASE_ADMIN_URL and PUBLIC_API_DATABASE_URL are required for DB integration");
  admin = new Pool({ connectionString: adminUrl });
  runtimeRole = new Pool({ connectionString: apiUrl });
  repository = new PostgresPublicFacilityRepository(apiUrl);
  await cleanup();
  const client = await admin.connect();
  try {
    await client.query("BEGIN");
    await client.query(
      `INSERT INTO app_private.regions (id, adcode, name, level, version) VALUES
       ($1, '110000', '北京市', 'province', 'p7-api-test'),
       ($2, '310000', '上海市', 'province', 'p7-api-test')`,
      [ids.regionBeijing, ids.regionShanghai],
    );
    await client.query(
      `INSERT INTO app_private.source_catalog
       (id, name, url, dataset_page, use_basis, status, app_display_allowed)
       VALUES ($1, '合成 API 来源', 'https://example.org/source', 'https://example.org/dataset',
               '本地集成测试', 'approved', true)`,
      [ids.source],
    );
    await client.query(
      `INSERT INTO app_private.import_runs (id, source_id, region_code, status, ended_at)
       VALUES ($1, $2, '110000', 'succeeded', now())`,
      [ids.importRun, ids.source],
    );
    for (let i = 0; i < samples.length; i += 1) {
      const sample = samples[i];
      await client.query(
        `INSERT INTO app_private.source_records
         (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
         VALUES ($1, $2, $3, $4::jsonb, 'https://example.org/record', $5, $6)`,
        [ids.records[i], ids.source, `synthetic-${i}`, JSON.stringify({ 法定代表人: "PRIVATE_PERSON_SENTINEL" }), String(i + 1).repeat(64), ids.importRun],
      );
      await client.query(
        `INSERT INTO app_private.facilities
         (id, name, normalized_name, category, region_id, address, ophthalmology_status,
          verification_status, published_at, last_verified_at)
         VALUES ($1, $2, $3, $4, $5, $6, 'verified', 'published', now(), now())`,
        [ids.facilities[i], sample.name, sample.normalized, sample.category, sample.region, `测试地址${i}`],
      );
      await client.query(
        `INSERT INTO app_private.facility_locations
         (facility_id, geog_wgs84, coordinate_source_record_id, location_status, verified_at)
         VALUES ($1, ST_SetSRID(ST_MakePoint($2, $3), 4326)::geography, $4, 'verified', now())`,
        [ids.facilities[i], sample.lon, sample.lat, ids.records[i]],
      );
      await client.query(
        `INSERT INTO app_private.facility_evidence (facility_id, source_record_id, field_name, field_value, confidence)
         VALUES ($1, $2, 'ophthalmology_status', '"verified"'::jsonb, 1),
                ($1, $2, 'name', to_jsonb($3::text), 1),
                ($1, $2, 'address', to_jsonb($4::text), 1)`,
        [ids.facilities[i], ids.records[i], sample.name, `测试地址${i}`],
      );
    }
    await client.query("COMMIT");
  } catch (error) {
    await client.query("ROLLBACK");
    throw error;
  } finally {
    client.release();
  }
}, 30_000);

afterAll(async () => {
  if (!admin || !repository) return;
  await cleanup();
  await repository.close();
  await runtimeRole.end();
  await admin.end();
});

describe("PostGIS public facility repository", () => {
  it("returns only three in-bounds synthetic facilities, with category and region filters", async () => {
    const page = await repository.list({ bbox: [116, 39, 117, 40], limit: 10 });
    expect(page.items).toHaveLength(3);
    expect(page.items.map((item) => item.id).sort()).toEqual(ids.facilities.slice(0, 3).sort());
    expect(JSON.stringify(page)).not.toContain("PRIVATE_PERSON_SENTINEL");
    expect((await repository.list({ bbox: [116, 39, 117, 40], limit: 10, category: "eye_clinic" })).items).toHaveLength(1);
    expect((await repository.list({ bbox: [116, 39, 117, 40], limit: 10, region: "11" })).items).toHaveLength(2);
    expect((await repository.list({ bbox: [-10, -10, -9, -9], limit: 10 })).items).toHaveLength(0);
  });

  it("supports detail lookup and exact/prefix normalized-name search", async () => {
    expect((await repository.getById(ids.facilities[0]))?.name).toBe("测试眼科医院A");
    expect(await repository.getById("00000000-0000-4000-8000-000000000299")).toBeNull();
    expect((await repository.search({ q: "测试眼科医院A", match: "exact", limit: 20 })).items).toHaveLength(1);
    expect((await repository.search({ q: "测试眼科", match: "prefix", limit: 20 })).items).toHaveLength(2);
  });

  it("continues keyset pages without duplicates and rejects private table reads", async () => {
    const first = await repository.list({ bbox: [116, 39, 117, 40], limit: 2 });
    const afterId = decodeCursor(first.nextCursor, "id");
    expect(afterId?.kind).toBe("id");
    const second = await repository.list({ bbox: [116, 39, 117, 40], limit: 2, cursor: afterId?.id });
    expect([...first.items, ...second.items]).toHaveLength(3);
    expect(new Set([...first.items, ...second.items].map((item) => item.id)).size).toBe(3);

    const searchFirst = await repository.search({ q: "测试", match: "prefix", limit: 2 });
    const searchCursor = decodeCursor(searchFirst.nextCursor, "search");
    expect(searchCursor?.kind).toBe("search");
    if (searchCursor?.kind !== "search") throw new Error("search cursor expected");
    const searchSecond = await repository.search({
      q: "测试",
      match: "prefix",
      limit: 2,
      cursor: { name: searchCursor.name, id: searchCursor.id },
    });
    expect([...searchFirst.items, ...searchSecond.items]).toHaveLength(4);

    await expect(runtimeRole.query("SELECT raw_payload FROM app_private.source_records")).rejects.toThrow();
  });

  it("uses a GiST-backed geography predicate", async () => {
    const client = await admin.connect();
    try {
      await client.query("BEGIN");
      await client.query("SET LOCAL enable_seqscan = off");
      const result = await client.query(
        `EXPLAIN (FORMAT JSON) SELECT facility_id FROM app_private.facility_locations
         WHERE ST_Intersects(geog_wgs84, ST_MakeEnvelope(116, 39, 117, 40, 4326)::geography)`,
      );
      expect(JSON.stringify(result.rows)).toContain("facility_locations_geog_wgs84_idx");
      await client.query("ROLLBACK");
    } finally {
      client.release();
    }
  });
});
