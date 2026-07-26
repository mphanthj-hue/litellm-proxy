param([switch]$Stop)

$log = "$env:USERPROFILE\.grok\warp-switch.log"
$intervalMin = 15  # rotate mỗi 15 phút

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

function Rotate-Warp {
    Write-Log "[SERVICE] Rotating WARP IP..."
    warp-cli disconnect 2>&1 | Out-Null
    Start-Sleep 2
    warp-cli connect 2>&1 | Out-Null
    $ok = Wait-Connected
    if ($ok) {
        Write-Log "[SERVICE] WARP rotated OK"
    } else {
        Write-Log "[SERVICE] WARP rotate FAILED"
    }
}

# Stop mode — NSSM gửi Ctrl+C, script tự thoát
if ($Stop) {
    Write-Log "[SERVICE] Stop signal received, exiting"
    return
}

Write-Log "[SERVICE] Started (interval: ${intervalMin}min)"

# Vòng lặp chính
while ($true) {
    Rotate-Warp
    for ($i = 0; $i -lt $intervalMin; $i++) {
        Start-Sleep -Seconds 60
    }
}
