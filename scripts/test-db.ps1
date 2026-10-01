$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
$projectName = 'eye-p1-check-' + [guid]::NewGuid().ToString('N').Substring(0, 8)
$previousPassword = [Environment]::GetEnvironmentVariable('EYE_MAP_POSTGRES_PASSWORD', 'Process')
$previousPort = [Environment]::GetEnvironmentVariable('EYE_MAP_DB_PORT', 'Process')
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
  }
}
Write-Host 'P1 database checks passed.'
