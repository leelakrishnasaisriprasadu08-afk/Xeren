#!/usr/bin/env bash
set -e

echo "=========================================================="
echo "    Launching Xeren-Mini Training on College NVIDIA GPU   "
echo "=========================================================="

# 1. Create and activate virtual environment
if [ ! -d ".venv-gpu" ]; then
    echo "Creating .venv-gpu..."
    python3 -m venv .venv-gpu
fi

source .venv-gpu/bin/activate

# 2. Install dependencies
echo "Installing GPU dependencies..."
pip install --upgrade pip
pip install -r training/gpu_launch/requirements_gpu.txt

# 3. Check NVIDIA GPU status
nvidia-smi

# 4. Run Training
echo "Starting training run..."
python training/gpu_launch/train_gpu.py

echo "Training run finished."
