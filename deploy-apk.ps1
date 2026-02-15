# deploy-apk.ps1 — Build and deploy APK to GCP server for in-app updates
# Usage: .\deploy-apk.ps1 -Version "0.4"

param(
    [Parameter(Mandatory=$true)]
    [string]$Version
)

$ErrorActionPreference = "Stop"
$SSH_KEY = "C:\Users\tyranno\.ssh\voicechat-key"
$SERVER = "tyranno@34.64.164.13"
$APK_PATH = "E:\Project\My\voice-chat\android\app\build\outputs\apk\debug\app-debug.apk"
$PROJECT = "E:\Project\My\voice-chat"

Write-Host "🦖 VoiceChat APK Deploy v$Version" -ForegroundColor Cyan

# 1. Build
Write-Host "`n[1/5] Building web app..." -ForegroundColor Yellow
Set-Location $PROJECT
npm run build 2>&1 | Out-Null
npx cap sync android 2>&1 | Out-Null
Write-Host "  ✓ Web build + sync complete"

# 2. Build APK
Write-Host "[2/5] Building APK..." -ForegroundColor Yellow
Set-Location "$PROJECT\android"
cmd /c "gradlew.bat assembleDebug" 2>&1 | Out-Null
if (-not (Test-Path $APK_PATH)) {
    Write-Host "  ✗ APK build failed!" -ForegroundColor Red
    exit 1
}
$apkSize = (Get-Item $APK_PATH).Length
Write-Host "  ✓ APK built ($([math]::Round($apkSize/1MB, 1)) MB)"

# 3. Create version.json
Write-Host "[3/5] Creating version info..." -ForegroundColor Yellow
$versionJson = @{
    version = $Version
    versionCode = [int]($Version -replace '\.','')
    size = $apkSize
    updatedAt = (Get-Date -Format "yyyy-MM-ddTHH:mm:ssZ")
} | ConvertTo-Json
$versionFile = "$env:TEMP\version.json"
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($versionFile, $versionJson, $utf8NoBom)
Write-Host "  ✓ version.json created (v$Version)"

# 4. Upload to server
Write-Host "[4/5] Uploading to server..." -ForegroundColor Yellow
ssh -i $SSH_KEY $SERVER "sudo mkdir -p /opt/voicechat/data/apk"
scp -i $SSH_KEY $APK_PATH "${SERVER}:/tmp/app-debug.apk"
scp -i $SSH_KEY $versionFile "${SERVER}:/tmp/version.json"
ssh -i $SSH_KEY $SERVER "sudo cp /tmp/app-debug.apk /opt/voicechat/data/apk/app-debug.apk && sudo cp /tmp/version.json /opt/voicechat/data/apk/version.json && sudo chmod 644 /opt/voicechat/data/apk/*"
Write-Host "  ✓ Uploaded to server"

# 5. Verify
Write-Host "[5/5] Verifying..." -ForegroundColor Yellow
$check = curl.exe -sk https://34.64.164.13/api/apk/latest 2>&1
Write-Host "  Server response: $check"

Write-Host "`n✅ Deploy complete! App can now update to v$Version" -ForegroundColor Green
