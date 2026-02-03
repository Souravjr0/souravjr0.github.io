from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .features import build_feature_row
from .predict import load_model

app = FastAPI(title="Demand Forecasting API")


class ForecastRequest(BaseModel):
    recent_values: list[float] = Field(..., min_items=7)
    horizon: int = Field(1, ge=1, le=30)


@app.on_event("startup")
def _load():
    app.state.model = load_model()


@app.post("/predict")
def predict(request: ForecastRequest):
    if len(request.recent_values) < 7:
        raise HTTPException(status_code=400, detail="Need at least 7 recent values")
    features = build_feature_row(request.recent_values)
    prediction = app.state.model.predict(features)[0]
    return {"forecast": float(prediction), "horizon": request.horizon}
