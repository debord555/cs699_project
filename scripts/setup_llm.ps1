# Sets up the local LLM (Lemonade Server + Qwen3-8B) used by the project.
# Usage:  powershell -ExecutionPolicy Bypass -File scripts\setup_llm.ps1
# Requires Lemonade to be installed first: https://lemonade-server.ai

param(
    [string]$Model = "Qwen3-8B-GGUF-Q4_K_M",
    [int]$Port = 13305,
    [int]$StartTimeoutSeconds = 60
)

$ErrorActionPreference = "Stop"
$BaseUrl = "http://127.0.0.1:$Port/api/v1"

function Test-Server {
    try {
        Invoke-RestMethod -Uri "$BaseUrl/health" -TimeoutSec 3 | Out-Null
        return $true
    } catch {
        return $false
    }
}

# 1. Find the lemonade CLI
$cli = Get-Command lemonade -ErrorAction SilentlyContinue
if (-not $cli) {
    $default = Join-Path $env:LOCALAPPDATA "lemonade_server\bin\lemonade.exe"
    if (Test-Path $default) {
        $cli = Get-Item $default
    } else {
        Write-Error "Lemonade not found. Install it from https://lemonade-server.ai and re-run."
    }
}
$lemonade = $cli.Source
if (-not $lemonade) { $lemonade = $cli.FullName }
$binDir = Split-Path $lemonade
Write-Host "Using $lemonade ($(& $lemonade --version))"

# 2. Start the server if it is not already running
if (Test-Server) {
    Write-Host "Server already running on port $Port"
} else {
    Write-Host "Starting Lemonade Server..."
    Start-Process -FilePath (Join-Path $binDir "LemonadeServer.exe") -WindowStyle Hidden
    $deadline = (Get-Date).AddSeconds($StartTimeoutSeconds)
    while (-not (Test-Server)) {
        if ((Get-Date) -gt $deadline) {
            Write-Error "Server did not come up on port $Port within $StartTimeoutSeconds s"
        }
        Start-Sleep -Seconds 2
    }
    Write-Host "Server is up"
}

# 3. Download the model if needed
$models = (Invoke-RestMethod -Uri "$BaseUrl/models").data
$entry = $models | Where-Object { $_.id -eq $Model }
if ($entry -and $entry.downloaded) {
    Write-Host "Model $Model already downloaded"
} else {
    Write-Host "Pulling $Model (about 5 GB, this can take a while)..."
    & $lemonade --port $Port pull $Model
    if ($LASTEXITCODE -ne 0) { Write-Error "Failed to pull $Model" }
}

# 4. Load it
Write-Host "Loading $Model..."
& $lemonade --port $Port load $Model
if ($LASTEXITCODE -ne 0) { Write-Error "Failed to load $Model" }

# 5. Smoke test through the OpenAI-compatible API
$body = @{
    model      = $Model
    messages   = @(@{ role = "user"; content = "Reply with just the word OK. /no_think" })
    max_tokens = 20
} | ConvertTo-Json -Depth 5
$resp = Invoke-RestMethod -Uri "$BaseUrl/chat/completions" -Method Post -ContentType "application/json" -Body $body
$reply = ($resp.choices[0].message.content -replace "(?s)<think>.*?</think>", "").Trim()
Write-Host "Model replied: $reply"

Write-Host ""
Write-Host "Done. Add these to your .env:"
Write-Host "  LLM_BASE_URL=$BaseUrl"
Write-Host "  LLM_MODEL=$Model"
