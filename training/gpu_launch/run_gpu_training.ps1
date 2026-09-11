# Xeren GPU Training Launcher (PowerShell)
# Run with: .\training\gpu_launch\run_gpu_training.ps1
# On college GPU machine (Linux): use run_gpu_training.sh instead

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "    Launching Xeren-Mini Training on NVIDIA GPU           " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

Set-Location $PSScriptRoot\..\..\

# 1. Create virtual environment if missing
if (-not (Test-Path ".venv-gpu")) {
    Write-Host "Creating .venv-gpu..." -ForegroundColor Yellow
    python -m venv .venv-gpu
}

# 2. Activate it
Write-Host "Activating .venv-gpu..." -ForegroundColor Yellow
& .venv-gpu\Scripts\Activate.ps1

# 3. Install GPU dependencies
Write-Host "Installing GPU dependencies..." -ForegroundColor Yellow
python -m pip install --upgrade pip
python -m pip install -r training/gpu_launch/requirements_gpu.txt

# 4. Check NVIDIA GPU status
Write-Host "Checking GPU..." -ForegroundColor Yellow
nvidia-smi

# 5. Run Training
Write-Host "Starting GPU training run..." -ForegroundColor Green
python training/gpu_launch/train_gpu.py

Write-Host "Training run finished." -ForegroundColor Green
