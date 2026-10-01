# P1 Database Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立全国眼科医疗资源地图的可迁移数据库基础，保存院区、来源证据、WGS84 坐标，并只通过已核验视图读取可公开机构。

**Architecture:** 本阶段只实现 PostgreSQL/PostGIS 数据模型和 SQL 验证，不创建前端、爬虫或真实医院数据。内部表放入 `app_private` schema；公开查询只读取 `public.published_facilities` 视图，地图 API 在 P7 实现。来源原始记录与字段证据独立保存，便于 P2–P5 审核与去重。

**Tech Stack:** PostgreSQL 17、PostGIS 3.5、SQL migrations、Docker Compose、PowerShell（Windows 本地验证）。目标托管数据库可为 Supabase PostgreSQL；执行远程迁移前须先核对扩展与 schema 权限。

---

**设计依据：** [P0 架构设计](../specs/2026-10-01-eye-care-map-design.md)。本计划只覆盖 P1；P2 采集、P4 地理编码、P7 API、P8 地图不在本次执行范围。

**当前环境：** 2026-10-01 检查到 Docker CLI 已安装，但 Docker 引擎未运行。执行计划时先启动 Docker Desktop，确认 `docker info` 成功。使用的 `postgis/postgis:17-3.5` 是 PostGIS 镜像官方列出的 PostgreSQL 17/PostGIS 3.5 组合。[镜像说明](https://hub.docker.com/r/postgis/postgis/) PostGIS 可以在 Supabase 启用，官方建议放在独立 `extensions` schema；本地镜像若已在 `public` 安装扩展，迁移通过 `search_path` 兼容现状，而不执行破坏性迁移。[Supabase PostGIS 指南](https://supabase.com/docs/guides/database/extensions/postgis)

## 文件分工

| 文件 | 单一职责 |
| --- | --- |
| `compose.yaml` | 本地 PostgreSQL/PostGIS 测试数据库，不含生产配置 |
| `db/migrations/001_core.sql` | 扩展、地区、机构主体、来源登记、院区核心表 |
| `db/migrations/002_evidence_location.sql` | 导入批次、原始记录、字段证据、候选/重复审核、WGS84 点位和审计 |
| `db/migrations/003_published_view.sql` | 读取索引和已发布视图 |
| `db/tests/001_core.sql` | 核心表与约束的事务内验证 |
| `db/tests/002_evidence_location.sql` | 原始来源幂等键、证据关联、空间距离验证 |
| `db/tests/003_published_view.sql` | 只有有审核证据和可信坐标的发布记录可见 |
| `scripts/test-db.ps1` | 顺序应用迁移并运行三组 SQL 测试 |

## Task 1: 本地数据库验证容器

**Files:**
- Create: `compose.yaml`

- [ ] **Step 1: 创建测试数据库配置**

```yaml
name: eye-map

services:
  db:
    image: postgis/postgis:17-3.5
    environment:
      POSTGRES_USER: eye
      POSTGRES_PASSWORD: eye_local_only
      POSTGRES_DB: eye
    volumes:
      - eye_pgdata:/var/lib/postgresql/data
      - ./db:/workspace/db:ro
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U eye -d eye"]
      interval: 2s
      timeout: 2s
      retries: 30

volumes:
  eye_pgdata:
```

- [ ] **Step 2: 验证配置并启动**

Run: `docker compose config --quiet`

Expected: exit code 0。顶层 `name` 使中文目录下的 Compose 项目名稳定。随后运行 `docker compose up -d --wait`，Expected: `db` 为 healthy；`docker compose exec -T db psql -U eye -d eye -Atqc 'select current_database()'` 输出 `eye`。若 daemon 不可用，先启动 Docker Desktop，再重复命令。

- [ ] **Step 3: Commit**

Run: `git add compose.yaml; git commit -m "build: add local PostGIS database"`

Expected: 新提交只包含 `compose.yaml`。

## Task 2: 核心地区、机构与来源 Schema

**Files:**
- Create: `db/tests/001_core.sql`
- Create: `db/migrations/001_core.sql`

- [ ] **Step 1: 先写核心表契约测试**

Create `db/tests/001_core.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000001', '110000', '北京市', 'province', '2026');
INSERT INTO app_private.organizations (id, canonical_name)
VALUES ('00000000-0000-0000-0000-000000000002', '测试医院');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status)
VALUES ('00000000-0000-0000-0000-000000000003', '测试来源', 'https://example.org/list', '测试许可', 'approved');
INSERT INTO app_private.facilities
  (id, organization_id, name, normalized_name, category, region_id, address, ophthalmology_status)
VALUES
  ('00000000-0000-0000-0000-000000000004',
   '00000000-0000-0000-0000-000000000002',
   '测试医院东院区', '测试医院东院区', 'general_hospital_ophthalmology',
   '00000000-0000-0000-0000-000000000001', '北京市东城区测试路1号', 'verified');
DO $$
BEGIN
  IF (SELECT count(*) FROM app_private.facilities WHERE name = '测试医院东院区') <> 1 THEN
    RAISE EXCEPTION 'core facility insert failed';
  END IF;
  BEGIN
    INSERT INTO app_private.facilities
      (name, normalized_name, category, region_id, address)
    VALUES ('错误类型', '错误类型', 'bad_category',
      '00000000-0000-0000-0000-000000000001', '测试地址');
    RAISE EXCEPTION 'invalid category was accepted';
  EXCEPTION WHEN check_violation THEN
    NULL;
  END;
END $$;
ROLLBACK;
```

- [ ] **Step 2: 确认测试先失败**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/001_core.sql`

Expected: 非零退出，提示 `schema "app_private" does not exist` 或 `relation ... does not exist`。

- [ ] **Step 3: 实现核心迁移**

Create `db/migrations/001_core.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS app_private;
REVOKE ALL ON SCHEMA app_private FROM PUBLIC;
SET LOCAL search_path = app_private, public, extensions;

CREATE TABLE app_private.regions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  adcode text NOT NULL CHECK (adcode ~ '^[0-9]{6}$'),
  name text NOT NULL,
  level text NOT NULL CHECK (level IN ('province', 'city', 'district')),
  parent_id uuid REFERENCES app_private.regions(id),
  version text NOT NULL,
  valid_from date,
  valid_to date,
  UNIQUE (adcode, version),
  CHECK (valid_to IS NULL OR valid_from IS NULL OR valid_to >= valid_from)
);

CREATE TABLE app_private.organizations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  canonical_name text NOT NULL,
  registration_id text,
  ownership_type text CHECK (ownership_type IN ('public', 'private', 'unknown')),
  created_at timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX organizations_registration_id_uq
  ON app_private.organizations (registration_id) WHERE registration_id IS NOT NULL;

CREATE TABLE app_private.source_catalog (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  name text NOT NULL,
  url text NOT NULL CHECK (url ~ '^https://'),
  owner text,
  use_basis text NOT NULL,
  permitted_fields text[] NOT NULL DEFAULT '{}',
  access_policy text,
  status text NOT NULL DEFAULT 'pending'
    CHECK (status IN ('pending', 'approved', 'suspended')),
  reviewed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE app_private.facilities (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid REFERENCES app_private.organizations(id),
  name text NOT NULL,
  normalized_name text NOT NULL,
  campus_name text,
  category text NOT NULL CHECK (category IN
    ('eye_specialty_hospital', 'general_hospital_ophthalmology',
     'ophthalmology_center', 'eye_clinic', 'unknown')),
  region_id uuid NOT NULL REFERENCES app_private.regions(id),
  address text NOT NULL,
  phone text,
  website text CHECK (website IS NULL OR website ~ '^https://'),
  hospital_level text,
  hospital_grade text,
  ophthalmology_status text NOT NULL DEFAULT 'unknown'
    CHECK (ophthalmology_status IN ('unknown', 'claimed', 'verified', 'rejected')),
  verification_status text NOT NULL DEFAULT 'candidate'
    CHECK (verification_status IN ('candidate', 'in_review', 'verified', 'published', 'withdrawn')),
  published_at timestamptz,
  last_verified_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (verification_status <> 'published' OR published_at IS NOT NULL)
);
COMMIT;
```

- [ ] **Step 4: 应用迁移并重新运行测试**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/001_core.sql`

Expected: exit code 0，输出 `COMMIT`。再运行 Step 2 的测试命令，Expected: exit code 0，输出 `ROLLBACK`。

- [ ] **Step 5: Commit**

Run: `git add db/tests/001_core.sql db/migrations/001_core.sql; git commit -m "feat(db): add core eye care schema"`

## Task 3: 来源证据、候选与空间位置

契约：重复候选使用 `duplicate_case_candidates` 关联表，以复合主键拒绝重复成员，外键保证候选存在，删除案件级联清理成员。pending 案件允许逐行组装；P11 解决案件的事务必须检查成员至少为 2，并在后续成员变更中维护该规则。`matched` 候选必须关联机构，`unmatched`/`rejected` 必须没有机构，`needs_review` 两种均允许。坐标通过 `coordinate_source_record_id` 追溯具体来源快照。导入区域为六位数字，running 的结束时间必须为空，终态必须非空。测试覆盖合法匹配、候选状态矛盾、成员外键/唯一性/级联、坐标来源外键、区域与结束时间约束。

**Files:**
- Create: `db/tests/002_evidence_location.sql`
- Create: `db/migrations/002_evidence_location.sql`

- [ ] **Step 1: 先写来源与坐标契约测试**

Create `db/tests/002_evidence_location.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000011', '440000', '广东省', 'province', '2026');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status)
VALUES ('00000000-0000-0000-0000-000000000012', '测试来源', 'https://example.org/guangdong', '测试许可', 'approved');
INSERT INTO app_private.facilities
  (id, name, normalized_name, category, region_id, address, ophthalmology_status)
VALUES ('00000000-0000-0000-0000-000000000013', '测试眼科医院', '测试眼科医院',
  'eye_specialty_hospital', '00000000-0000-0000-0000-000000000011',
  '广州市测试路1号', 'verified');
INSERT INTO app_private.import_runs (id, source_id, region_code, status)
VALUES ('00000000-0000-0000-0000-000000000014',
  '00000000-0000-0000-0000-000000000012', '440000', 'running');
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000015',
  '00000000-0000-0000-0000-000000000012', 'hospital-1', '{"name":"测试眼科医院"}',
  'https://example.org/guangdong/1', repeat('a', 64),
  '00000000-0000-0000-0000-000000000014');
INSERT INTO app_private.facility_evidence
  (facility_id, source_record_id, field_name, field_value, confidence)
VALUES ('00000000-0000-0000-0000-000000000013',
  '00000000-0000-0000-0000-000000000015', 'ophthalmology_status',
  '"verified"'::jsonb, 1.0);
INSERT INTO app_private.facility_locations
  (facility_id, geog_wgs84, coordinate_source_record_id, location_status)
VALUES ('00000000-0000-0000-0000-000000000013',
  ST_SetSRID(ST_MakePoint(113.2644, 23.1291), 4326)::geography,
  '00000000-0000-0000-0000-000000000015', 'verified');
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM app_private.facility_locations
    WHERE facility_id = '00000000-0000-0000-0000-000000000013'
      AND ST_DWithin(geog_wgs84,
        ST_SetSRID(ST_MakePoint(113.2644, 23.1291), 4326)::geography, 10)
  ) THEN
    RAISE EXCEPTION 'WGS84 nearby query failed';
  END IF;
  BEGIN
    INSERT INTO app_private.source_records
      (source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
    VALUES ('00000000-0000-0000-0000-000000000012', 'hospital-1', '{}',
      'https://example.org/guangdong/1', repeat('a', 64),
      '00000000-0000-0000-0000-000000000014');
    RAISE EXCEPTION 'duplicate source snapshot was accepted';
  EXCEPTION WHEN unique_violation THEN
    NULL;
  END;
END $$;
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000016',
  '00000000-0000-0000-0000-000000000012', 'hospital-2', '{}',
  'https://example.org/guangdong/2', repeat('b', 64),
  '00000000-0000-0000-0000-000000000014');
INSERT INTO app_private.candidate_records
  (id, source_record_id, parsed_fields, match_status, proposed_facility_id)
VALUES
  ('00000000-0000-0000-0000-000000000017',
   '00000000-0000-0000-0000-000000000015', '{}', 'matched',
   '00000000-0000-0000-0000-000000000013'),
  ('00000000-0000-0000-0000-000000000018',
   '00000000-0000-0000-0000-000000000016', '{}', 'unmatched', NULL);
-- Pending cases may be assembled one membership at a time.
INSERT INTO app_private.duplicate_cases (id, reason)
VALUES ('00000000-0000-0000-0000-000000000019', '测试重复候选');
INSERT INTO app_private.duplicate_case_candidates (duplicate_case_id, candidate_record_id)
VALUES
  ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000017'),
  ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000018');
INSERT INTO app_private.import_runs (source_id, region_code, status, ended_at)
VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'succeeded', now());
DO $$
BEGIN
  IF (SELECT count(*) FROM app_private.duplicate_case_candidates
      WHERE duplicate_case_id = '00000000-0000-0000-0000-000000000019') <> 2 THEN
    RAISE EXCEPTION 'duplicate case membership count is wrong';
  END IF;
  BEGIN
    INSERT INTO app_private.duplicate_case_candidates VALUES
      ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000099');
    RAISE EXCEPTION 'nonexistent candidate membership was accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.duplicate_case_candidates VALUES
      ('00000000-0000-0000-0000-000000000019', '00000000-0000-0000-0000-000000000017');
    RAISE EXCEPTION 'duplicate candidate membership was accepted';
  EXCEPTION WHEN unique_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records SET proposed_facility_id = NULL
      WHERE id = '00000000-0000-0000-0000-000000000017';
    RAISE EXCEPTION 'matched candidate without facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records
      SET proposed_facility_id = '00000000-0000-0000-0000-000000000013'
      WHERE id = '00000000-0000-0000-0000-000000000018';
    RAISE EXCEPTION 'unmatched candidate with facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.candidate_records SET match_status = 'rejected'
      WHERE id = '00000000-0000-0000-0000-000000000017';
    RAISE EXCEPTION 'rejected candidate with facility was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  UPDATE app_private.candidate_records SET match_status = 'needs_review'
    WHERE id IN ('00000000-0000-0000-0000-000000000017', '00000000-0000-0000-0000-000000000018');
  UPDATE app_private.candidate_records SET match_status = 'rejected'
    WHERE id = '00000000-0000-0000-0000-000000000018';
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status)
    VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'failed');
    RAISE EXCEPTION 'terminal import without ended_at was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status, ended_at)
    VALUES ('00000000-0000-0000-0000-000000000012', '440000', 'running', now());
    RAISE EXCEPTION 'running import with ended_at was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    INSERT INTO app_private.import_runs (source_id, region_code, status)
    VALUES ('00000000-0000-0000-0000-000000000012', '44000', 'running');
    RAISE EXCEPTION 'invalid import region code was accepted';
  EXCEPTION WHEN check_violation THEN NULL;
  END;
  BEGIN
    UPDATE app_private.facility_locations
      SET coordinate_source_record_id = '00000000-0000-0000-0000-000000000099'
      WHERE facility_id = '00000000-0000-0000-0000-000000000013';
    RAISE EXCEPTION 'nonexistent coordinate source record was accepted';
  EXCEPTION WHEN foreign_key_violation THEN NULL;
  END;
  DELETE FROM app_private.duplicate_cases WHERE id = '00000000-0000-0000-0000-000000000019';
  IF EXISTS (SELECT 1 FROM app_private.duplicate_case_candidates
      WHERE duplicate_case_id = '00000000-0000-0000-0000-000000000019') THEN
    RAISE EXCEPTION 'duplicate case deletion did not cascade';
  END IF;
END $$;
ROLLBACK;
```

- [ ] **Step 2: 确认测试先失败**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/002_evidence_location.sql`

Expected: 在仅应用 001_core 的新库中非零退出，提示 `relation "app_private.import_runs" does not exist`。审核修复时使用独立项目 `eye-p1-task3-review`：先运行 `docker compose -p eye-p1-task3-review up -d --wait` 和 001_core 迁移，再以相同 `-p` 参数运行测试。原版 002 迁移后，新测试还应因缺少 `coordinate_source_record_id` 失败。

- [ ] **Step 3: 实现来源与坐标迁移**

Create `db/migrations/002_evidence_location.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
CREATE TABLE app_private.import_runs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id),
  region_code text NOT NULL CHECK (region_code ~ '^[0-9]{6}$'),
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  status text NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
  counts jsonb NOT NULL DEFAULT '{}'::jsonb,
  error_summary text,
  CHECK ((status = 'running' AND ended_at IS NULL)
    OR (status IN ('succeeded', 'failed', 'cancelled') AND ended_at IS NOT NULL))
);
CREATE TABLE app_private.source_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id uuid NOT NULL REFERENCES app_private.source_catalog(id),
  source_key text NOT NULL,
  raw_payload jsonb NOT NULL,
  source_url text NOT NULL CHECK (source_url ~ '^https://'),
  collected_at timestamptz NOT NULL DEFAULT now(),
  content_hash text NOT NULL CHECK (content_hash ~ '^[a-f0-9]{64}$'),
  import_run_id uuid NOT NULL REFERENCES app_private.import_runs(id),
  UNIQUE (source_id, source_key, content_hash)
);
CREATE TABLE app_private.candidate_records (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  source_record_id uuid NOT NULL UNIQUE REFERENCES app_private.source_records(id),
  parsed_fields jsonb NOT NULL,
  match_status text NOT NULL DEFAULT 'unmatched'
    CHECK (match_status IN ('unmatched', 'matched', 'needs_review', 'rejected')),
  proposed_facility_id uuid REFERENCES app_private.facilities(id),
  CHECK ((match_status = 'matched' AND proposed_facility_id IS NOT NULL)
    OR (match_status IN ('unmatched', 'rejected') AND proposed_facility_id IS NULL)
    OR match_status = 'needs_review')
);
CREATE TABLE app_private.facility_evidence (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  facility_id uuid NOT NULL REFERENCES app_private.facilities(id),
  source_record_id uuid NOT NULL REFERENCES app_private.source_records(id),
  field_name text NOT NULL,
  field_value jsonb NOT NULL,
  confidence numeric(3,2) CHECK (confidence BETWEEN 0 AND 1),
  reviewed_at timestamptz,
  UNIQUE (facility_id, source_record_id, field_name)
);
CREATE TABLE app_private.duplicate_cases (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  reason text NOT NULL,
  score numeric(3,2) CHECK (score BETWEEN 0 AND 1),
  resolution text NOT NULL DEFAULT 'pending'
    CHECK (resolution IN ('pending', 'merge', 'separate', 'reject')),
  reviewer_id uuid,
  resolved_at timestamptz
);
-- Pending cases allow incremental membership assembly. P11 must ensure >=2
-- members in the transaction that resolves a case, and preserve that invariant.
CREATE TABLE app_private.duplicate_case_candidates (
  duplicate_case_id uuid NOT NULL REFERENCES app_private.duplicate_cases(id) ON DELETE CASCADE,
  candidate_record_id uuid NOT NULL REFERENCES app_private.candidate_records(id),
  PRIMARY KEY (duplicate_case_id, candidate_record_id)
);
CREATE TABLE app_private.facility_locations (
  facility_id uuid PRIMARY KEY REFERENCES app_private.facilities(id) ON DELETE CASCADE,
  geog_wgs84 geography(Point, 4326) NOT NULL,
  coordinate_source_record_id uuid NOT NULL REFERENCES app_private.source_records(id),
  accuracy_m integer CHECK (accuracy_m IS NULL OR accuracy_m >= 0),
  location_status text NOT NULL DEFAULT 'candidate'
    CHECK (location_status IN ('candidate', 'verified', 'rejected')),
  verified_at timestamptz
);
CREATE TABLE app_private.audit_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_id uuid,
  entity text NOT NULL,
  entity_id uuid NOT NULL,
  action text NOT NULL,
  before_value jsonb,
  after_value jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);
COMMIT;
```

- [ ] **Step 4: 应用迁移并重新运行测试**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/002_evidence_location.sql`

Expected: `COMMIT`。审核修复应先运行 `docker compose -p eye-p1-task3-review down --volumes`，重建该专用测试项目，再依次应用 001_core、002_evidence_location；所有命令添加 `-p eye-p1-task3-review`。随后运行 001_core 与 002_evidence_location 两组测试，Expected: 两组均 `ROLLBACK` 且 exit code 0。再验证 `docker compose -p eye-p1-task3-review config --quiet`、数据库 healthy 与 `select current_database()` 输出 `eye`，最后清理该临时项目。

- [ ] **Step 5: Commit**

Run: `git add db/tests/002_evidence_location.sql db/migrations/002_evidence_location.sql; git commit -m "feat(db): add provenance and locations"`

## Task 4: 查询索引与已发布视图

**Files:**
- Create: `db/tests/003_published_view.sql`
- Create: `db/migrations/003_published_view.sql`

- [ ] **Step 1: 先写发布门槛测试**

Create `db/tests/003_published_view.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
INSERT INTO app_private.regions (id, adcode, name, level, version)
VALUES ('00000000-0000-0000-0000-000000000021', '110000', '北京市', 'province', '2026');
INSERT INTO app_private.source_catalog (id, name, url, use_basis, status)
VALUES ('00000000-0000-0000-0000-000000000022', '已准入来源', 'https://example.org/source', '测试许可', 'approved');
INSERT INTO app_private.import_runs (id, source_id, region_code, status, ended_at)
VALUES ('00000000-0000-0000-0000-000000000023',
  '00000000-0000-0000-0000-000000000022', '110000', 'succeeded', now());
INSERT INTO app_private.source_records
  (id, source_id, source_key, raw_payload, source_url, content_hash, import_run_id)
VALUES ('00000000-0000-0000-0000-000000000024',
  '00000000-0000-0000-0000-000000000022', 'eye-1', '{}',
  'https://example.org/source/1', repeat('b', 64),
  '00000000-0000-0000-0000-000000000023');
INSERT INTO app_private.facilities
  (id, name, normalized_name, category, region_id, address,
   ophthalmology_status, verification_status, published_at, last_verified_at)
VALUES
  ('00000000-0000-0000-0000-000000000025', '可见医院', '可见医院',
   'eye_specialty_hospital', '00000000-0000-0000-0000-000000000021',
   '北京市测试路1号', 'verified', 'published', now(), now()),
  ('00000000-0000-0000-0000-000000000026', '缺证据医院', '缺证据医院',
   'eye_specialty_hospital', '00000000-0000-0000-0000-000000000021',
   '北京市测试路2号', 'verified', 'published', now(), now());
INSERT INTO app_private.facility_locations
  (facility_id, geog_wgs84, coordinate_source_record_id, location_status, verified_at)
VALUES
  ('00000000-0000-0000-0000-000000000025',
   ST_SetSRID(ST_MakePoint(116.4, 39.9), 4326)::geography,
   '00000000-0000-0000-0000-000000000024', 'verified', now()),
  ('00000000-0000-0000-0000-000000000026',
   ST_SetSRID(ST_MakePoint(116.41, 39.91), 4326)::geography,
   '00000000-0000-0000-0000-000000000024', 'verified', now());
INSERT INTO app_private.facility_evidence
  (facility_id, source_record_id, field_name, field_value, confidence)
VALUES
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'ophthalmology_status',
   '"verified"'::jsonb, 1.0),
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'name',
   '"可见医院"'::jsonb, 1.0),
  ('00000000-0000-0000-0000-000000000025',
   '00000000-0000-0000-0000-000000000024', 'address',
   '"北京市测试路1号"'::jsonb, 1.0);
DO $$
BEGIN
  IF (SELECT count(*) FROM public.published_facilities
      WHERE id IN ('00000000-0000-0000-0000-000000000025',
                   '00000000-0000-0000-0000-000000000026')) <> 1 THEN
    RAISE EXCEPTION 'published view did not enforce evidence gate';
  END IF;
  IF NOT EXISTS (SELECT 1 FROM public.published_facilities
      WHERE id = '00000000-0000-0000-0000-000000000025'
        AND longitude_wgs84 BETWEEN 116.39 AND 116.41
        AND latitude_wgs84 BETWEEN 39.89 AND 39.91) THEN
    RAISE EXCEPTION 'published location fields are wrong';
  END IF;
END $$;
ROLLBACK;
```

- [ ] **Step 2: 确认测试先失败**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/003_published_view.sql`

Expected: 非零退出，提示 `relation "public.published_facilities" does not exist`。

- [ ] **Step 3: 实现索引和视图**

Create `db/migrations/003_published_view.sql`:

```sql
\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;
CREATE INDEX facilities_region_category_published_idx
  ON app_private.facilities (region_id, category)
  WHERE verification_status = 'published';
CREATE INDEX facilities_normalized_name_idx
  ON app_private.facilities (normalized_name);
CREATE INDEX source_records_lookup_idx
  ON app_private.source_records (source_id, source_key);
CREATE INDEX facility_evidence_lookup_idx
  ON app_private.facility_evidence (facility_id, field_name);
CREATE INDEX facility_locations_geog_idx
  ON app_private.facility_locations USING GIST (geog_wgs84);

CREATE VIEW public.published_facilities WITH (security_barrier = true) AS
SELECT f.id, f.name, f.campus_name, f.category, f.address,
       f.phone, f.website, f.hospital_level, f.hospital_grade,
       r.adcode, r.name AS region_name, f.last_verified_at,
       l.geog_wgs84,
       ST_X(l.geog_wgs84::geometry) AS longitude_wgs84,
       ST_Y(l.geog_wgs84::geometry) AS latitude_wgs84
FROM app_private.facilities AS f
JOIN app_private.regions AS r ON r.id = f.region_id
JOIN app_private.facility_locations AS l ON l.facility_id = f.id
JOIN app_private.source_records AS coordinate_record
  ON coordinate_record.id = l.coordinate_source_record_id
JOIN app_private.source_catalog AS coordinate_source
  ON coordinate_source.id = coordinate_record.source_id
WHERE f.verification_status = 'published'
  AND f.published_at IS NOT NULL
  AND f.last_verified_at IS NOT NULL
  AND f.ophthalmology_status = 'verified'
  AND l.location_status = 'verified'
  AND l.verified_at IS NOT NULL
  AND coordinate_source.status = 'approved'
  AND EXISTS (
    SELECT 1 FROM app_private.facility_evidence AS e
    JOIN app_private.source_records AS sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog AS sc ON sc.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'ophthalmology_status'
      AND e.field_value = '"verified"'::jsonb
      AND sc.status = 'approved'
  )
  AND EXISTS (
    SELECT 1 FROM app_private.facility_evidence AS e
    JOIN app_private.source_records AS sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog AS sc ON sc.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'name'
      AND e.field_value = to_jsonb(f.name)
      AND sc.status = 'approved'
  )
  AND EXISTS (
    SELECT 1 FROM app_private.facility_evidence AS e
    JOIN app_private.source_records AS sr ON sr.id = e.source_record_id
    JOIN app_private.source_catalog AS sc ON sc.id = sr.source_id
    WHERE e.facility_id = f.id
      AND e.field_name = 'address'
      AND e.field_value = to_jsonb(f.address)
      AND sc.status = 'approved'
  );
REVOKE ALL ON public.published_facilities FROM PUBLIC;
COMMIT;
```

- [ ] **Step 4: 应用迁移并重新运行测试**

Run: `docker compose exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/003_published_view.sql`

Expected: `COMMIT`。再运行 Step 2 测试命令，Expected: `ROLLBACK` 且 exit code 0。

- [ ] **Step 5: Commit**

Run: `git add db/tests/003_published_view.sql db/migrations/003_published_view.sql; git commit -m "feat(db): expose verified facilities view"`

## Task 5: 一键验证与 P1 验收

**Files:**
- Create: `scripts/test-db.ps1`

- [ ] **Step 1: 创建验证脚本**

Create `scripts/test-db.ps1`:

```powershell
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-p1-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
Push-Location $repoRoot
try {
  docker compose -p $projectName up -d --wait
  if ($LASTEXITCODE -ne 0) { throw 'Docker database did not become healthy.' }
  $sqlFiles = @(
    '/workspace/db/migrations/001_core.sql',
    '/workspace/db/migrations/002_evidence_location.sql',
    '/workspace/db/migrations/003_published_view.sql',
    '/workspace/db/tests/001_core.sql',
    '/workspace/db/tests/002_evidence_location.sql',
    '/workspace/db/tests/003_published_view.sql'
  )
  foreach ($sqlFile in $sqlFiles) {
    docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f $sqlFile
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $sqlFile" }
  }
  Write-Host 'P1 database checks passed.'
}
finally {
  docker compose -p $projectName down --volumes
  Pop-Location
}
```

- [ ] **Step 2: 在全新数据库运行**

Run: `pwsh -NoProfile -File scripts/test-db.ps1`

Expected: 三个迁移各输出 `COMMIT`，三个测试各输出 `ROLLBACK`，末行 `P1 database checks passed.`。脚本使用随机 Compose project name 创建专用测试卷，结束时只清理该 project 创建的容器和卷；不会操作其他数据库卷。

- [ ] **Step 3: 验证空间索引与权限边界**

Run: `docker compose exec -T db psql -U eye -d eye -Atqc "select indexname from pg_indexes where schemaname='app_private' and indexname='facility_locations_geog_idx'"`

Expected: `facility_locations_geog_idx`。再运行 `docker compose exec -T db psql -U eye -d eye -Atqc "select count(*) from pg_class c cross join lateral aclexplode(coalesce(c.relacl,acldefault('r',c.relowner))) a where c.oid='public.published_facilities'::regclass and a.grantee=0 and a.privilege_type='SELECT'"`，Expected: `0`（没有授予 PUBLIC 的 SELECT）。

- [ ] **Step 4: Commit**

Run: `git add scripts/test-db.ps1; git commit -m "test(db): add P1 migration verification"`

## P1 完成门槛

- 三个 migration 在全新 PostgreSQL/PostGIS 17/3.5 库顺序成功。
- 三组事务测试通过：类型约束、来源快照幂等、WGS84 米制查询、发布证据门槛。
- `app_private` 内部表无匿名直接读取路径；`published_facilities` 视图默认不授予 `PUBLIC`。
- 空间索引存在；迁移文件和验证脚本已提交，`git status --short` 为空。
- 记录 Docker 环境、PostGIS 扩展所在 schema、SQL 测试输出。此阶段没有真实数据、前端或全国覆盖声明。

## 自检与范围边界

本计划对应 P0 的数据模型、来源证据、空间点位和已发布查询门槛；采集适配器、后台权限、坐标服务许可、真实数据质量和地图 UI 分别留给 P2、P11、P4、P5、P8。P1 SQL 中的 `confidence` 是证据可信度，不能作为面向用户的医院质量评分。发布视图是读取防线；P11 的发布事务仍需实现状态变更与审计。
