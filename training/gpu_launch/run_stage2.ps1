# =============================================================================
# Xeren-Mini Stage 2 Training Launcher
# Stage 2: ~120M parameters | Vocab: 32K | RTX A1000 (8GB)
# Requires: Stage 1 checkpoint at training/checkpoints/stage1/checkpoint_final.pt
# =============================================================================

Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "    XEREN-MINI STAGE 2 — Domain Specialization" -ForegroundColor Magenta
Write-Host "    Model: ~120M params | Vocab: 32K | RTX A1000 8GB" -ForegroundColor Magenta
Write-Host "    Heads: Plugin + Confidence + Threat Detection" -ForegroundColor Magenta
Write-Host "==========================================================" -ForegroundColor Magenta

# Verify Stage 1 checkpoint exists
if (-not (Test-Path "training/checkpoints/stage1/checkpoint_final.pt")) {
    Write-Host "ERROR: Stage 1 checkpoint not found!" -ForegroundColor Red
    Write-Host "Please run Stage 1 first: .\training\gpu_launch\run_stage1.ps1" -ForegroundColor Yellow
    exit 1
}
Write-Host "[OK] Stage 1 checkpoint found. Initializing Stage 2 with weight transfer..." -ForegroundColor Green

# Check GPU
nvidia-smi

# Load environment variables
$env:HF_TOKEN = (Get-Content .env | Select-String "^HF_TOKEN=" | ForEach-Object { $_.Line.Split("=", 2)[1] })
$env:DATABASE_URL = (Get-Content .env | Select-String "^DATABASE_URL=" | ForEach-Object { $_.Line.Split("=", 2)[1] })
$env:QDRANT_URL = (Get-Content .env | Select-String "^QDRANT_URL=" | ForEach-Object { $_.Line.Split("=", 2)[1] })
$env:QDRANT_API_KEY = (Get-Content .env | Select-String "^QDRANT_API_KEY=" | ForEach-Object { $_.Line.Split("=", 2)[1] })

Write-Host ""
Write-Host "[1/3] Building Stage 2 domain-specific dataset..." -ForegroundColor Yellow
Write-Host "      Sources: WildGuard, OpenR1-Math, Hermes, The Stack..." -ForegroundColor Yellow

python training/gpu_launch/train_gpu.py --stage 2 --build-data

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: Stage 2 training failed!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host "Stage 2 COMPLETE! Xeren-Mini-150 is ready!" -ForegroundColor Green
Write-Host ""
Write-Host "Checkpoint: training/checkpoints/stage2/checkpoint_final.pt" -ForegroundColor Green
Write-Host "Provider:   src/xeren/models/providers/xeren_native.py" -ForegroundColor Green
Write-Host ""
Write-Host "To start continuous training loop:" -ForegroundColor Yellow
Write-Host "  python training/src/engine/continuous_trainer.py" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Green
