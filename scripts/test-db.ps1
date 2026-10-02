$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-db-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$environmentNames = @(
  'EYE_MAP_POSTGRES_PASSWORD', 'EYE_MAP_DB_PORT', 'DATABASE_URL', 'ETL_DATABASE_URL',
  'DATABASE_ADMIN_URL', 'GEOCODE_DATABASE_URL', 'PUBLIC_API_DATABASE_URL',
  'ADMIN_DATABASE_URL', 'SYNC_DATABASE_URL', 'P13_COLLECTOR_PASSWORD', 'P13_ETL_PASSWORD',
  'P13_GEOCODE_PASSWORD', 'P13_PUBLIC_API_PASSWORD', 'P13_ADMIN_DATABASE_PASSWORD', 'P13_SYNC_PASSWORD'
)
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
  $env:DATABASE_URL = "postgresql://eye_collector_runtime:$env:P13_COLLECTOR_PASSWORD@127.0.0.1:$testPort/eye"
  $env:ETL_DATABASE_URL = "postgresql://eye_etl_runtime:$env:P13_ETL_PASSWORD@127.0.0.1:$testPort/eye"
  $env:GEOCODE_DATABASE_URL = "postgresql://eye_geocode_runtime:$env:P13_GEOCODE_PASSWORD@127.0.0.1:$testPort/eye"
  $env:PUBLIC_API_DATABASE_URL = "postgresql://eye_public_api_runtime:$env:P13_PUBLIC_API_PASSWORD@127.0.0.1:$testPort/eye"
  $env:ADMIN_DATABASE_URL = "postgresql://eye_admin_review_runtime:$env:P13_ADMIN_DATABASE_PASSWORD@127.0.0.1:$testPort/eye"
  $env:SYNC_DATABASE_URL = "postgresql://eye_sync_worker_runtime:$env:P13_SYNC_PASSWORD@127.0.0.1:$testPort/eye"
  $env:DATABASE_ADMIN_URL = "postgresql://eye:$env:EYE_MAP_POSTGRES_PASSWORD@127.0.0.1:$testPort/eye"
  Push-Location $repoRoot
  try {
    docker compose -p $projectName up -d --wait
    if ($LASTEXITCODE -ne 0) { throw 'Disposable PostGIS did not become healthy.' }
    node scripts/db-test-bootstrap.mjs $projectName
    if ($LASTEXITCODE -ne 0) { throw 'P1–P13 database bootstrap/regression SQL failed.' }
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
  }
  finally {
    docker compose -p $projectName down --volumes --remove-orphans
    if ($LASTEXITCODE -ne 0) { throw 'Disposable database cleanup failed.' }
    Pop-Location
  }
}
finally {
  foreach ($name in $environmentNames) {
    $oldValue = $previousEnvironment[$name]
    if ($null -eq $oldValue) { Remove-Item "Env:$name" -ErrorAction SilentlyContinue }
    else { [Environment]::SetEnvironmentVariable($name, $oldValue, 'Process') }
  }
}
Write-Host 'P1–P13 disposable database checks passed.'
