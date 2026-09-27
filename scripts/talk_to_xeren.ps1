# =============================================================================
# Interactive Terminal Chat with Xeren Autonomous Agent
# Realtime Streaming | Task Planning | Rich Markdown | API Connected
# =============================================================================

$pythonExe = "python"
if (Get-Command "python" -ErrorAction SilentlyContinue) {
    $pythonExe = "python"
} elseif (Test-Path "C:\Users\leela\AppData\Local\Programs\Python\Python312\python.exe") {
    $pythonExe = "C:\Users\leela\AppData\Local\Programs\Python\Python312\python.exe"
} elseif (Test-Path "d:\Xeren\.venv\Scripts\python.exe") {
    $pythonExe = "d:\Xeren\.venv\Scripts\python.exe"
}

& $pythonExe scripts/chat_agent.py
