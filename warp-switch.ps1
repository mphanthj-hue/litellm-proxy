param([switch]$Auto)

$log = "$env:USERPROFILE\.grok\warp-switch.log"
$time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

function Write-Log($msg) {
    $t = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "$t $msg" | Out-File $log -Append
}

function Wait-Connected($timeout = 10) {
    $elapsed = 0
    while ($elapsed -lt $timeout) {
        $s = warp-cli status 2>&1
        if ($s -match "Connected") { return $true }
        Start-Sleep 1
        $elapsed++
    }
    return $false
}

# Disconnect
warp-cli disconnect 2>&1 | Out-Null
Start-Sleep 2

# Connect
warp-cli connect 2>&1 | Out-Null

# Chờ Connected (tối đa 10s)
$ok = Wait-Connected

if ($Auto) {
    if ($ok) { Write-Log "[AUTO] WARP switched" }
    else     { Write-Log "[AUTO] WARP FAILED after timeout" }
    exit
}

# Manual mode — có popup
Write-Host "🔄 WARP IP switched!"
if (-not $ok) {
    Write-Host "⚠️  WARP not connected yet, waiting..."
    Start-Sleep 3
}
$s = warp-cli status 2>&1
Write-Host "   Status: $($s -replace 'Status update: ','')"
Write-Log "[MANUAL] WARP switched"
