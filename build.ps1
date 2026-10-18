[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# Change to project directory
$projectPath = Join-Path $env:USERPROFILE "Desktop" "软件杯" "a3-edu-agent-system"
Set-Location $projectPath

Write-Host "Building frontend..."
docker-compose build --no-cache frontend

Write-Host "Starting frontend..."
docker-compose up -d frontend

Write-Host "Done!"
