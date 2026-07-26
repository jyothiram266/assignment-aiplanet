# Local ROCm GPU Setup Guide (Fedora Linux + AMD GPU)

This guide documents how to setup local fine-tuning on Fedora Linux with AMD GPUs (RDNA2 / gfx1030 / gfx1032 architecture, e.g., RX 6700XT / RX 6800 / RX 6900 series) using PyTorch with ROCm acceleration.

## 1. Environment Variable Override

On RDNA2 consumer GPUs (e.g. `gfx1032`), ROCm requires overriding the GFX ISA version target to `10.3.0` to activate HIP matrix kernels:

```bash
export HSA_OVERRIDE_GFX_VERSION=10.3.0
export ROCM_PATH=/opt/rocm
export HIP_VISIBLE_DEVICES=0
```

Add these to your `~/.bashrc` or `.env` file before executing PyTorch fine-tuning scripts.

## 2. Python Virtual Environment Setup

```bash
python3 -m venv venv
source venv/bin/activate

# Install PyTorch built with ROCm 6.x support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm6.1

# Install fine-tuning dependencies
pip install transformers peft datasets trl accelerate boto3
```

## 3. Verify ROCm Acceleration

Run the following python snippet to verify PyTorch detects your AMD GPU with ROCm HIP support:

```python
import torch
print("CUDA / ROCm Available:", torch.cuda.is_available())
print("Device Count:", torch.cuda.device_count())
print("Device Name:", torch.cuda.get_device_name(0))
```

Expected Output:
```text
CUDA / ROCm Available: True
Device Count: 1
Device Name: AMD Radeon RX 6700 XT (or equivalent)
```

## 4. Running Local Fine-Tuning & Quantization Pipeline

```bash
# Step 1: LoRA Fine-Tuning
python training/train_lora.py --base_model Qwen/Qwen2.5-0.5B-Instruct --output_dir ./checkpoints/v1.0.0

# Step 2: Quantize to GGUF Q4_K_M
python training/quantize.py --model_dir ./checkpoints/v1.0.0 --output_dir ./quantized --version v1.0.0 --quant_type Q4_K_M

# Step 3: Upload Artifact to DigitalOcean Spaces S3
export SPACES_ACCESS_KEY_ID="your-key"
export SPACES_SECRET_ACCESS_KEY="your-secret"
python training/upload_artifact.py --model_file ./quantized/model-v1.0.0-q4_k_m.gguf --version v1.0.0
```
