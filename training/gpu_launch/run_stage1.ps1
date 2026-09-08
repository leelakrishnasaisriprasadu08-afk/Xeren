# =============================================================================
# Xeren-Mini Stage 1 Training Launcher
# Stage 1: ~70M parameters | Vocab: 16K | RTX A1000 (8GB)
# =============================================================================

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    XEREN-MINI STAGE 1 — Building Language Foundation" -ForegroundColor Cyan
Write-Host "    Model: ~70M params | Vocab: 16K | RTX A1000 8GB" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Check GPU
nvidia-smi

# Set HuggingFace token for dataset downloads
$env:HF_TOKEN = (Get-Content .env | Select-String "^HF_TOKEN=" | ForEach-Object { $_.Line.Split("=", 2)[1] })
$env:DATABASE_URL = (Get-Content .env | Select-String "^DATABASE_URL=" | ForEach-Object { $_.Line.Split("=", 2)[1] })

Write-Host ""
Write-Host "[1/3] Building Stage 1 dataset from HuggingFace sources..." -ForegroundColor Yellow
python training/gpu_launch/train_gpu.py --stage 1 --build-data

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Stage 1 training failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Stage 1 COMPLETE! Checkpoint saved to:" -ForegroundColor Green
Write-Host "  training/checkpoints/stage1/checkpoint_final.pt" -ForegroundColor Green
Write-Host ""
Write-Host "Next Step: Run Stage 2 training:" -ForegroundColor Yellow
Write-Host "  .\training\gpu_launch\run_stage2.ps1" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
