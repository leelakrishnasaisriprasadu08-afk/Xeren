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
$pythonExe = "python"
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} elseif (Test-Path "C:\Users\leela\AppData\Local\Programs\Python\Python312\python.exe") {
    $pythonExe = "C:\Users\leela\AppData\Local\Programs\Python\Python312\python.exe"
} elseif (Test-Path "d:\Xeren\.venv\Scripts\python.exe") {
    $pythonExe = "d:\Xeren\.venv\Scripts\python.exe"
}

Write-Host "🚀 Launching Xeren FastAPI on http://127.0.0.1:8000 using $pythonExe" -ForegroundColor Green
$env:PYTHONPATH = "backend;backend/src;$env:PYTHONPATH"
& $pythonExe -m uvicorn xeren.server.app:app --host 127.0.0.1 --port 8000 --app-dir backend/src --reload --log-level info

