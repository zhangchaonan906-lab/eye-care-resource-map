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
}
finally {
  try {
    docker compose -p $projectName down --volumes
    if ($LASTEXITCODE -ne 0) { throw 'Docker database cleanup failed.' }
  }
  finally {
    Pop-Location
  }
}
Write-Host 'P1 database checks passed.'
