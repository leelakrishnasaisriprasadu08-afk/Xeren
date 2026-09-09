# =============================================================================
# Interactive Terminal Chat with Xeren LLM (Tier 3)
# =============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "         TALK TO YOUR SCRATCH-TRAINED XEREN LLM" -ForegroundColor Cyan
Write-Host "         Model: Tier 3 (214M Params) | RTX A1000 GPU" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$pythonExe = if (Test-Path ".venv\Scripts\python.exe") { ".venv\Scripts\python.exe" } else { "python" }

& $pythonExe training/scripts/chat.py
