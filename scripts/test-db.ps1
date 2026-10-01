$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-p1-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$previousPassword = [Environment]::GetEnvironmentVariable('EYE_MAP_POSTGRES_PASSWORD', 'Process')
$previousPort = [Environment]::GetEnvironmentVariable('EYE_MAP_DB_PORT', 'Process')
$previousDatabaseUrl = [Environment]::GetEnvironmentVariable('DATABASE_URL', 'Process')
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
  $sqlFiles = @(
    '/workspace/db/migrations/001_core.sql',
    '/workspace/db/migrations/002_evidence_location.sql',
    '/workspace/db/migrations/003_published_view.sql',
    '/workspace/db/migrations/004_collector_permissions.sql',
    '/workspace/db/tests/001_core.sql',
    '/workspace/db/tests/002_evidence_location.sql',
    '/workspace/db/tests/003_published_view.sql',
    '/workspace/db/tests/004_collector_permissions.sql'
  )
  foreach ($sqlFile in $sqlFiles) {
    docker compose -p $projectName exec -T db psql -U eye -d eye -v ON_ERROR_STOP=1 -f $sqlFile
    if ($LASTEXITCODE -ne 0) { throw "SQL failed: $sqlFile" }
  }
  $collectorPassword = [Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32))
  docker compose -p $projectName exec -T db psql -U eye -d eye -v "collector_password=$collectorPassword" -f /workspace/scripts/provision-collector-login.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not provision the temporary collector login.' }
  docker compose -p $projectName exec -T db psql -U eye -d eye -f /workspace/scripts/seed-fixture-source.sql
  if ($LASTEXITCODE -ne 0) { throw 'Could not seed the synthetic source catalog.' }
  $env:DATABASE_URL = "postgresql://eye_collector_runtime:$collectorPassword@127.0.0.1:$testPort/eye"
  Push-Location (Join-Path $repoRoot 'services/collector')
  try {
    py -m pytest -m database -q
    if ($LASTEXITCODE -ne 0) { throw 'Collector database integration tests failed.' }
    $cliResult = py -m eye_collector.cli run --source fixture --region 110000 --dry-run --limit 1 | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $cliResult.status -ne 'succeeded' -or -not $cliResult.dry_run) {
      throw 'Collector CLI dry-run verification failed.'
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
  }
}
Write-Host 'P1/P2 database checks passed.'
