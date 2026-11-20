<#
Builds the ReturnRight images (API, mock payment gateway, web app), starts them with
PostgreSQL and loads the synthetic demo data, then prints what was loaded and where to go.

  .\scripts\start.ps1           build, start, seed only if the database is empty
  .\scripts\start.ps1 -Reset    same, then wipe and reload fresh demo data
  .\scripts\start.ps1 -Stop     stop everything (data is kept)

If scripts are blocked: powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
Mac, Linux or Git Bash: scripts/start.sh [--reset | --stop]
#>
param(
    [switch]$Reset,
    [switch]$Stop
)

$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)

function Invoke-Checked([string]$Description, [scriptblock]$Command) {
    & $Command
    if ($LASTEXITCODE -ne 0) { throw "$Description failed (exit code $LASTEXITCODE)." }
}

function Get-EnvValue([string]$Name, [string]$Default) {
    $line = Get-Content .env | Where-Object { $_ -match "^$Name=" } | Select-Object -Last 1
    if ($line) {
        $value = $line.Substring($Name.Length + 1).Trim()
        if ($value) { return $value }
    }
    return $Default
}

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    throw 'Docker is not installed. Install Docker Desktop and try again.'
}
# Through cmd: Windows PowerShell 5.1 turns redirected stderr into errors when stopping on errors.
$null = cmd /c 'docker info >nul 2>&1'
if ($LASTEXITCODE -ne 0) { throw 'Docker is not running. Start Docker Desktop and try again.' }

if ($Stop) {
    Invoke-Checked 'Stopping' { docker compose stop }
    Write-Host 'Stopped. Run .\scripts\start.ps1 to start again; your data is kept.'
    return
}

if (-not (Test-Path .env)) {
    Copy-Item .env.example .env
    Write-Host 'Created .env from .env.example (dummy values; change ports there if one is taken).'
}

Write-Host '==> Building images: returnright-api, returnright-gateway, returnright-web'
Invoke-Checked 'Building the images' { docker compose build }

Write-Host '==> Starting the database, gateway, API and web app (the API seeds an empty database)'
Invoke-Checked 'Starting the stack' { docker compose up -d --wait --wait-timeout 300 }

if ($Reset) {
    Write-Host '==> Reloading fresh demo data'
    Invoke-Checked 'Seeding' { docker compose exec -T api python -m scripts.seed }
}

Write-Host '==> Rows in the database'
$counts = @"
SELECT 'products', count(*) FROM products
UNION ALL SELECT 'customers', count(*) FROM customers
UNION ALL SELECT 'orders', count(*) FROM orders
UNION ALL SELECT 'returns', count(*) FROM returns
UNION ALL SELECT 'refunds', count(*) FROM refunds
UNION ALL SELECT 'ledger entries', count(*) FROM ledger_entries
UNION ALL SELECT 'audit rows', count(*) FROM audit_log
UNION ALL SELECT 'staff users', count(*) FROM staff_users
"@
Invoke-Checked 'Counting rows' {
    docker compose exec -T db psql -U returnright -d returnright -tA -F ': ' -c $counts
}

$webPort = Get-EnvValue 'WEB_PORT' '8080'
$apiPort = Get-EnvValue 'API_PORT' '8000'
$gatewayPort = Get-EnvValue 'GATEWAY_PORT' '8001'
$dbPort = Get-EnvValue 'DB_PORT' '5434'
$password = Get-EnvValue 'DEMO_PASSWORD' 'change-me-demo'
Write-Host @"

ReturnRight is running.
  Web app    http://localhost:$webPort
  API docs   http://localhost:$apiPort/docs
  Gateway    http://localhost:$gatewayPort/health
  Database   localhost:$dbPort (user and database: returnright)

  Staff sign-in: warehouse1, finance1, manager1 / $password
  Customer: asha.verma@example.com with orders ORD-DEMO-01 to ORD-DEMO-10
            rohan.mehta@example.com with ORD-DEMO-11 (the 4th return flags the customer)

  Logs: docker compose logs -f api    Stop: .\scripts\start.ps1 -Stop
"@
