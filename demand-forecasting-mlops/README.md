# Demand Forecasting MLOps Pipeline

A production-ready demand forecasting template with synthetic data generation, feature engineering, model training, evaluation, and a FastAPI inference service.

## Highlights
- Reproducible data generation
- Time-series lag features
- Training + evaluation scripts
- Saved model artifacts
- REST API for predictions

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/train_model.py
```

## Run the API

```bash
uvicorn src.api:app --reload --port 8000
```

### Sample Request

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"recent_values":[120,130,128,140,150,160,155],"horizon":1}'
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

## Notes
- Synthetic dataset is generated automatically if data/sales.csv is missing.
- Model artifacts and metrics are saved in artifacts/.