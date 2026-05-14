# deploy-apk.ps1 — Build and deploy APK to NanoPC-T4 server for in-app updates
# Usage: .\deploy-apk.ps1 -Version "0.10.27" [-Host "nanopi"]
#
# Default host: 'nanopi' (SSH alias via Cloudflare Tunnel + key auth)
# Alternatives: 'nanopi-lan' (192.168.123.200, home LAN only)

param(
    [Parameter(Mandatory=$true)]
    [string]$Version,
    [string]$NanoPiHost = "nanopi"
)

$ErrorActionPreference = "Stop"
$PROJECT = "C:\Project\88.MyProject\voice-chat"
$APK_PATH = "$PROJECT\android\app\build\outputs\apk\debug\app-debug.apk"

Write-Host "🦖 Rex APK Deploy v$Version → $NanoPiHost" -ForegroundColor Cyan

# 1. Web build
Write-Host "`n[1/5] Building web app..." -ForegroundColor Yellow
Set-Location $PROJECT
npm run build 2>&1 | Out-Null
npx cap sync android 2>&1 | Out-Null
Write-Host "  ✓ Web build + sync complete"

# 2. Build APK
Write-Host "[2/5] Building APK..." -ForegroundColor Yellow
Set-Location "$PROJECT\android"
$env:JAVA_HOME = "C:\Program Files\Android\openjdk\jdk-21.0.8"
$env:ANDROID_HOME = "C:\Program Files (x86)\Android\android-sdk"
$env:ANDROID_SDK_ROOT = $env:ANDROID_HOME
$env:PATH = "$env:JAVA_HOME\bin;$env:PATH"
cmd /c "gradlew.bat assembleDebug" 2>&1 | Out-Null
if (-not (Test-Path $APK_PATH)) {
    Write-Host "  ✗ APK build failed!" -ForegroundColor Red
    exit 1
}
$apkSize = (Get-Item $APK_PATH).Length
Write-Host "  ✓ APK built ($([math]::Round($apkSize/1MB, 1)) MB)"

# 3. Create version metadata
Write-Host "[3/5] Creating metadata..." -ForegroundColor Yellow
$timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
$versionJson = @{
    version = $Version
    versionCode = [int]($Version -replace '\.','')
    size = $apkSize
    updatedAt = $timestamp
} | ConvertTo-Json -Compress

$metaJson = @{
    version = $Version
    versionCode = [int]($Version -replace '\.','')
    size = $apkSize
    downloadUrl = "/api/apk/download"
} | ConvertTo-Json -Compress

$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText("$env:TEMP\version.json", $versionJson, $utf8NoBom)
[System.IO.File]::WriteAllText("$env:TEMP\meta.json", $metaJson, $utf8NoBom)
Write-Host "  ✓ version.json + meta.json (v$Version, $apkSize bytes)"

# 4. Upload to NanoPi
Write-Host "[4/5] Uploading to $NanoPiHost..." -ForegroundColor Yellow
scp $APK_PATH "${NanoPiHost}:/tmp/app-debug.apk"
scp "$env:TEMP\version.json" "$env:TEMP\meta.json" "${NanoPiHost}:/tmp/"
ssh $NanoPiHost "sudo cp /tmp/app-debug.apk /opt/voicechat/data/apk/app-debug.apk && sudo cp /tmp/version.json /opt/voicechat/data/apk/version.json && sudo cp /tmp/meta.json /opt/voicechat/data/apk/meta.json && sudo chmod 644 /opt/voicechat/data/apk/*"
Write-Host "  ✓ Uploaded to /opt/voicechat/data/apk/"

# 5. Verify
Write-Host "[5/5] Verifying..." -ForegroundColor Yellow
$check = curl.exe -sk https://voicechat.tyranno.xyz/api/apk/latest 2>&1
Write-Host "  Server response: $check"

Write-Host "`n✅ Deploy complete! App can now update to v$Version" -ForegroundColor Green
