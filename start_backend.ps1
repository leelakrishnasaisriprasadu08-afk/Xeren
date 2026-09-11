# Xeren Backend Server Startup Script
# Run this from d:\Xeren to start the Xeren AI backend on port 8000
Write-Host "⚡ Starting Xeren Backend Server..." -ForegroundColor Cyan
$existing = netstat -ano | findstr ":8000 " | ForEach-Object { ($_ -split '\s+')[-1] } | Sort-Object -Unique
foreach ($pid in $existing) {
    if ($pid -and $pid -match '^\d+$') {
        try { Stop-Process -Id $pid -Force -ErrorAction SilentlyContinue } catch {}
    }
}
Start-Sleep -Seconds 1
Write-Host "🚀 Launching Xeren FastAPI on http://127.0.0.1:8000" -ForegroundColor Green
d:\Xeren\.venv\Scripts\python.exe -m uvicorn xeren.server.app:app --host 127.0.0.1 --port 8000 --app-dir src --reload --log-level info
