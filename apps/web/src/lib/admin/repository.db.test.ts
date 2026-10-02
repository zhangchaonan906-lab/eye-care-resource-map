import { afterAll, beforeAll, describe, expect, it } from "vitest";
import { Pool } from "pg";
import { AdminReviewRepository } from "./repository";
import { PostgresPublicFacilityRepository } from "../public-api/repository";

const id = {
  region: "00000000-0000-4000-8000-000000001101",
  source: "00000000-0000-4000-8000-000000001102",
  run: "00000000-0000-4000-8000-000000001103",
  records: ["00000000-0000-4000-8000-000000001104", "00000000-0000-4000-8000-000000001105", "00000000-0000-4000-8000-000000001106"],
  candidates: ["00000000-0000-4000-8000-000000001107", "00000000-0000-4000-8000-000000001108", "00000000-0000-4000-8000-000000001109"],
  duplicate: "00000000-0000-4000-8000-000000001110",
  actor: "00000000-0000-4000-8000-000000001111",
  location: "00000000-0000-4000-8000-000000001112",
  locationConflict: "00000000-0000-4000-8000-000000001113",
  publicationDuplicate: "00000000-0000-4000-8000-000000001114",
  locationLowAccuracy: "00000000-0000-4000-8000-000000001115",
  locationReplacement: "00000000-0000-4000-8000-000000001116",
};
const sourceFields = ["name", "address", "specialties", "coordinates"];
let admin: Pool;
let runtime: Pool;
let restricted: AdminReviewRepository;
let publicRepository: PostgresPublicFacilityRepository;
let facilityId = "";

async function decide(entity: string, entityId: string, action: string, requestId: string, payload: Record<string, unknown> = {}) {
  return restricted.decide({ requestId, actorId: id.actor, entity, entityId, action, payload, reason: "synthetic integration review" });
}

async function expectPublicVisibility(visible: boolean) {
  const [detail,list,search,nearby] = await Promise.all([
    publicRepository.getById(facilityId),
    publicRepository.list({ bbox:[116,39,117,40], zoom:10, limit:100 }),
    publicRepository.search({ q:"P11 测试眼科中心", match:"exact", limit:100 }),
    publicRepository.nearby({ latitude:39.9, longitude:116.4, radiusMeters:5000, limit:100 }),
  ]);
  expect(Boolean(detail)).toBe(visible);
  expect(list.items.some((item) => item.id===facilityId)).toBe(visible);
  expect(search.items.some((item) => item.id===facilityId)).toBe(visible);
  expect(nearby.items.some((item) => item.id===facilityId)).toBe(visible);
}

beforeAll(async () => {
  const adminUrl = process.env.DATABASE_ADMIN_URL;
  const adminRuntimeUrl = process.env.ADMIN_DATABASE_URL;
  const publicUrl = process.env.PUBLIC_API_DATABASE_URL;
  if (!adminUrl || !adminRuntimeUrl || !publicUrl) throw new Error("DATABASE_ADMIN_URL, ADMIN_DATABASE_URL and PUBLIC_API_DATABASE_URL are required for P11 DB integration");
  if (adminUrl === publicUrl || adminRuntimeUrl === publicUrl) throw new Error("admin DB URL must be separate from public API runtime URL");
  admin = new Pool({ connectionString: adminUrl });
  runtime = new Pool({ connectionString: adminRuntimeUrl });
  restricted = new AdminReviewRepository(adminRuntimeUrl);
  publicRepository = new PostgresPublicFacilityRepository(publicUrl);
  await admin.query("BEGIN");
  try {
    await admin.query("INSERT INTO app_private.regions(id,adcode,name,level,version) VALUES($1,'110000','测试北京市','province','p11-admin-test')", [id.region]);
    await admin.query(
      `INSERT INTO app_private.source_catalog(id,name,url,dataset_page,use_basis,status,data_use_allowed,reuse_allowed,app_display_allowed,permitted_fields,retention_restrictions)
       VALUES($1,'P11 synthetic source','https://example.test/source','https://example.test/dataset','synthetic integration fixture','approved',true,true,false,$2,'unrestricted')`,
      [id.source, sourceFields],
    );
    await admin.query("INSERT INTO app_private.import_runs(id,source_id,region_code,status,ended_at) VALUES($1,$2,'110000','succeeded',now())", [id.run, id.source]);
    const rows = [
      { candidate: id.candidates[0], record: id.records[0], name: "P11 测试眼科中心", address: "测试路 11 号" },
      { candidate: id.candidates[1], record: id.records[1], name: "P11 重复候选甲", address: "测试路 21 号" },
      { candidate: id.candidates[2], record: id.records[2], name: "P11 重复候选乙", address: "测试路 22 号" },
    ];
    for (let index = 0; index < rows.length; index += 1) {
      const row = rows[index];
      await admin.query(
        `INSERT INTO app_private.source_records(id,source_id,source_key,raw_payload,source_url,content_hash,import_run_id)
         VALUES($1,$2,$3,$4::jsonb,$5,$6,$7)`,
        [row.record,id.source,`p11-${index}`,JSON.stringify({ name: row.name, address: row.address, specialties: "眼科" }),`https://example.test/${index}`,String(index+1).repeat(64),id.run],
      );
      await admin.query(
        `INSERT INTO app_private.candidate_records(id,source_record_id,parsed_fields,normalized_name,normalized_address,administrative_code,match_status)
         VALUES($1,$2,$3::jsonb,$4,$5,'110000','unmatched')`,
        [row.candidate,row.record,JSON.stringify({name:row.name,address:row.address}),row.name,row.address],
      );
      await admin.query(
        `INSERT INTO app_private.candidate_evidence(candidate_record_id,source_record_id,field_name,evidence_value,evidence_text,evidence_type,rule_version)
         VALUES($1,$2,'specialties','"眼科"','眼科','explicit_field_mention','p11-test-v1')`, [row.candidate,row.record],
      );
    }
    await admin.query("INSERT INTO app_private.duplicate_cases(id,reason,score) VALUES($1,'synthetic exact comparison',0.8)", [id.duplicate]);
    await admin.query("INSERT INTO app_private.duplicate_case_candidates(duplicate_case_id,candidate_record_id) VALUES($1,$2),($1,$3)", [id.duplicate,id.candidates[1],id.candidates[2]]);
    await admin.query("COMMIT");
  } catch (error) { await admin.query("ROLLBACK"); throw error; }
}, 30_000);

afterAll(async () => {
  if (admin) {
    await admin.query("UPDATE app_private.candidate_records SET match_status='unmatched',proposed_facility_id=NULL WHERE id=ANY($1::uuid[])",[id.candidates]);
    await admin.query("DELETE FROM app_private.facility_evidence WHERE facility_id IN (SELECT id FROM app_private.facilities WHERE name LIKE 'P11 %')");
    await admin.query("DELETE FROM app_private.facility_locations WHERE facility_id IN (SELECT id FROM app_private.facilities WHERE name LIKE 'P11 %')");
    await admin.query("DELETE FROM app_private.facilities WHERE name LIKE 'P11 %'");
    await admin.query("UPDATE app_private.source_catalog SET status='suspended',retention_restrictions='delete_on_withdrawal' WHERE id=$1",[id.source]);
    await admin.query("SELECT app_private.erase_withdrawn_source_records($1)",[id.source]);
    await admin.query("DELETE FROM app_private.admin_idempotency WHERE actor_id=$1",[id.actor]);
    await admin.query("DELETE FROM app_private.import_runs WHERE id=$1",[id.run]);
    await admin.query("DELETE FROM app_private.source_catalog WHERE id=$1",[id.source]);
    await admin.query("DELETE FROM app_private.regions WHERE id=$1",[id.region]);
    await admin.end();
  }
  await runtime?.end();
  await restricted?.close();
  await publicRepository?.close();
});

describe("P11 review decisions through the restricted runtime role", () => {
  it("limits admin to review projections and decision functions", async () => {
    const result = await runtime.query(`SELECT current_user, pg_has_role(session_user,'eye_admin_review','member') AS member,
      has_table_privilege(current_user,'app_private.facilities','UPDATE') AS can_update,
      has_table_privilege(current_user,'app_private.source_records','SELECT') AS can_read_raw`);
    expect(result.rows[0]).toMatchObject({ current_user: "eye_admin_review_runtime", member: true, can_update: false, can_read_raw: false });
    const candidates = await restricted.list("candidates", { limit: 5, status: "unmatched" });
    expect(candidates.items[0]).not.toHaveProperty("raw_payload");
    expect(JSON.stringify(candidates.items)).not.toContain("raw_payload");
  });

  it("creates an in-review facility and replays the same idempotency key once", async () => {
    const key = "00000000-0000-4000-8000-000000001201";
    const payload = { name: "P11 测试眼科中心", address: "测试路 11 号", regionId: id.region, category: "ophthalmology_center" };
    const first = await decide("candidate",id.candidates[0],"CREATE_FACILITY",key,payload) as { facilityId: string };
    const replay = await decide("candidate",id.candidates[0],"CREATE_FACILITY",key,payload) as { facilityId: string };
    facilityId = first.facilityId;
    expect(replay.facilityId).toBe(facilityId);
    const status = await admin.query("SELECT verification_status FROM app_private.facilities WHERE id=$1", [facilityId]);
    expect(status.rows[0].verification_status).toBe("in_review");
    const raw = await admin.query("SELECT raw_payload FROM app_private.source_records WHERE id=$1", [id.records[0]]);
    expect(raw.rows[0].raw_payload).toMatchObject({ specialties: "眼科" });
  });

  it("verifies and promotes only an eligible existing location", async () => {
    await admin.query(
      `INSERT INTO app_private.candidate_locations(id,candidate_record_id,source_record_id,provider,provider_version,query_address,query_administrative_code,
       address_fingerprint,result_fingerprint,returned_address,returned_adcode,longitude_wgs84,latitude_wgs84,original_coordinate_system,accuracy_m,precision_level,
       geocode_result_type,validation_status,request_at)
       VALUES($1,$2,$3,'fixture','fixture-v1','测试路 11 号','110000',$4,$5,'测试路 11 号','110000',116.4,39.9,'WGS84',20,'rooftop','fixture','needs_review',now())`,
      [id.location,id.candidates[0],id.records[0],"a".repeat(64),"b".repeat(64)],
    );
    await decide("location",id.location,"VERIFY_LOCATION","00000000-0000-4000-8000-000000001202");
    await decide("location",id.location,"PROMOTE_LOCATION","00000000-0000-4000-8000-000000001203");
    const result = await admin.query("SELECT location_status,accuracy_m,verified_at IS NOT NULL AS verified,coordinate_source_record_id FROM app_private.facility_locations WHERE facility_id=$1", [facilityId]);
    expect(result.rows[0]).toMatchObject({ location_status: "verified", accuracy_m: 20, verified: true, coordinate_source_record_id: id.records[0] });

    await admin.query(
      `INSERT INTO app_private.candidate_locations(id,candidate_record_id,source_record_id,provider,provider_version,query_address,query_administrative_code,
       address_fingerprint,result_fingerprint,returned_address,returned_adcode,longitude_wgs84,latitude_wgs84,original_coordinate_system,accuracy_m,precision_level,
       geocode_result_type,validation_status,request_at)
       VALUES($1,$2,$3,'fixture','fixture-v1','测试路 11 号','110000',$4,$5,'测试路 11 号','110000',116.4,39.9,'WGS84',200,'street','fixture','needs_review',now())`,
      [id.locationLowAccuracy,id.candidates[0],id.records[0],"e".repeat(64),"f".repeat(64)],
    );
    await expect(decide("location",id.locationLowAccuracy,"VERIFY_LOCATION","00000000-0000-4000-8000-000000001222")).rejects.toMatchObject({ code: "23514" });
    await admin.query(
      `INSERT INTO app_private.candidate_locations(id,candidate_record_id,source_record_id,provider,provider_version,query_address,query_administrative_code,
       address_fingerprint,result_fingerprint,returned_address,returned_adcode,longitude_wgs84,latitude_wgs84,original_coordinate_system,stored_coordinate_system,
       accuracy_m,precision_level,geocode_result_type,validation_status,request_at,verified_at)
       VALUES($1,$2,$3,'fixture','fixture-v1','测试路 11 号','110000',$4,$5,'测试路 11 号','110000',116.401,39.9,'WGS84','WGS84',25,'rooftop','fixture','verified',now(),now())`,
      [id.locationReplacement,id.candidates[0],id.records[0],"a".repeat(63)+"1","b".repeat(63)+"2"],
    );
    await expect(decide("location",id.locationReplacement,"PROMOTE_LOCATION","00000000-0000-4000-8000-000000001223")).rejects.toMatchObject({ code: "23514" });
    await decide("location",id.locationReplacement,"PROMOTE_LOCATION","00000000-0000-4000-8000-000000001224",{ replaceVerified:true });
    const audit = await admin.query("SELECT before_value IS NOT NULL AS before_saved,after_value IS NOT NULL AS after_saved FROM app_private.audit_events WHERE entity='location' AND entity_id=$1 AND action='PROMOTE_LOCATION' ORDER BY created_at DESC LIMIT 1",[id.locationReplacement]);
    expect(audit.rows[0]).toMatchObject({ before_saved:true, after_saved:true });
  });

  it("fails closed on rights, then enforces verify/publish/return/republish/withdraw visibility", async () => {
    await decide("facility",facilityId,"VERIFY_FACILITY","00000000-0000-4000-8000-000000001204");
    await expectPublicVisibility(false);
    await expect(decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001205")).rejects.toMatchObject({ code: "23514" });
    await admin.query("UPDATE app_private.source_catalog SET app_display_allowed=true,reuse_allowed=NULL WHERE id=$1",[id.source]);
    await expect(decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001216")).rejects.toMatchObject({ code: "23514" });
    await admin.query("UPDATE app_private.source_catalog SET reuse_allowed=true WHERE id=$1",[id.source]);
    const setupDuplicate = await admin.connect();
    try {
      await setupDuplicate.query("BEGIN");
      await setupDuplicate.query("INSERT INTO app_private.duplicate_cases(id,reason) VALUES($1,'publication conflict gate test')",[id.publicationDuplicate]);
      await setupDuplicate.query("INSERT INTO app_private.duplicate_case_candidates(duplicate_case_id,candidate_record_id) VALUES($1,$2),($1,$3)",[id.publicationDuplicate,id.candidates[0],id.candidates[1]]);
      await setupDuplicate.query("COMMIT");
    } catch (error) {
      await setupDuplicate.query("ROLLBACK");
      throw error;
    } finally {
      setupDuplicate.release();
    }
    await expect(decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001217")).rejects.toMatchObject({ code: "23514" });
    await decide("duplicate",id.publicationDuplicate,"SEPARATE","00000000-0000-4000-8000-000000001218");
    await admin.query(
      `INSERT INTO app_private.candidate_locations(id,candidate_record_id,source_record_id,provider,provider_version,query_address,query_administrative_code,
       address_fingerprint,result_fingerprint,returned_address,returned_adcode,longitude_wgs84,latitude_wgs84,original_coordinate_system,accuracy_m,precision_level,
       geocode_result_type,validation_status,request_at)
       VALUES($1,$2,$3,'fixture','fixture-v1','测试路 11 号','110000',$4,$5,'附近地址','110000',116.5,39.9,'WGS84',20,'rooftop','fixture','needs_review',now())`,
      [id.locationConflict,id.candidates[0],id.records[0],"c".repeat(64),"d".repeat(64)],
    );
    await expect(decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001219")).rejects.toMatchObject({ code: "23514" });
    await decide("location",id.locationConflict,"REJECT_LOCATION","00000000-0000-4000-8000-000000001220");
    await decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001206");
    await expectPublicVisibility(true);
    await admin.query("UPDATE app_private.source_catalog SET status='suspended' WHERE id=$1",[id.source]);
    await expectPublicVisibility(false);
    await admin.query("UPDATE app_private.source_catalog SET status='approved' WHERE id=$1",[id.source]);
    await decide("facility",facilityId,"RETURN_TO_REVIEW","00000000-0000-4000-8000-000000001207");
    await expectPublicVisibility(false);
    await decide("facility",facilityId,"VERIFY_FACILITY","00000000-0000-4000-8000-000000001208");
    await admin.query("UPDATE app_private.source_catalog SET status='suspended' WHERE id=$1",[id.source]);
    await expect(decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001221")).rejects.toMatchObject({ code: "23514" });
    await admin.query("UPDATE app_private.source_catalog SET status='approved' WHERE id=$1",[id.source]);
    await decide("facility",facilityId,"PUBLISH","00000000-0000-4000-8000-000000001209");
    await expectPublicVisibility(true);
    await decide("facility",facilityId,"WITHDRAW","00000000-0000-4000-8000-000000001210");
    await expectPublicVisibility(false);
    const audit = await admin.query("SELECT count(*)::int AS count FROM app_private.audit_events WHERE entity_id=$1",[facilityId]);
    expect(audit.rows[0].count).toBeGreaterThanOrEqual(6);
  });

  it("merges duplicate candidates, reopens the case, and rejects a candidate without deleting provenance", async () => {
    await decide("duplicate",id.duplicate,"MERGE","00000000-0000-4000-8000-000000001211",{
      primaryCandidateId:id.candidates[1], name:"P11 重复候选甲", address:"测试路 21 号", regionId:id.region, category:"unknown",
    });
    const merged = await admin.query("SELECT count(DISTINCT proposed_facility_id)::int AS facilities FROM app_private.candidate_records WHERE id=ANY($1::uuid[])",[id.candidates.slice(1)]);
    expect(merged.rows[0].facilities).toBe(1);
    await decide("duplicate",id.duplicate,"REOPEN_DUPLICATE_CASE","00000000-0000-4000-8000-000000001212");
    const reopened = await admin.query("SELECT resolution FROM app_private.duplicate_cases WHERE id=$1",[id.duplicate]);
    expect(reopened.rows[0].resolution).toBe("pending");
    const concurrent = await Promise.allSettled([
      decide("duplicate",id.duplicate,"SEPARATE","00000000-0000-4000-8000-000000001213"),
      decide("duplicate",id.duplicate,"REJECT_DUPLICATE","00000000-0000-4000-8000-000000001215"),
    ]);
    expect(concurrent.filter((result) => result.status === "fulfilled")).toHaveLength(1);
    expect(concurrent.find((result) => result.status === "rejected")).toMatchObject({ status: "rejected", reason: { code: "40001" } });
    const resolution = await admin.query("SELECT resolution FROM app_private.duplicate_cases WHERE id=$1",[id.duplicate]);
    await decide("duplicate",id.duplicate,"REOPEN_DUPLICATE_CASE","00000000-0000-4000-8000-000000001225");
    await decide("duplicate",id.duplicate,resolution.rows[0].resolution === "separate" ? "REJECT_DUPLICATE" : "SEPARATE","00000000-0000-4000-8000-000000001226");
    await decide("candidate",id.candidates[2],"REJECT_CANDIDATE","00000000-0000-4000-8000-000000001214");
    const source = await admin.query("SELECT count(*)::int AS count FROM app_private.source_records WHERE id=$1",[id.records[2]]);
    expect(source.rows[0].count).toBe(1);
  });
});
