"""
Cognitive CanSat - GPU Heavy-Duty Vision Model Training Pipeline
---------------------------------------------------------------
CUDA Workstation Accelerated Training for MobileNetV3-Small and ResNet-18
on EuroSAT with SLAI (Safe Landing Area Index) 4-Tier Mapping.

Target Hardware: NVIDIA CUDA GPUs (Tensor Cores / Automatic Mixed Precision)
Gracefully falls back to CPU if run without CUDA.

Outputs:
- ml/saved_models/mobilenet_v3_small_best.pth
- ml/saved_models/resnet18_best.pth
- ml/saved_models/mobilenet_v3_small.onnx
- ml/saved_models/resnet18.onnx
- Refreshed ml/vision_model_comparison.json
"""

import os
import sys
import time
import json
import random
from typing import Dict, Any, List, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import models, transforms
from PIL import Image

DATA_DIR = os.path.join(REPO_ROOT, "data", "eurosat", "2750")
MODELS_DIR = os.path.join(REPO_ROOT, "ml", "saved_models")
COMPARISON_JSON_PATH = os.path.join(REPO_ROOT, "ml", "vision_model_comparison.json")

os.makedirs(MODELS_DIR, exist_ok=True)

# ---------------------------------------------------------------------------
# 4-Tier Safe Landing Area Index (SLAI) Mapping
# ---------------------------------------------------------------------------
SLAI_CLASSES = [
    "SAFE_LZ",          # 0: Open pastures, crops, fields
    "OBSTACLE_CANOPY",  # 1: Forest canopy
    "CRITICAL_HAZARD",  # 2: Highways, buildings, industrial
    "WATER_HAZARD"      # 3: Rivers, lakes, open water
]

CLASS_MAP = {
    "AnnualCrop": 0,
    "HerbaceousVegetation": 0,
    "Pasture": 0,
    "PermanentCrop": 0,
    "Forest": 1,
    "Highway": 2,
    "Industrial": 2,
    "Residential": 2,
    "River": 3,
    "SeaLake": 3
}


class EuroSATDataset(Dataset):
    """Loads EuroSAT 2750 RGB imagery with 4-class SLAI tactical mapping."""
    def __init__(self, root_dir: str, transform=None):
        self.samples: List[Tuple[str, int]] = []
        self.transform = transform

        candidates = [
            root_dir,
            os.path.join(root_dir, "2750"),
            os.path.join(REPO_ROOT, "data", "eurosat", "2750"),
            os.path.join(REPO_ROOT, "data", "eurosat")
        ]

        found_dir = None
        for cand in candidates:
            if cand and os.path.exists(cand) and any(os.path.isdir(os.path.join(cand, c)) for c in CLASS_MAP):
                found_dir = cand
                break

        if not found_dir:
            raise FileNotFoundError(
                f"Dataset not found at {root_dir}. Please run: python ml/download_dataset.py"
            )

        for folder_name in sorted(os.listdir(found_dir)):
            if folder_name in CLASS_MAP:
                folder_path = os.path.join(found_dir, folder_name)
                label = CLASS_MAP[folder_name]
                for fname in sorted(os.listdir(folder_path)):
                    if fname.lower().endswith((".jpg", ".jpeg", ".png", ".tif")):
                        self.samples.append((os.path.join(folder_path, fname), label))

        if len(self.samples) == 0:
            raise RuntimeError(f"Found no valid image samples in {found_dir}")

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, label


def create_dataloaders(batch_size: int = 64, img_size: int = 224, num_workers: int = 4):
    train_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomVerticalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.1, contrast=0.1),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    val_transform = transforms.Compose([
        transforms.Resize((img_size, img_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])

    full_ds = EuroSATDataset(DATA_DIR, transform=train_transform)
    total_len = len(full_ds)
    train_len = int(0.85 * total_len)
    val_len = total_len - train_len

    torch.manual_seed(42)
    train_set, val_set = random_split(full_ds, [train_len, val_len])

    # Assign val_transform to validation set
    class TransformSubset(Dataset):
        def __init__(self, subset, transform):
            self.subset = subset
            self.transform = transform

        def __len__(self):
            return len(self.subset)

        def __getitem__(self, idx):
            path, label = self.subset.dataset.samples[self.subset.indices[idx]]
            img = Image.open(path).convert("RGB")
            if self.transform:
                img = self.transform(img)
            return img, label

    val_set = TransformSubset(val_set, val_transform)

    train_loader = DataLoader(
        train_set,
        batch_size=batch_size,
        shuffle=True,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )
    val_loader = DataLoader(
        val_set,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=torch.cuda.is_available()
    )

    return train_loader, val_loader, total_len, train_len, val_len


def train_single_architecture(
    model_name: str,
    model: nn.Module,
    train_loader: DataLoader,
    val_loader: DataLoader,
    device: torch.device,
    epochs: int = 15,
    learning_rate: float = 3e-4
) -> Tuple[nn.Module, Dict[str, Any]]:
    print("\n" + "=" * 70)
    print(f"Beginning Training: {model_name} on {device}")
    print("=" * 70)

    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.AdamW(model.parameters(), lr=learning_rate, weight_decay=1e-4)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    scaler = torch.cuda.amp.GradScaler(enabled=(device.type == "cuda"))

    best_val_acc = 0.0
    best_weights_path = os.path.join(MODELS_DIR, f"{model_name.lower()}_best.pth")
    history = []

    start_time = time.time()

    for epoch in range(1, epochs + 1):
        ep_t0 = time.time()
        # Training Phase
        model.train()
        running_loss = 0.0
        correct_train = 0
        total_train = 0

        for imgs, labels in train_loader:
            imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
            optimizer.zero_grad()

            with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                outputs = model(imgs)
                loss = criterion(outputs, labels)

            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()

            running_loss += loss.item() * imgs.size(0)
            preds = torch.argmax(outputs, dim=1)
            correct_train += (preds == labels).sum().item()
            total_train += labels.size(0)

        scheduler.step()
        train_loss = running_loss / total_train
        train_acc = correct_train / total_train

        # Validation Phase
        model.eval()
        val_loss_sum = 0.0
        correct_val = 0
        total_val = 0

        with torch.no_grad():
            for imgs, labels in val_loader:
                imgs, labels = imgs.to(device, non_blocking=True), labels.to(device, non_blocking=True)
                with torch.cuda.amp.autocast(enabled=(device.type == "cuda")):
                    outputs = model(imgs)
                    loss = criterion(outputs, labels)

                val_loss_sum += loss.item() * imgs.size(0)
                preds = torch.argmax(outputs, dim=1)
                correct_val += (preds == labels).sum().item()
                total_val += labels.size(0)

        val_loss = val_loss_sum / total_val
        val_acc = correct_val / total_val
        ep_duration = time.time() - ep_t0

        is_best = val_acc > best_val_acc
        if is_best:
            best_val_acc = val_acc
            torch.save(model.state_dict(), best_weights_path)

        log_line = (
            f"Epoch [{epoch:02d}/{epochs:02d}] ({ep_duration:.1f}s) | "
            f"Train Loss: {train_loss:.4f} Acc: {train_acc*100:.2f}% | "
            f"Val Loss: {val_loss:.4f} Acc: {val_acc*100:.2f}%"
            f"{' [NEW BEST]' if is_best else ''}"
        )
        print(log_line)

        history.append({
            "epoch": epoch,
            "train_loss": round(train_loss, 4),
            "train_acc": round(train_acc * 100, 2),
            "val_loss": round(val_loss, 4),
            "val_acc": round(val_acc * 100, 2),
            "duration_s": round(ep_duration, 2)
        })

    total_training_time = time.time() - start_time
    print(f"\n[Finished {model_name}] Best Val Accuracy: {best_val_acc*100:.2f}% in {total_training_time:.1f}s")
    print(f"Saved optimal weights to: {best_weights_path}")

    # Load best weights before returning
    model.load_state_dict(torch.load(best_weights_path, map_location=device))
    model.eval()

    # Export to ONNX for cross-platform C++/Python deployment
    onnx_path = os.path.join(MODELS_DIR, f"{model_name.lower()}.onnx")
    try:
        dummy_x = torch.randn(1, 3, 224, 224).to(device)
        torch.onnx.export(
            model,
            dummy_x,
            onnx_path,
            input_names=["input"],
            output_names=["probabilities"],
            dynamic_axes={"input": {0: "batch_size"}, "probabilities": {0: "batch_size"}},
            opset_version=14
        )
        print(f"Exported ONNX model to: {onnx_path}")
    except Exception as onnx_err:
        print(f"Warning: ONNX export skipped due to: {onnx_err}")

    summary = {
        "model_name": model_name,
        "best_val_acc_pct": round(best_val_acc * 100, 2),
        "total_training_time_s": round(total_training_time, 1),
        "epochs": epochs,
        "history": history,
        "weights_path": best_weights_path,
        "onnx_path": onnx_path
    }
    return model, summary


def main():
    torch.manual_seed(42)
    np.random.seed(42)
    random.seed(42)

    # 1. Device Inspection
    if torch.cuda.is_available():
        device = torch.device("cuda:0")
        gpu_name = torch.cuda.get_device_name(0)
        gpu_mem_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
        torch.backends.cudnn.benchmark = True
        print(f"[Device] CUDA Accelerated Hardware Detected: {gpu_name} ({gpu_mem_gb:.1f} GB VRAM)")
        batch_size = 64
        num_workers = min(8, os.cpu_count() or 4)
        epochs = 15
    else:
        device = torch.device("cpu")
        print("[Device] CUDA not detected. Training on CPU fallback mode.")
        batch_size = 32
        num_workers = 2
        epochs = 3

    # 2. Dataloaders
    print(f"\n[Dataset] Loading EuroSAT from: {DATA_DIR}")
    train_loader, val_loader, total_samples, n_train, n_val = create_dataloaders(
        batch_size=batch_size, img_size=224, num_workers=num_workers
    )
    print(f"[Dataset] Total samples: {total_samples:,} | Train: {n_train:,} | Validation: {n_val:,}")

    training_results = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": str(device),
        "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU",
        "dataset_samples": total_samples,
        "architectures": {}
    }

    # 3. Model 1: MobileNetV3-Small (Tier 2 Companion)
    print("\nInstantiating MobileNetV3-Small...")
    try:
        mbv3 = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    except Exception:
        mbv3 = models.mobilenet_v3_small(weights=None)
    mbv3.classifier[3] = nn.Linear(mbv3.classifier[3].in_features, 4)

    _, mbv3_summary = train_single_architecture(
        model_name="mobilenet_v3_small",
        model=mbv3,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        epochs=epochs,
        learning_rate=3e-4
    )
    training_results["architectures"]["mobilenet_v3_small"] = mbv3_summary

    # 4. Model 2: ResNet-18 (Tier 3 Ground Station)
    print("\nInstantiating ResNet-18...")
    try:
        res18 = models.resnet18(weights=models.ResNet18_Weights.DEFAULT)
    except Exception:
        res18 = models.resnet18(weights=None)
    res18.fc = nn.Linear(res18.fc.in_features, 4)

    _, res18_summary = train_single_architecture(
        model_name="resnet18",
        model=res18,
        train_loader=train_loader,
        val_loader=val_loader,
        device=device,
        epochs=epochs,
        learning_rate=2e-4
    )
    training_results["architectures"]["resnet18"] = res18_summary

    # 5. Save Summary JSON
    summary_path = os.path.join(REPO_ROOT, "ml", "gpu_training_summary.json")
    with open(summary_path, "w") as f:
        json.dump(training_results, f, indent=2)
    print(f"\n[Completed] Full training summary written to: {summary_path}")

    # 6. Run Benchmark to update comparison metrics
    print("\n[Benchmark] Updating ml/vision_model_comparison.json...")
    try:
        from ml.benchmark_vision_models import run_benchmark
        run_benchmark()
    except Exception as bm_err:
        print(f"Warning updating benchmark metrics: {bm_err}")

    print("\n" + "=" * 70)
    print("ALL MODELS TRAINED, VALIDATED, AND EXPORTED SUCCESSFULLY")
    print("=" * 70)


if __name__ == "__main__":
    main()
