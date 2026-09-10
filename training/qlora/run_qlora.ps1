# Xeren QLoRA Launcher — RTX A1000 Windows
# Run from project root: .\training\qlora\run_qlora.ps1

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "   Xeren QLoRA Fine-Tuning  |  TinyLlama-1.1B on RTX A1000" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

Set-Location $PSScriptRoot\..\..

# 1. Create venv if missing
if (-not (Test-Path ".venv-qlora")) {
    Write-Host "[1/4] Creating .venv-qlora..." -ForegroundColor Yellow
    python -m venv .venv-qlora
} else {
    Write-Host "[1/4] .venv-qlora already exists." -ForegroundColor Green
}

# 2. Activate
Write-Host "[2/4] Activating .venv-qlora..." -ForegroundColor Yellow
& .venv-qlora\Scripts\Activate.ps1

# 3. Install dependencies
Write-Host "[3/4] Installing QLoRA dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip --quiet
python -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121 --quiet
python -m pip install -r training\qlora\requirements_qlora.txt --quiet
Write-Host "  Dependencies installed." -ForegroundColor Green

# 4. GPU check
Write-Host "[4/4] Checking GPU..." -ForegroundColor Yellow
nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}, GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else None}')"

# 5. Run training
Write-Host "`nStarting QLoRA fine-tuning..." -ForegroundColor Green
Write-Host "  Base model : TinyLlama/TinyLlama-1.1B-Chat-v1.0" -ForegroundColor White
Write-Host "  Trainable  : ~6.7M LoRA params (0.6% of 1.1B)" -ForegroundColor White
Write-Host "  Est. time  : 4-6 hours on RTX A1000 6GB" -ForegroundColor White
Write-Host ""

python training\qlora\train_qlora.py

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  Training complete! To serve Xeren:" -ForegroundColor Green
Write-Host "  python training\qlora\serve_qlora.py" -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan
