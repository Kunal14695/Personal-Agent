# Startup script for Personal Assistant Web App
Write-Host "=======================================================================" -ForegroundColor Cyan
Write-Host "Launching Personal Assistant Web Server..." -ForegroundColor Cyan
Write-Host "Using Model: $(Get-Content .env | Select-String "GEMINI_MODEL" | ForEach-Object { $_.Line.Split('=')[1] })" -ForegroundColor Yellow
Write-Host "=======================================================================" -ForegroundColor Cyan

# Start uvicorn server
python -m uvicorn server:app --host 0.0.0.0 --port 8000

# After server terminates, show message
Write-Host "`nWeb server stopped." -ForegroundColor Yellow
