"""
Disease Cost Estimator
======================
Looks up a diagnosis (by ICD-10 code or free-text name) in the embedded
disease_cost_estimates.json dataset and returns a pre-filled cost breakdown
suitable for auto-filling the Pre-Auth form cost section.

Matching priority:
  1. Exact ICD-10 code match (e.g. "I21.0")
  2. ICD-10 prefix match (first 3 characters, e.g. "I21")
  3. Alias keyword match (case-insensitive substring in aliases list)
  4. Diagnosis name fuzzy match (word overlap)
"""
from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

_DATASET_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "disease_cost_estimates.json")


@lru_cache(maxsize=1)
def _load_dataset() -> list[dict]:
    path = os.path.normpath(_DATASET_PATH)
    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)
    # Support both legacy array format and new {_meta, data} object format
    data = raw["data"] if isinstance(raw, dict) else raw
    logger.info(f"Disease cost dataset loaded: {len(data)} entries")
    return data


def estimate_costs(
    icd10_code: Optional[str] = None,
    diagnosis_text: Optional[str] = None,
) -> Optional[dict]:
    """
    Return cost estimate dict for the given ICD-10 code / diagnosis text, or
    None if no match found.

    The returned dict maps directly to PreAuthRequest cost fields:
        room_rent_per_day, icu_charges_per_day, ot_charges, professional_fees,
        medicines_consumables, investigation_diagnostics_cost, total_estimated_cost,
        expected_days_in_hospital, days_in_icu, room_type,
        surgery_name, icd10_pcs_code, treatment_type, category
    """
    dataset = _load_dataset()
    match = _find_match(dataset, icd10_code, diagnosis_text)
    if not match:
        return None
    return _build_estimate(match)


def _find_match(dataset: list[dict], icd10_code: Optional[str], diagnosis_text: Optional[str]) -> Optional[dict]:
    code = (icd10_code or "").strip().upper()
    text = (diagnosis_text or "").lower().strip()

    # 1. Exact ICD-10 match
    if code:
        for entry in dataset:
            if entry["icd10_code"].upper() == code:
                return entry

    # 2. ICD-10 prefix match (first 3 chars)
    if len(code) >= 3:
        prefix = code[:3]
        for entry in dataset:
            if entry["icd10_code"].upper().startswith(prefix):
                return entry

    # 3. Alias keyword match
    if text:
        for entry in dataset:
            for alias in entry.get("aliases", []):
                if alias in text or text in alias:
                    return entry

    # 4. Word-overlap on diagnosis name
    if text:
        stopwords = {"the", "of", "and", "with", "for", "due", "to", "in", "a", "an",
                     "or", "by", "on", "at", "as", "requiring", "acute", "chronic"}
        text_words = set(text.split()) - stopwords
        best_score = 0
        best_entry = None
        for entry in dataset:
            diag_words = set(entry["diagnosis"].lower().split()) - stopwords
            if not diag_words:
                continue
            overlap = len(text_words & diag_words) / max(len(text_words), len(diag_words))
            if overlap > best_score:
                best_score = overlap
                best_entry = entry
        if best_score >= 0.3:
            return best_entry

    return None


def _build_estimate(entry: dict) -> dict:
    """Compute total and map to pre-auth form fields."""
    los  = entry["typical_los_days"]
    icu  = entry["icu_days"]

    room_total  = entry["room_rent_per_day"] * max(los - icu, 1)
    icu_total   = entry["icu_charges_per_day"] * icu
    ot          = entry["ot_charges"]
    prof        = entry["professional_fees"]
    meds        = entry["medicines_consumables"]
    invest      = entry["investigation_diagnostics"]
    other       = entry["other_charges"]

    total = room_total + icu_total + ot + prof + meds + invest + other

    return {
        # Cost fields
        "room_rent_per_day":               entry["room_rent_per_day"],
        "icu_charges_per_day":             entry["icu_charges_per_day"],
        "ot_charges":                      ot,
        "professional_fees":               prof,
        "medicines_consumables":           meds,
        "investigation_diagnostics_cost":  invest,
        "other_hospital_expenses":         other,
        "total_estimated_cost":            total,
        # Admission fields
        "expected_days_in_hospital":       los,
        "days_in_icu":                     icu,
        "room_type":                       entry["room_type"],
        # Clinical fields (used to auto-fill surgery / treatment sections)
        "surgery_name":                    entry.get("surgery_name"),
        "icd10_pcs_code":                  entry.get("icd10_pcs_code"),
        "treatment_type":                  entry["treatment_type"],
        "category":                        entry["category"],
        # Metadata
        "matched_icd10":                   entry["icd10_code"],
        "matched_diagnosis":               entry["diagnosis"],
    }
