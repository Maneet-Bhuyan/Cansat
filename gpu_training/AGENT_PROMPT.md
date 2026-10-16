# ANTIGRAVITY AUTONOMOUS TASK PROMPT (FOR CUDA LAPTOP)
======================================================

Paste the prompt below into Antigravity on your CUDA-equipped laptop to autonomously execute the model training, benchmarking, verification, and GitHub synchronization.

---

### COPY FROM HERE:

```text
You are working on the Cognitive CanSat Safe Landing AI (SLAI) project on this CUDA-equipped workstation.

Your goal is to fine-tune and export the two heavy-duty vision models (Tier 2: MobileNetV3-Small and Tier 3: ResNet-18) on the EuroSAT dataset using NVIDIA CUDA acceleration, benchmark them, verify the system, and push the trained artifacts to GitHub.

Strict project constraints:
- Maintain documentation integrity and preserve code style.
- Strictly ZERO EMOJIS across all code, docstrings, commit messages, and text responses.
- Clickable markdown links for all paths and symbols using the file:// scheme.

Follow these execution steps sequentially:

Step 1: Context & Hardware Audit
- Read gpu_training/context.txt and gpu_training/README.md.
- Check PyTorch and CUDA availability:
  python -c "import torch; print('CUDA Available:', torch.cuda.is_available(), '| GPU:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE', '| VRAM (GB):', round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2) if torch.cuda.is_available() else 0)"
- If CUDA is not detected, check if PyTorch is installed with CUDA support (pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121).

Step 2: Execute Heavy-Duty Training Pipeline
- Run the turnkey training script:
  python gpu_training/train_heavy_duty_models.py
- This will train MobileNetV3-Small (15 epochs) and ResNet-18 (15 epochs) with Automatic Mixed Precision (AMP), saving:
  - ml/saved_models/mobilenet_v3_small_best.pth
  - ml/saved_models/resnet18_best.pth
  - ml/saved_models/mobilenet_v3_small.onnx
  - ml/saved_models/resnet18.onnx
  - ml/gpu_training_summary.json

Step 3: Vision Benchmark & Video Evaluation
- Run the benchmark suite to refresh latency, memory, and flight video metrics:
  python ml/benchmark_vision_models.py
- Verify that ml/vision_model_comparison.json is updated.

Step 4: Quality & Test Suite Verification
- Run the JavaScript and Python test suites:
  node tests/selftest.js
  python -m unittest tests/test_backend_core.py tests/test_database.py tests/test_telemetry_analyzer.py
- Ensure all tests pass with zero failures.

Step 5: Git Commit & Push
- Stage the newly generated artifacts:
  git add ml/saved_models/mobilenet_v3_small_best.pth ml/saved_models/resnet18_best.pth ml/saved_models/mobilenet_v3_small.onnx ml/saved_models/resnet18.onnx ml/gpu_training_summary.json ml/vision_model_comparison.json
- Commit with a clear message (strictly no emojis):
  git commit -m "Train and export MobileNetV3-Small and ResNet-18 on CUDA workstation"
- Push changes to origin main:
  git push origin main

Step 6: Completion Report
Provide a clean summary containing:
1. Hardware detected: GPU model, CUDA version, VRAM.
2. Final validation accuracy and training time for MobileNetV3-Small and ResNet-18.
3. CPU and GPU latency comparison.
4. Out-of-Distribution (OOD) guard verification status.
5. Confirmation of git push so the primary laptop can pull the changes.
```
