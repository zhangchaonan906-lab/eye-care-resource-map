$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-db-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$backupRoot = Join-Path ([IO.Path]::GetTempPath()) ('eye-map-p14-backup-' + [guid]::NewGuid().ToString('N'))
$environmentNames = @(
  'EYE_MAP_POSTGRES_PASSWORD', 'EYE_MAP_DB_PORT', 'DATABASE_URL', 'ETL_DATABASE_URL',
  'DATABASE_ADMIN_URL', 'GEOCODE_DATABASE_URL', 'PUBLIC_API_DATABASE_URL',
  'ADMIN_DATABASE_URL', 'SYNC_DATABASE_URL', 'P13_COLLECTOR_PASSWORD', 'P13_ETL_PASSWORD',
  'P13_GEOCODE_PASSWORD', 'P13_PUBLIC_API_PASSWORD', 'P13_ADMIN_DATABASE_PASSWORD', 'P13_SYNC_PASSWORD', 'P13_CORRECTION_PASSWORD', 'APP_ENV'
)
$environmentNames += @('P14_BACKUP_DIR','P14_PG_TOOL_CONTAINER','RESTORE_DATABASE_URL','RESTORE_CONFIRM','RESTORE_BACKUP_FILE')
$previousEnvironment = @{}
foreach ($name in $environmentNames) { $previousEnvironment[$name] = [Environment]::GetEnvironmentVariable($name, 'Process') }
$portProbe = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback, 0)
$portProbe.Start()
$testPort = $portProbe.LocalEndpoint.Port
$portProbe.Stop()
function New-TestSecret {
  $bytes = New-Object byte[] 32
  $generator = [Security.Cryptography.RandomNumberGenerator]::Create()
  try { $generator.GetBytes($bytes) } finally { $generator.Dispose() }
  ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

try {
  $env:EYE_MAP_DB_PORT = [string]$testPort
  $env:EYE_MAP_POSTGRES_PASSWORD = New-TestSecret
  $env:P13_COLLECTOR_PASSWORD = New-TestSecret
  $env:P13_ETL_PASSWORD = New-TestSecret
  $env:P13_GEOCODE_PASSWORD = New-TestSecret
  $env:P13_PUBLIC_API_PASSWORD = New-TestSecret
  $env:P13_ADMIN_DATABASE_PASSWORD = New-TestSecret
  $env:P13_SYNC_PASSWORD = New-TestSecret
  $env:P13_CORRECTION_PASSWORD = New-TestSecret
  $env:DATABASE_URL = "postgresql://eye_collector_runtime:$env:P13_COLLECTOR_PASSWORD@127.0.0.1:$testPort/eye"
  $env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$env:P13_ETL_PASSWORD@127.0.0.1:$testPort/eye"
  $env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$env:P13_GEOCODE_PASSWORD@127.0.0.1:$testPort/eye"
  $env:PUBLIC_API_DATABASE_URL = "postgresql://eye_public_api_runtime:$env:P13_PUBLIC_API_PASSWORD@127.0.0.1:$testPort/eye"
  $env:ADMIN_DATABASE_URL = "postgresql://eye_admin_review_runtime:$env:P13_ADMIN_DATABASE_PASSWORD@127.0.0.1:$testPort/eye"
    $env:SYNC_DATABASE_URL = "postgresql://eye_sync_worker_runtime:$env:P13_SYNC_PASSWORD@127.0.0.1:$testPort/eye"
    $env:CORRECTION_DATABASE_URL = "postgresql://eye_correction_runtime:$env:P13_CORRECTION_PASSWORD@127.0.0.1:$testPort/eye"
  $env:DATABASE_ADMIN_URL = "postgresql://eye:$env:EYE_MAP_POSTGRES_PASSWORD@127.0.0.1:$testPort/eye"
  Push-Location $repoRoot
  try {
    docker compose -p $projectName up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Disposable PostGIS did not become healthy.' }
    node scripts/db-test-bootstrap.mjs $projectName
    if ($LASTEXITCODE -ne 0) { throw 'P1–P13 database bootstrap/regression SQL failed.' }
    $containerId = (docker compose -p $projectName ps -q db | Out-String).Trim()
    docker compose -p $projectName exec -T db dropdb -U eye --if-exists p14_migration_clean
    if ($LASTEXITCODE -ne 0) { throw 'Could not clear the disposable migration target.' }
    docker compose -p $projectName exec -T db createdb -U eye --template=template0 p14_migration_clean
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the clean migration target.' }
    docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d p14_migration_clean -v ON_ERROR_STOP=1 -c 'CREATE EXTENSION postgis WITH SCHEMA public'
    if ($LASTEXITCODE -ne 0) { throw 'Could not provision the required PostGIS extension in the clean migration target.' }
    $sourceAdminUrl = $env:DATABASE_ADMIN_URL
    $env:DATABASE_ADMIN_URL = $sourceAdminUrl -replace '/eye$','/p14_migration_clean'
    $env:P14_PG_TOOL_CONTAINER = $containerId
    node scripts/apply-migrations.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Ordered migration application failed on an empty database.' }
    node scripts/apply-migrations.mjs
    if ($LASTEXITCODE -ne 0) { throw 'Migration runner idempotent replay verification failed.' }
    $migrationCount = (docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d p14_migration_clean -A -t -c "SELECT count(*) FROM public.schema_migrations" | Out-String).Trim()
    if ($LASTEXITCODE -ne 0 -or $migrationCount -ne '16') { throw "Migration registry count is not 16: $migrationCount" }
    $env:DATABASE_ADMIN_URL = $sourceAdminUrl
    Remove-Item Env:P14_PG_TOOL_CONTAINER -ErrorAction SilentlyContinue
    py -m pip install -e 'services/collector[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Collector development dependencies could not be installed.' }
    Push-Location (Join-Path $repoRoot 'services/collector')
    try {
      py -m pytest -m database -q
      if ($LASTEXITCODE -ne 0) { throw 'Collector database tests failed.' }
      py -m eye_collector.cli run --source fixture --region 110000 | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'Fixture collection failed.' }
      py -m pytest -m etl_database -q
      if ($LASTEXITCODE -ne 0) { throw 'ETL database tests failed.' }
      py -m eye_collector.cli geocode --provider fixture --dry-run --limit 2 | Out-Null
      if ($LASTEXITCODE -ne 0) { throw 'Fixture geocoder dry-run failed.' }
      py -m pytest -m geocode_database -q
      if ($LASTEXITCODE -ne 0) { throw 'Geocoder database tests failed.' }
      if ($env:P5_BEIJING_OFFICIAL_FILE -and $env:P5_SHENZHEN_OFFICIAL_FILE) {
        $beijing = py -m eye_collector.cli inspect-file --source beijing-open-data-designated-medical-institutions --file $env:P5_BEIJING_OFFICIAL_FILE | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $beijing.row_count -ne 4876 -or -not $beijing.schema_match -or -not $beijing.ready_to_import) { throw 'Beijing official file inspect failed.' }
        $shenzhen = py -m eye_collector.cli inspect-file --source shenzhen-open-data-baoan-hospital-basic-information --file $env:P5_SHENZHEN_OFFICIAL_FILE | ConvertFrom-Json
        if ($LASTEXITCODE -ne 0 -or $shenzhen.row_count -ne 27 -or -not $shenzhen.schema_match -or -not $shenzhen.ready_to_import) { throw 'Shenzhen official file inspect failed.' }
      }
    }
    finally { Pop-Location }
    Push-Location (Join-Path $repoRoot 'apps/web')
    try {
      npm ci --ignore-scripts
      if ($LASTEXITCODE -ne 0) { throw 'Web dependencies could not be installed.' }
      npm run test:db
      if ($LASTEXITCODE -ne 0) { throw 'Web database tests failed.' }
    }
    finally { Pop-Location }

    New-Item -ItemType Directory -Path $backupRoot | Out-Null
    docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -f /workspace/db/tests/p14_restore_drill_seed.sql
    if ($LASTEXITCODE -ne 0) { throw 'Could not seed the synthetic restore facility.' }
    docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -v ON_ERROR_STOP=1 -c "INSERT INTO app_private.audit_events(entity,entity_id,action) VALUES('p14_restore_drill',gen_random_uuid(),'synthetic_backup_drill')"
    if ($LASTEXITCODE -ne 0) { throw 'Could not seed synthetic restore audit record.' }
    $countsSql = "SELECT (SELECT count(*) FROM public.published_facility_api),(SELECT count(*) FROM app_private.audit_events),(SELECT count(*) FROM app_private.source_records),(SELECT count(*) FROM app_private.facility_locations),(SELECT count(*) FROM public.schema_migrations)"
    $before = (docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d eye -A -t -F '|' -c $countsSql | Out-String).Trim() -replace '\s',''
    if ($before -notmatch '^[1-9][0-9]*\|[1-9][0-9]*\|[1-9][0-9]*\|[1-9][0-9]*\|15$') { throw "Synthetic restore drill baseline was incomplete: $before" }
    $containerId = (docker compose -p $projectName ps -q db | Out-String).Trim()
    $env:APP_ENV = 'ci'
    $env:P14_BACKUP_DIR = $backupRoot
    $env:P14_PG_TOOL_CONTAINER = $containerId
    node scripts/backup-db.mjs
    if ($LASTEXITCODE -ne 0) { throw 'P14 backup tool failed.' }
    $backupFile = (Get-ChildItem -LiteralPath $backupRoot -Filter 'eye-map-ci-*.dump' | Select-Object -First 1).FullName
    docker compose -p $projectName exec -T db dropdb -U eye --if-exists p14_restore_target
    if ($LASTEXITCODE -ne 0) { throw 'Could not clear the disposable restore target.' }
    docker compose -p $projectName exec -T db createdb -U eye --template=template0 p14_restore_target
    if ($LASTEXITCODE -ne 0) { throw 'Could not create an empty disposable restore target.' }
    $env:RESTORE_DATABASE_URL = $env:DATABASE_ADMIN_URL -replace '/eye$','/p14_restore_target'
    $env:RESTORE_CONFIRM = 'p14_restore_target'
    $env:RESTORE_BACKUP_FILE = $backupFile
    $restoreTimer = [Diagnostics.Stopwatch]::StartNew()
    node scripts/restore-db.mjs
    if ($LASTEXITCODE -ne 0) { throw 'P14 restore tool failed.' }
    $restoreTimer.Stop()
    $after = (docker compose -p $projectName exec -T db psql -h 127.0.0.1 -U eye -d p14_restore_target -A -t -F '|' -c $countsSql | Out-String).Trim() -replace '\s',''
    if ($LASTEXITCODE -ne 0 -or $before -ne $after) { throw "Restored counts differ: before=$before after=$after" }
    $publicCount = (docker compose -p $projectName exec -T db psql -q -h 127.0.0.1 -U eye -d p14_restore_target -A -t -c "SET ROLE eye_public_api_runtime; SELECT count(*) FROM public.query_published_facilities_bbox(116.3,39.8,116.5,40.0,NULL,NULL,NULL,10); RESET ROLE" | Out-String).Trim() -replace '\s',''
    if ($LASTEXITCODE -ne 0 -or [int]$publicCount -lt 1) { throw 'Restored public API query smoke failed.' }
    Write-Host "P14 disposable backup/restore drill PASS; restore duration ms: $($restoreTimer.ElapsedMilliseconds); restored counts: $after"
    docker compose -p $projectName exec -T db dropdb -U eye p14_restore_target
    if ($LASTEXITCODE -ne 0) { throw 'Could not remove the disposable restore target.' }
  }
  finally {
    docker compose -p $projectName down --volumes --remove-orphans
    if ($LASTEXITCODE -ne 0) { throw 'Disposable database cleanup failed.' }
    Pop-Location
    $tempRoot = [IO.Path]::GetFullPath([IO.Path]::GetTempPath())
    $resolvedBackupRoot = [IO.Path]::GetFullPath($backupRoot)
    if ($resolvedBackupRoot.StartsWith($tempRoot, [StringComparison]::OrdinalIgnoreCase) -and (Test-Path -LiteralPath $resolvedBackupRoot)) {
      Remove-Item -LiteralPath $resolvedBackupRoot -Recurse -Force
    }
  }
}
finally {
  foreach ($name in $environmentNames) {
    $oldValue = $previousEnvironment[$name]
    if ($null -eq $oldValue) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
    else { [Environment]::SetEnvironmentVariable($name, $oldValue, 'Process') }
  }
}
Write-Host 'P1–P14 disposable database checks passed.'
