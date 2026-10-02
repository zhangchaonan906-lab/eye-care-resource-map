$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-p5-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$previousPassword = [Environment]::GetEnvironmentVariable('EYE_MAP_POSTGRES_PASSWORD', 'Process')
$previousPort = [Environment]::GetEnvironmentVariable('EYE_MAP_DB_PORT', 'Process')
$previousDatabaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL', 'Process')
$previousEtlDatabaseUrl = [Environment]::GetEnvironmentVariable('ETL_DATABASE_URL', 'Process')
$previousDatabaseAdminUrl = [Environment]::GetEnvironmentVariable('DATABASE_ADMIN_URL', 'Process')
$previousGeocodeDatabaseUrl = [Environment]::GetEnvironmentVariable('GEOCODE_DATABASE_URL', 'Process')
$previousSyncDatabaseUrl = [Environment]::GetEnvironmentVariable('SYNC_DATABASE_URL', 'Process')
$previousPublicApiDatabaseUrl = [Environment]::GetEnvironmentVariable('PUBLIC_API_DATABASE_URL', 'Process')
$previousAdminDatabaseUrl = [Environment]::GetEnvironmentVariable('ADMIN_DATABASE_URL', 'Process')
$portProbe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$portProbe.Start()
$testPort = $portProbe.LocalEndpoint.Port
$portProbe.Stop()
$env:EYE_MAP_POSTGRES_PASSWORD = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
$env:EYE_MAP_DB_PORT = [string]$testPort
Push-Location $repoRoot
try {
  docker compose -p $projectName up -d --wait
  if ($LASTEXITCODE -ne 0) { throw 'Docker database did not become healthy.' }
  $migrationFiles = @(
    '/workspace/db/migrations/001_core.sql',
    '/workspace/db/migrations/002_evidence_location.sql',
    '/workspace/db/migrations/003_published_view.sql',
    '/workspace/db/migrations/004_collector_permissions.sql'
  )
  foreach ($sqlFile in $migrationFiles) {
    docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f $sqlFile
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $sqlFile" }
  }
  docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/004_legacy_source_policy_fixture.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not seed legacy source policy migration fixtures.' }
  docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/005_etl_candidates.sql
  if ($LASTEXITCODE -ne 0) { throw 'P3 ETL migration failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/006_geocoding.sql
  if ($LASTEXITCODE -ne 0) { throw 'P4 geocoding migration failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/007_source_open_data_rights.sql
  if ($LASTEXITCODE -ne 0) { throw 'P5 source rights migration failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/008_source_file_provenance.sql
  if ($LASTEXITCODE -ne 0) { throw 'P5 source file provenance migration failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -f /workspace/scripts/seed-opendata-sources.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not seed the qualified official open-data sources.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/009_real_export_compatibility_before.sql
  if ($LASTEXITCODE -ne 0) { throw 'P5 pre-migration source permission check failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/009_real_export_compatibility.sql
  if ($LASTEXITCODE -ne 0) { throw 'P5 real export compatibility migration failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/migrations/010_etl_import_run_scope.sql
  if ($LASTEXITCODE -ne 0) { throw 'P5 ETL import-run scope migration failed.' }
  foreach ($migration in @('011_public_api.sql','012_nearby_api.sql','013_admin_review.sql','014_incremental_sync.sql','015_public_query_performance.sql')) {
    $sqlFile = "/workspace/db/migrations/$migration"
    docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f $sqlFile
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $sqlFile" }
  }
  $publicApiPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $adminPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $syncPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "api_password=$publicApiPassword" -f /workspace/scripts/provision-public-api-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary public API login.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "admin_password=$adminPassword" -f /workspace/scripts/provision-admin-review-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary admin review login.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "sync_password=$syncPassword" -f /workspace/scripts/provision-sync-worker-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary sync worker login.' }
  $testFiles = @(
    '/workspace/db/tests/001_core.sql',
    '/workspace/db/tests/002_evidence_location.sql',
    '/workspace/db/tests/003_published_view.sql',
    '/workspace/db/tests/004_collector_permissions.sql',
    '/workspace/db/tests/005_etl_candidates.sql',
    '/workspace/db/tests/006_geocoding.sql',
    '/workspace/db/tests/007_source_open_data_rights.sql',
    '/workspace/db/tests/009_real_export_compatibility.sql',
    '/workspace/db/tests/011_public_api.sql',
    '/workspace/db/tests/012_nearby_api.sql',
    '/workspace/db/tests/013_admin_review.sql'
  )
  foreach ($sqlFile in $testFiles) {
    docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f $sqlFile
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $sqlFile" }
  }
  $collectorPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $etlPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  $geocodePassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "collector_password=$collectorPassword" -f /workspace/scripts/provision-collector-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary collector login.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -f /workspace/scripts/seed-fixture-source.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not seed the synthetic source catalog.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/014_incremental_sync.sql
  if ($LASTEXITCODE -ne 0) { throw 'P12 incremental sync database tests failed.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/p13_synthetic_performance.sql
  if ($LASTEXITCODE -ne 0) { throw 'P13 synthetic performance database checks failed.' }
  $env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:$testPort/eye"
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "etl_password=$etlPassword" -f /workspace/scripts/provision-etl-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary ETL login.' }
  $env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$etlPassword@127.0.0.1:$testPort/eye"
  $env:SYNC_DATABASE_URL = "postgresql://eye_sync_worker_runtime:$syncPassword@127.0.0.1:$testPort/eye"
  $env:PUBLIC_API_DATABASE_URL = "postgresql://eye_public_api_runtime:$publicApiPassword@127.0.0.1:$testPort/eye"
  $env:ADMIN_DATABASE_URL = "postgresql://eye_admin_review_runtime:$adminPassword@127.0.0.1:$testPort/eye"
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "geocode_password=$geocodePassword" -f /workspace/scripts/provision-geocode-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary geocode login.' }
  $env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$geocodePassword@127.0.0.1:$testPort/eye"
  $env:DATABASE_ADMIN_URL = "postgresql://eye:$env:EYE_MAP_POSTGRES_PASSWORD@127.0.0.1:$testPort/eye"
  Push-Location (Join-Path $repoRoot 'apps/web')
  try {
    npm run test:db
    if ($LASTEXITCODE -ne 0) { throw 'Public API and admin database integration tests failed.' }
  }
  finally {
    Pop-Location
  }
  Push-Location (Join-Path $repoRoot 'services/collector')
  try {
    $cliResult = py -m eye_collector.cli run --source fixture --region 110000 --dry-run --limit 1 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $cliResult.status -ne 'succeeded' -or -not $cliResult.dry_run -or $cliResult.counts.inserted -ne 1) {
      throw 'Collector CLI dry-run verification failed.'
    }
    py -m pytest -m database -q
    if ($LASTEXITCODE -ne 0) { throw 'Collector database integration tests failed.' }
    py -m eye_collector.cli run --source fixture --region 110000 | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Could not populate synthetic fixture snapshots for P3 ETL tests.' }
    py -m pytest -m etl_database -q
    if ($LASTEXITCODE -ne 0) { throw 'P3 ETL database integration tests failed.' }
    $geocodeResult = py -m eye_collector.cli geocode --provider fixture --dry-run --limit 2 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or -not $geocodeResult.dry_run -or $geocodeResult.counts.candidates_read -gt 2) {
      throw 'Geocoding CLI dry-run verification failed.'
    }
    py -m pytest -m geocode_database -q
    if ($LASTEXITCODE -ne 0) { throw 'P4 geocoding database integration tests failed.' }
    if ($env:P5_BEIJING_OFFICIAL_FILE -and $env:P5_SHENZHEN_OFFICIAL_FILE) {
      $previousPythonIoEncoding = [Environment]::GetEnvironmentVariable('PYTHONIOENCODING', 'Process')
      $env:PYTHONIOENCODING = 'ascii:backslashreplace'
      $beijing = py -m eye_collector.cli inspect-file --source beijing-open-data-designated-medical-institutions --file $env:P5_BEIJING_OFFICIAL_FILE | ConvertFrom-Json
      if ($LASTEXITCODE -ne 0 -or $beijing.sha256 -ne '49848ce24856fb28ed542f46c0e5f805c35b19c3fcea0d85d97d0734487fa918' -or $beijing.row_count -ne 4876 -or -not $beijing.schema_match -or -not $beijing.ready_to_import -or $beijing.recommended_first_pilot_limit -ne 50) {
        throw 'Read-only inspection of the official Beijing file did not match the approved file fingerprint and schema.'
      }
      $shenzhen = py -m eye_collector.cli inspect-file --source shenzhen-open-data-baoan-hospital-basic-information --file $env:P5_SHENZHEN_OFFICIAL_FILE | ConvertFrom-Json
      if ($LASTEXITCODE -ne 0 -or $shenzhen.sha256 -ne '9b9554a8553676c906b8b364987ca11d929a204a02fdd3503e23be1cf86348d7' -or $shenzhen.archive_member_sha256 -ne '55a06fd088b436506a4c5692424a07e487159300ad6f191fce046bdbcdd1a129' -or $shenzhen.archive_member_name -ne '宝安区-医院基本信息_2920002800636.xlsx' -or $shenzhen.data_sheet_name -ne '数据集1' -or $shenzhen.row_count -ne 27 -or -not $shenzhen.schema_match -or -not $shenzhen.ready_to_import) {
        throw ('Read-only Shenzhen inspection mismatch: ' + ($shenzhen | ConvertTo-Json -Compress))
      }
      $beijing | ConvertTo-Json -Compress
      $shenzhen | ConvertTo-Json -Compress
      if ($null -eq $previousPythonIoEncoding) {
        Remove-Item Env:\PYTHONIOENCODING -ErrorAction SilentlyContinue
      } else {
        $env:PYTHONIOENCODING = $previousPythonIoEncoding
      }
    }
  }
  finally {
    Pop-Location
  }
}
finally {
  try {
    docker compose -p $projectName down --volumes
    if ($LASTEXITCODE -ne 0) { throw 'Docker database cleanup failed.' }
  }
  finally {
    Pop-Location
    if ($null -eq $previousPassword) {
      Remove-Item Env:\EYE_MAP_POSTGRES_PASSWORD -ErrorAction SilentlyContinue
    } else {
      $env:EYE_MAP_POSTGRES_PASSWORD = $previousPassword
    }
    if ($null -eq $previousPort) {
      Remove-Item Env:\EYE_MAP_DB_PORT -ErrorAction SilentlyContinue
    } else {
      $env:EYE_MAP_DB_PORT = $previousPort
    }
    if ($null -eq $previousDatabaseUrl) {
      Remove-Item Env:\DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:DATABASE_URL = $previousDatabaseUrl
    }
    if ($null -eq $previousEtlDatabaseUrl) {
      Remove-Item Env:\ETL_DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:ETL_DATABASE_URL = $previousEtlDatabaseUrl
    }
    if ($null -eq $previousDatabaseAdminUrl) {
      Remove-Item Env:\DATABASE_ADMIN_URL -ErrorAction SilentlyContinue
    } else {
      $env:DATABASE_ADMIN_URL = $previousDatabaseAdminUrl
    }
    if ($null -eq $previousGeocodeDatabaseUrl) {
      Remove-Item Env:\GEOCODE_DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:GEOCODE_DATABASE_URL = $previousGeocodeDatabaseUrl
    }
    if ($null -eq $previousSyncDatabaseUrl) {
      Remove-Item Env:\\SYNC_DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:SYNC_DATABASE_URL = $previousSyncDatabaseUrl
    }
    if ($null -eq $previousPublicApiDatabaseUrl) {
      Remove-Item Env:\PUBLIC_API_DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:PUBLIC_API_DATABASE_URL = $previousPublicApiDatabaseUrl
    }
    if ($null -eq $previousAdminDatabaseUrl) {
      Remove-Item Env:\ADMIN_DATABASE_URL -ErrorAction SilentlyContinue
    } else {
      $env:ADMIN_DATABASE_URL = $previousAdminDatabaseUrl
    }
  }
}
Write-Host 'P1-P5, P12, P13 disposable database checks passed.'
