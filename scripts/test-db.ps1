$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-p4-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$previousPassword = [Environment]::GetEnvironmentVariable('EYE_MAP_POSTGRES_PASSWORD', 'Process')
$previousPort = [Environment]::GetEnvironmentVariable('EYE_MAP_DB_PORT', 'Process')
$previousDatabaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL', 'Process')
$previousEtlDatabaseUrl = [Environment]::GetEnvironmentVariable('ETL_DATABASE_URL', 'Process')
$previousDatabaseAdminUrl = [Environment]::GetEnvironmentVariable('DATABASE_ADMIN_URL', 'Process')
$previousGeocodeDatabaseUrl = [Environment]::GetEnvironmentVariable('GEOCODE_DATABASE_URL', 'Process')
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
  $testFiles = @(
    '/workspace/db/tests/001_core.sql',
    '/workspace/db/tests/002_evidence_location.sql',
    '/workspace/db/tests/003_published_view.sql',
    '/workspace/db/tests/004_collector_permissions.sql',
    '/workspace/db/tests/005_etl_candidates.sql',
    '/workspace/db/tests/006_geocoding.sql'
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
  $env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:$testPort/eye"
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "etl_password=$etlPassword" -f /workspace/scripts/provision-etl-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary ETL login.' }
  $env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$etlPassword@127.0.0.1:$testPort/eye"
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "geocode_password=$geocodePassword" -f /workspace/scripts/provision-geocode-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary geocode login.' }
  $env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$geocodePassword@127.0.0.1:$testPort/eye"
  $env:DATABASE_ADMIN_URL = "postgresql://eye:$env:EYE_MAP_POSTGRES_PASSWORD@127.0.0.1:$testPort/eye"
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
  }
}
Write-Host 'P1/P2/P3/P4 database checks passed.'
