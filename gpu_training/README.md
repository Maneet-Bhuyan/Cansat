# Cognitive CanSat - GPU Workstation Training Package

This directory contains the standalone CUDA deep learning training suite for fine-tuning heavy-duty vision models (MobileNetV3-Small and ResNet-18) on the 27,000-image EuroSAT dataset.

---

## 1. Prerequisites

- Operating System: Windows or Linux with an NVIDIA GPU (RTX 20/30/40 series, GTX 1660+, or A-series/Tesla).
- NVIDIA Display Drivers: 525+ or newer.
- Python 3.10, 3.11, or 3.12.
- Git installed and authenticated with your repository.

---

## 2. Quick Setup on CUDA Laptop

1. Pull latest code from GitHub:
   ```bash
   git pull origin main
   ```

2. Activate your virtual environment:
   ```powershell
   # Windows PowerShell
   .\.venv\Scripts\Activate.ps1

   # Linux/macOS
   source .venv/bin/activate
   ```

3. Ensure PyTorch with CUDA support is installed:
   ```bash
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
   pip install -r requirements.txt
   ```

4. Verify CUDA detection:
   ```bash
   python -c "import torch; print('CUDA available:', torch.cuda.is_available(), '| Device:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None')"
   ```

---

## 3. Running the Training Pipeline

Execute the automated training script:
```bash
python gpu_training/train_heavy_duty_models.py
```

### What Happens Automatically:
1. Detects your NVIDIA GPU and enables Tensor Cores with Automatic Mixed Precision (`torch.cuda.amp`).
2. Loads and parses 27,000 EuroSAT images into the 4 Safe Landing Area Index (SLAI) classes:
   - `SAFE_LZ` (Farmland, pasture, crops)
   - `OBSTACLE_CANOPY` (Forests)
   - `CRITICAL_HAZARD` (Highways, buildings, industrial)
   - `WATER_HAZARD` (Rivers, lakes)
3. Trains MobileNetV3-Small (Tier 2 Companion model) for 15 epochs with Cosine Annealing learning rate.
4. Trains ResNet-18 (Tier 3 Ground Station model) for 15 epochs.
5. Saves the best model checkpoints to `ml/saved_models/`:
   - `mobilenet_v3_small_best.pth`
   - `resnet18_best.pth`
6. Exports optimized ONNX graphs for C++/Python runtime:
   - `mobilenet_v3_small.onnx`
   - `resnet18.onnx`
7. Automatically executes `ml/benchmark_vision_models.py` to evaluate latency, memory, OOD guard performance, and descent flight video test frames, outputting `ml/vision_model_comparison.json`.

---

## 4. Verification & Testing

Run the test suites to ensure everything is operating cleanly:
```bash
node tests/selftest.js
python -m unittest tests/test_backend_core.py tests/test_database.py tests/test_telemetry_analyzer.py
```

---

## 5. Pushing Results to GitHub

Once training completes, stage the generated model checkpoints, metrics, and logs, then push to GitHub:
```bash
git add ml/saved_models/mobilenet_v3_small_best.pth
git add ml/saved_models/resnet18_best.pth
git add ml/saved_models/mobilenet_v3_small.onnx
git add ml/saved_models/resnet18.onnx
git add ml/gpu_training_summary.json
git add ml/vision_model_comparison.json
git commit -m "Train and export MobileNetV3-Small and ResNet-18 on CUDA workstation"
git push origin main
```

---

## 6. Hand-off Back to Primary Laptop

After pushing from the GPU laptop, return to the primary laptop and run:
```bash
git pull origin main
```
The FastAPI backend (`backend/app.py`), the Mission Control dashboard (`frontend/dashboard.html`), and the TinyML visualizer (`frontend/tinyml.html`) will automatically detect and load the newly fine-tuned heavy-duty models!
