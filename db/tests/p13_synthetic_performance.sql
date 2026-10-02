\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

CREATE TEMP TABLE p13_performance_rows (
  ordinal integer PRIMARY KEY,
  facility_id uuid NOT NULL,
  source_record_id uuid NOT NULL,
  region_code text NOT NULL,
  longitude double precision NOT NULL,
  latitude double precision NOT NULL
) ON COMMIT DROP;

INSERT INTO app_private.regions(adcode,name,level,version)
VALUES
  ('110000','P13 合成北京','city','p13-synthetic'),
  ('120000','P13 合成天津','city','p13-synthetic'),
  ('310000','P13 合成上海','city','p13-synthetic'),
  ('440000','P13 合成广东','city','p13-synthetic'),
  ('510000','P13 合成四川','city','p13-synthetic');

INSERT INTO app_private.source_catalog(
  name,url,use_basis,permitted_fields,access_policy,status,reviewed_at,
  data_use_allowed,reuse_allowed,app_display_allowed,raw_data_transfer_allowed,
  raw_data_redistribution_allowed,attribution_required,retention_restrictions
)
VALUES(
  'P13 Synthetic Performance Fixture','https://fixture.invalid/p13-performance',
  'Runtime-generated synthetic benchmark only',ARRAY['name','address','coordinates','specialties','ophthalmology_status'],
  'automated_access_allowed','approved',now(),true,true,true,false,false,false,'unrestricted'
);

INSERT INTO app_private.import_runs(source_id,region_code,status,ended_at)
SELECT id,'110000','succeeded',now() FROM app_private.source_catalog
WHERE name='P13 Synthetic Performance Fixture';

INSERT INTO p13_performance_rows(ordinal,facility_id,source_record_id,region_code,longitude,latitude)
SELECT
  n,
  gen_random_uuid(),
  gen_random_uuid(),
  (ARRAY['110000','120000','310000','440000','510000'])[1 + (n % 5)],
  CASE WHEN n % 5 = 0 THEN 116.40 + ((n % 100) * 0.0001)
       WHEN n % 5 = 1 THEN 117.20 + ((n % 100) * 0.0001)
       WHEN n % 5 = 2 THEN 121.40 + ((n % 100) * 0.0001)
       WHEN n % 5 = 3 THEN 114.10 + ((n % 100) * 0.0001)
       ELSE 104.10 + ((n % 100) * 0.0001) END,
  CASE WHEN n % 5 = 0 THEN 39.90 + ((n % 100) * 0.0001)
       WHEN n % 5 = 1 THEN 39.10 + ((n % 100) * 0.0001)
       WHEN n % 5 = 2 THEN 31.20 + ((n % 100) * 0.0001)
       WHEN n % 5 = 3 THEN 22.60 + ((n % 100) * 0.0001)
       ELSE 30.70 + ((n % 100) * 0.0001) END
FROM generate_series(1,5000) AS n;

INSERT INTO app_private.source_records(
  id,source_id,source_key,raw_payload,source_url,content_hash,import_run_id
)
SELECT
  rows.source_record_id,
  source.id,
  'p13-' || rows.ordinal,
  jsonb_build_object('name','P13 Synthetic Hospital ' || lpad(rows.ordinal::text,5,'0'),'specialties','眼科'),
  'https://fixture.invalid/p13-performance/' || rows.ordinal,
  md5(rows.ordinal::text) || md5('p13-' || rows.ordinal),
  run.id
FROM p13_performance_rows AS rows
JOIN app_private.source_catalog AS source ON source.name='P13 Synthetic Performance Fixture'
JOIN app_private.import_runs AS run ON run.source_id=source.id;

INSERT INTO app_private.facilities(
  id,name,normalized_name,category,region_id,address,ophthalmology_status,
  verification_status,published_at,last_verified_at
)
SELECT
  rows.facility_id,
  'P13 Synthetic Hospital ' || lpad(rows.ordinal::text,5,'0'),
  'p13 synthetic hospital ' || lpad(rows.ordinal::text,5,'0'),
  CASE WHEN rows.ordinal % 2 = 0 THEN 'eye_specialty_hospital' ELSE 'ophthalmology_center' END,
  region.id,
  '合成地址 ' || rows.ordinal,
  'verified','published',now(),now()
FROM p13_performance_rows AS rows
JOIN app_private.regions AS region
  ON region.adcode=rows.region_code AND region.version='p13-synthetic';

INSERT INTO app_private.facility_locations(
  facility_id,geog_wgs84,coordinate_source_record_id,location_status,verified_at
)
SELECT rows.facility_id,ST_SetSRID(ST_MakePoint(rows.longitude,rows.latitude),4326)::geography,
  rows.source_record_id,'verified',now()
FROM p13_performance_rows AS rows;

INSERT INTO app_private.facility_evidence(facility_id,source_record_id,field_name,field_value,confidence,reviewed_at)
SELECT rows.facility_id,rows.source_record_id,evidence.field_name,evidence.field_value,1.0,now()
FROM p13_performance_rows AS rows
CROSS JOIN LATERAL (
  VALUES
    ('name',to_jsonb('P13 Synthetic Hospital ' || lpad(rows.ordinal::text,5,'0'))),
    ('address',to_jsonb('合成地址 ' || rows.ordinal)),
    ('specialties',to_jsonb('眼科'::text)),
    ('ophthalmology_status','"verified"'::jsonb)
) AS evidence(field_name,field_value);

ANALYZE app_private.facility_locations;
ANALYZE app_private.facilities;
ANALYZE app_private.facility_evidence;

DO $$ BEGIN
  IF (
    SELECT count(DISTINCT api.id)
    FROM public.published_facility_api AS api
    JOIN app_private.facility_evidence AS evidence ON evidence.facility_id=api.id
    JOIN app_private.source_records AS records ON records.id=evidence.source_record_id
    JOIN app_private.source_catalog AS source ON source.id=records.source_id
    WHERE source.name='P13 Synthetic Performance Fixture'
  ) <> 5000 THEN
    RAISE EXCEPTION 'P13 benchmark must publish exactly 5000 synthetic rows';
  END IF;
END $$;

\echo 'P13 EXPLAIN ANALYZE — bounding box'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id FROM public.query_published_facilities_bbox(
  116.39,39.89,116.42,39.92,NULL,NULL,NULL,100
);

\echo 'P13 EXPLAIN ANALYZE — nearby ST_DWithin'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id FROM public.query_published_facilities_nearby(39.90,116.40,5000,NULL,100);

\echo 'P13 EXPLAIN ANALYZE — GiST bbox predicate'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT facility_id FROM app_private.facility_locations
WHERE ST_Intersects(geog_wgs84,ST_MakeEnvelope(116.39,39.89,116.42,39.92,4326)::geography);

\echo 'P13 EXPLAIN ANALYZE — GiST nearby predicate'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT facility_id FROM app_private.facility_locations
WHERE ST_DWithin(geog_wgs84,ST_SetSRID(ST_MakePoint(116.40,39.90),4326)::geography,5000);

\echo 'P13 EXPLAIN ANALYZE — indexed prefix-search projection'
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT id FROM app_private.facilities
WHERE verification_status='published' AND published_at IS NOT NULL
  AND last_verified_at IS NOT NULL AND ophthalmology_status='verified'
  AND normalized_name LIKE 'p13 synthetic hospital 00%' ESCAPE E'\\'
ORDER BY normalized_name,id
LIMIT 21;

CREATE TEMP TABLE p13_reference_samples (
  endpoint text NOT NULL,
  duration_ms double precision NOT NULL,
  succeeded boolean NOT NULL
) ON COMMIT DROP;

DO $$
DECLARE
  iteration integer;
  started_at timestamptz;
  target_id uuid := (SELECT facility_id FROM p13_performance_rows ORDER BY ordinal LIMIT 1);
  endpoint_name text;
BEGIN
  FOR iteration IN 1..52 LOOP
    endpoint_name := CASE iteration % 4
      WHEN 0 THEN 'facilities'
      WHEN 1 THEN 'nearby'
      WHEN 2 THEN 'search'
      ELSE 'detail'
    END;
    started_at := clock_timestamp();
    BEGIN
      CASE endpoint_name
        WHEN 'facilities' THEN
          PERFORM id FROM public.query_published_facilities_bbox(
            116.39,39.89,116.42,39.92,NULL,NULL,NULL,100
          );
        WHEN 'nearby' THEN
          PERFORM id FROM public.query_published_facilities_nearby(39.90,116.40,5000,NULL,100);
        WHEN 'search' THEN
          PERFORM id FROM public.query_published_facilities_search(
            'p13 synthetic hospital 00%','prefix',NULL,NULL,NULL,NULL,21
          );
        ELSE
          PERFORM id FROM public.published_facility_api WHERE id=target_id;
      END CASE;
      INSERT INTO p13_reference_samples VALUES (
        endpoint_name, extract(epoch FROM clock_timestamp()-started_at)*1000, true
      );
    EXCEPTION WHEN OTHERS THEN
      INSERT INTO p13_reference_samples VALUES (
        endpoint_name, extract(epoch FROM clock_timestamp()-started_at)*1000, false
      );
    END;
  END LOOP;
END $$;

\echo 'P13 reference benchmark — 13 sequential requests per endpoint; synthetic 5000 rows'
SELECT endpoint,
       count(*) AS requests,
       round((percentile_cont(0.50) WITHIN GROUP (ORDER BY duration_ms))::numeric,2) AS median_ms,
       round((percentile_cont(0.95) WITHIN GROUP (ORDER BY duration_ms))::numeric,2) AS p95_ms,
       round(max(duration_ms)::numeric,2) AS max_ms,
       round((100.0 * count(*) FILTER (WHERE NOT succeeded) / count(*))::numeric,2) AS error_rate_pct
FROM p13_reference_samples
GROUP BY endpoint
ORDER BY endpoint;

ROLLBACK;
