"""
Configuration API Routes
GET  /api/config/cost-estimates         — return current cost estimates data array
PUT  /api/config/cost-estimates         — overwrite data array (preserves _meta)
POST /api/config/cost-estimates/upload  — upload a JSON file to replace data array
"""
import json
import logging
import os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import Any

logger = logging.getLogger(__name__)
router = APIRouter()

_DATASET_PATH = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "data", "disease_cost_estimates.json")
)


def _read_file() -> dict:
    with open(_DATASET_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Normalise to {_meta, data} shape
    if isinstance(raw, list):
        return {"_meta": {}, "data": raw}
    return raw


def _write_file(content: dict):
    with open(_DATASET_PATH, "w", encoding="utf-8") as f:
        json.dump(content, f, indent=2, ensure_ascii=False)


class CostEstimatesPayload(BaseModel):
    data: list[Any]


# ---------------------------------------------------------------------------

@router.get("/config/cost-estimates")
async def get_cost_estimates():
    """Return the current cost estimates (data array + meta)."""
    try:
        return _read_file()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read cost estimates: {e}")


@router.put("/config/cost-estimates")
async def update_cost_estimates(payload: CostEstimatesPayload):
    """Replace the data array. _meta block is preserved from the existing file."""
    try:
        existing = _read_file()
        existing["data"] = payload.data
        _write_file(existing)
        # Bust the lru_cache so cost_estimator picks up the new data immediately
        from app.services.cost_estimator import _load_dataset
        _load_dataset.cache_clear()
        logger.info(f"Cost estimates updated: {len(payload.data)} entries")
        return {"success": True, "count": len(payload.data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update cost estimates: {e}")


@router.post("/config/cost-estimates/upload")
async def upload_cost_estimates(file: UploadFile = File(...)):
    """
    Upload a JSON file. Accepted formats:
      - Array of entries  [...]
      - Object with data key  {"data": [...], ...}
    _meta from the existing file is preserved.
    """
    if not file.filename or not file.filename.lower().endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files are accepted")

    content = await file.read()
    try:
        uploaded = json.loads(content)
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=422, detail=f"Invalid JSON: {e}")

    new_data = uploaded if isinstance(uploaded, list) else uploaded.get("data")
    if not isinstance(new_data, list):
        raise HTTPException(status_code=422, detail="JSON must be an array or an object with a 'data' array")

    try:
        existing = _read_file()
        existing["data"] = new_data
        _write_file(existing)
        from app.services.cost_estimator import _load_dataset
        _load_dataset.cache_clear()
        logger.info(f"Cost estimates replaced via upload: {len(new_data)} entries")
        return {"success": True, "count": len(new_data)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded data: {e}")
