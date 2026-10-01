\set ON_ERROR_STOP on
BEGIN;
SET LOCAL search_path = app_private, public, extensions;

INSERT INTO app_private.source_catalog (
  name, url, owner, use_basis, permitted_fields, access_policy, status, reviewed_at,
  registration_id_reliable, platform, dataset_page, data_provider, open_condition,
  license_url, source_updated_at, data_use_allowed, reuse_allowed,
  app_display_allowed, raw_data_transfer_allowed, raw_data_redistribution_allowed,
  attribution_required, attribution_text, retention_restrictions,
  pilot_group, pilot_group_record_limit
)
SELECT
  source.name, source.dataset_page, source.data_provider, source.use_basis,
  source.permitted_fields, 'manual_only', 'approved', '2026-10-01T00:00:00Z',
  source.registration_id_reliable, source.platform, source.dataset_page,
  source.data_provider, '无条件开放', source.license_url, source.source_updated_at,
  true, true, true, source.raw_data_transfer_allowed,
  source.raw_data_redistribution_allowed, true, source.attribution_text,
  source.retention_restrictions, 'p5-official-open-data', 300
FROM (VALUES
  (
    '北京市公共数据开放平台-医院',
    'https://data.beijing.gov.cn/zyml/wnkfsj/5652.htm',
    '市卫健委',
    '北京市公共数据开放平台法律声明：免费、非排他使用，可自由利用、传播和分享；此行适用其“医院”数据集，无条件开放。下载/API 需注册用户，P5 使用人工下载的官方文件。',
    ARRAY['source_fields', 'name']::text[],
    false,
    '北京市公共数据开放平台',
    '北京市公共数据开放平台',
    'https://data.beijing.gov.cn/gywm/mzsm/index.htm',
    DATE '2024-11-20',
    true,
    true,
    'unrestricted'
  ),
  (
    '北京市公共数据开放平台-定点医疗机构信息',
    'https://data.beijing.gov.cn/zyml/ajg/sybj/17425.htm',
    '市医保局',
    '北京市公共数据开放平台法律声明：免费、非排他使用，可自由利用、传播和分享；此行适用“定点医疗机构信息”数据集，无条件开放。下载/API 需注册用户，P5 使用人工下载的官方文件。',
    ARRAY['source_fields', 'name', 'address', 'administrative_context', 'hospital_grade', 'source_category', 'registration_id']::text[],
    true,
    '北京市公共数据开放平台',
    '北京市公共数据开放平台',
    'https://data.beijing.gov.cn/gywm/mzsm/index.htm',
    DATE '2026-08-13',
    true,
    true,
    'unrestricted'
  ),
  (
    '深圳市政府数据开放平台-宝安区-医院基本信息',
    'https://opendata.sz.gov.cn/data/dataSet/toDataDetails/29200_02800636',
    '宝安区人民政府',
    '深圳市政府数据开放平台服务条款：注册用户可免费获取、使用、利用及再利用，须署名；禁止有偿或无偿转让原始数据。平台下架后不得继续保存或使用。该宝安区数据集无条件开放，使用人工下载文件。',
    ARRAY['source_fields', 'source_reference_id', 'name', 'administrative_context', 'address', 'hospital_level', 'hospital_grade', 'source_category', 'specialties']::text[],
    false,
    '深圳市政府数据开放平台',
    '深圳市政府数据开放平台',
    'https://opendata.sz.gov.cn/maintenance/forward/toTermOfService',
    DATE '2025-04-15',
    false,
    false,
    'delete_on_withdrawal'
  )
) AS source (
  name, dataset_page, data_provider, use_basis, permitted_fields,
  registration_id_reliable, platform, attribution_text, license_url,
  source_updated_at, raw_data_transfer_allowed, raw_data_redistribution_allowed,
  retention_restrictions
)
WHERE NOT EXISTS (
  SELECT 1 FROM app_private.source_catalog existing
  WHERE existing.name = source.name AND existing.url = source.dataset_page
);

COMMIT;
