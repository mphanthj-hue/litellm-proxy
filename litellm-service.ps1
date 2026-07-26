param([switch]$Stop)

$docker = "C:\Program Files\Docker\Docker\resources\bin\docker.exe"
$composeFile = "D:\CODE\litellm\docker-compose.yml"
$logTag = "LiteLLM-Service"

function Write-Log($msg) {
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$time] [$logTag] $msg"
}

if ($Stop) {
    Write-Log "Stopping LiteLLM containers..."
    & $docker compose -f $composeFile down
    Write-Log "Containers stopped."
    return
}

Write-Log "Service starting..."

# Chờ Docker Desktop ready (tối đa 5 phút)
$dockerReady = $false
for ($i = 0; $i -lt 30; $i++) {
    $test = & $docker ps 2>&1
    if ($LASTEXITCODE -eq 0) {
        $dockerReady = $true
        break
    }
    Write-Log "Waiting for Docker Desktop... attempt $($i+1)/30"
    Start-Sleep -Seconds 10
}

if (-not $dockerReady) {
    Write-Log "ERROR: Docker Desktop not available after 5 minutes. Exiting."
    exit 1
}
Write-Log "Docker Desktop ready."

# Start containers
Write-Log "Starting LiteLLM containers..."
& $docker compose -f $composeFile up -d
Write-Log "Containers started."

# Keep alive — NSSM cần process chạy liên tục
# Kiểm tra health mỗi 60s, nếu container chết thì restart
while ($true) {
    Start-Sleep -Seconds 60
    $health = & $docker compose -f $composeFile ps --status running 2>$null
    if ($LASTEXITCODE -ne 0 -or -not ($health -match "litellm")) {
        Write-Log "LiteLLM container not running, restarting..."
        & $docker compose -f $composeFile up -d
    } else {
        Write-Log "Health check OK"
    }
}
