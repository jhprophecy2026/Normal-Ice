"""
Financial Audit API
GET /api/financial-audit/{abha_id}

Returns a pre-generated financial audit profile for a known ABHA patient.
Audits are stored in app/data/financial_audits.json, keyed by ABHA ID.
"""
import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException

logger = logging.getLogger(__name__)
router = APIRouter()

_DATA_FILE = Path(__file__).parent.parent / "data" / "financial_audits.json"

def _load() -> dict:
    with open(_DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


@router.get("/financial-audit/{abha_id}")
async def get_financial_audit(abha_id: str):
    """Return the pre-generated financial audit for an ABHA patient."""
    audits = _load()
    audit = audits.get(abha_id)
    if not audit:
        raise HTTPException(status_code=404, detail=f"No financial audit found for ABHA ID: {abha_id}")
    return audit
