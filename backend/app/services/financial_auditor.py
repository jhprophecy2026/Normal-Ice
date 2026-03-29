"""
Financial Audit Service

Given a full case context (pre-auth + enhancements + discharge), uses Gemini to
produce a charge-by-charge narrative audit that explains WHY each cost was incurred,
referencing the actual clinical documents provided.
"""
import json
import logging
from typing import Optional
from pydantic import BaseModel

from app.services.llm import GeminiExtractor

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Output models
# ---------------------------------------------------------------------------

class AuditLineItem(BaseModel):
    category: str
    billed_amount: Optional[float] = None
    pre_auth_amount: Optional[float] = None
    variance: Optional[float] = None           # billed - pre_auth (positive = overrun)
    status: str                                 # "justified" | "overrun" | "unexplained" | "not_billed"
    explanation: str                            # Gemini narrative
    references: list[str] = []                 # which doc fields support this


class FinancialAuditReport(BaseModel):
    overall_summary: str
    risk_level: str                            # "low" | "medium" | "high"
    total_pre_auth: Optional[float] = None
    total_enhanced: Optional[float] = None
    total_billed: Optional[float] = None
    total_variance: Optional[float] = None
    line_items: list[AuditLineItem] = []
    recommendations: list[str] = []


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

_PROMPT = """You are a senior medical billing auditor for an insurance TPA (Third Party Administrator) in India.

You have been given the complete case data for a patient hospitalization episode. Your job is to produce a financial audit that EXPLAINS each charge category by referencing the actual clinical and administrative documents provided.

=== CASE DATA ===

PRE-AUTHORIZATION:
{pre_auth_json}

ENHANCEMENT REQUEST(S) (if any):
{enhancements_json}

DISCHARGE / FINAL BILL:
{discharge_json}

=== INSTRUCTIONS ===

For EACH of the following charge categories, provide a structured audit entry:
1. Room Charges
2. ICU Charges
3. Surgery / OT Charges
4. Medicine & Consumables
5. Investigation / Diagnostics
6. Other Charges

For each category:
- State the billed amount (from discharge) and pre-authorized amount (from pre-auth or last enhancement)
- Explain WHY this cost was incurred, citing specific fields from the documents (e.g. "Pre-auth stated admission_type=ICU, days_in_icu=3 at Rs X/day")
- If an enhancement was raised that changed this amount, reference it
- Set status as:
  * "justified"     — billed amount is within authorized limits and clinically explained
  * "overrun"       — billed amount exceeds authorized amount without a covering enhancement
  * "unexplained"   — charges present but no clinical context found in documents
  * "not_billed"    — authorized in pre-auth but not billed at discharge

Also produce:
- overall_summary: 2-3 sentence narrative of the entire financial picture
- risk_level: "low" if all justified, "medium" if minor overruns, "high" if major unexplained charges
- recommendations: list of specific actions for the TPA reviewer

Return ONLY this JSON structure (no markdown, no code blocks):
{{
  "overall_summary": "string",
  "risk_level": "low|medium|high",
  "total_pre_auth": number or null,
  "total_enhanced": number or null,
  "total_billed": number or null,
  "total_variance": number or null,
  "line_items": [
    {{
      "category": "string",
      "billed_amount": number or null,
      "pre_auth_amount": number or null,
      "variance": number or null,
      "status": "justified|overrun|unexplained|not_billed",
      "explanation": "string — cite specific document fields",
      "references": ["Pre-auth field: ...", "Enhancement #1: ...", "Discharge field: ..."]
    }}
  ],
  "recommendations": ["string", ...]
}}
"""


# ---------------------------------------------------------------------------
# Service function
# ---------------------------------------------------------------------------

async def run_financial_audit(
    pre_auth: dict | None,
    enhancements: list[dict],
    discharge: dict,
) -> FinancialAuditReport:
    """
    Call Gemini to audit the discharge bill against pre-auth and enhancement data.
    Returns a FinancialAuditReport with per-category justifications.
    """
    # Sanitise: remove internal/noise keys before sending to Gemini
    _noise = {"id", "created_at", "updated_at", "revenue_flags", "status"}

    def _clean(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in _noise and v is not None}

    pre_auth_str  = json.dumps(_clean(pre_auth), indent=2)  if pre_auth   else "Not available"
    enhance_str   = json.dumps([_clean(e) for e in enhancements], indent=2) if enhancements else "None"
    discharge_str = json.dumps(_clean(discharge), indent=2)

    prompt = _PROMPT.format(
        pre_auth_json=pre_auth_str,
        enhancements_json=enhance_str,
        discharge_json=discharge_str,
    )

    extractor = GeminiExtractor()
    raw = await extractor._call_gemini_with_retry(prompt)
    logger.info(f"Financial audit Gemini response ({len(raw)} chars)")

    cleaned = extractor._clean_json_response(raw)
    data = json.loads(cleaned)

    # Build line items
    line_items = [
        AuditLineItem(**{k: v for k, v in item.items() if k in AuditLineItem.model_fields})
        for item in data.get("line_items", [])
    ]

    return FinancialAuditReport(
        overall_summary=data.get("overall_summary", ""),
        risk_level=data.get("risk_level", "medium"),
        total_pre_auth=data.get("total_pre_auth"),
        total_enhanced=data.get("total_enhanced"),
        total_billed=data.get("total_billed"),
        total_variance=data.get("total_variance"),
        line_items=line_items,
        recommendations=data.get("recommendations", []),
    )
