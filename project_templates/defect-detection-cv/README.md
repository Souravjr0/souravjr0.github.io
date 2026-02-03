# Industrial Defect Detection (Computer Vision)

A lightweight CV baseline for defect screening. Generates synthetic images, extracts edge-based features, and trains an SVM classifier.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/generate_dataset.py
python scripts/train_model.py
```

## Predict

```bash
python -m src.predict --image data/sample.png
```

## Project Structure

```
.
├── artifacts/
├── data/
├── scripts/
├── src/
└── requirements.txt
```
