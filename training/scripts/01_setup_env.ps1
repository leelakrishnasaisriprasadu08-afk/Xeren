# Environment verification and dependency check script for Xeren LLM training
Write-Host "=== Setting up Xeren LLM Training Environment ===" -ForegroundColor Cyan

# Verify uv is installed
if (Get-Command uv -ErrorAction SilentlyContinue) {
    Write-Host "✓ Found uv package manager" -ForegroundColor Green
    uv pip install -r training/requirements.txt
} else {
    Write-Host "uv not found, using python -m pip" -ForegroundColor Yellow
    python -m pip install -r training/requirements.txt
}

Write-Host "✓ Environment setup complete." -ForegroundColor Green
