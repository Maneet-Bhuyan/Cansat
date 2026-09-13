# Flight Data & Remote Sensing Datasets

This directory contains satellite remote sensing datasets and aerial archives used for training the Edge TinyML landing zone classifier.

## Assets

* **EuroSAT_RGB.zip**: Tracked archive (89.9 MB) containing Sentinel-2 multispectral satellite imagery (27,000 images, 64x64 RGB across 10 land cover classes).
* **eurosat/**: Extracted image directory (gitignored to prevent repository bloat). Automatically extracted during workstation setup or via python ml/download_dataset.py.
