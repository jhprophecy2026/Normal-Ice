"""
Discharge API Routes
POST /api/discharge                      — create discharge record
GET  /api/discharge/by-bill/{bill_no}    — get discharge by bill_no  (MUST be before /{id})
GET  /api/discharge/{id}                 — get discharge by id
PUT  /api/discharge/{id}                 — update discharge
POST /api/discharge/{id}/extract         — upload PDF, Gemini extracts fields, updates record
"""
import gc
import logging
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File

from app.models.discharge import DischargeRequest, DischargeResponse, DischargeExtract
from app.services.supabase_client import get_supabase
from app.services.ocr import extract_pdf_text, render_gemini_thumbnails
from app.services.discharge_extractor import extract_discharge_data
from app.services.claim_reconciliation import compute_discharge_revenue_flags
from app.services.ocr_strategies.quality_checker import TextQualityChecker
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

OCR_QUALITY_USABLE = 40.0


def _compute_revenue_flags(discharge: dict, pre_auth: dict | None) -> List[dict]:
    """Delegates to the claim reconciliation service."""
    return compute_discharge_revenue_flags(discharge, pre_auth)


def _row_to_response(row: dict) -> DischargeResponse:
    return DischargeResponse(**{k: v for k, v in row.items() if k in DischargeResponse.model_fields})


# ---------------------------------------------------------------------------
# Routes — order matters: by-bill BEFORE /{id}
# ---------------------------------------------------------------------------

@router.get("/discharge/by-bill/{bill_no}", response_model=DischargeResponse)
async def get_discharge_by_bill(bill_no: str):
    """Get a discharge record by bill number."""
    sb = get_supabase()
    res = sb.table("discharge_requests").select("*").eq("bill_no", bill_no).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"No discharge record found for bill_no='{bill_no}'")
    return _row_to_response(res.data[0])


@router.post("/discharge", response_model=DischargeResponse)
async def create_discharge(data: DischargeRequest):
    """Create a new discharge record and compute initial revenue flags."""
    sb = get_supabase()

    row = {k: v for k, v in data.model_dump().items() if v is not None}
    row["status"] = row.get("status", "pending")
    row["revenue_flags"] = []

    # Fetch pre-auth for flag computation
    pre_auth = None
    if data.pre_auth_id:
        pa_res = sb.table("pre_auth_requests").select("*").eq("id", data.pre_auth_id).execute()
        if pa_res.data:
            pre_auth = pa_res.data[0]

    flags = _compute_revenue_flags(row, pre_auth)
    row["revenue_flags"] = flags

    res = sb.table("discharge_requests").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create discharge record")
    return _row_to_response(res.data[0])


@router.get("/discharge/{discharge_id}", response_model=DischargeResponse)
async def get_discharge(discharge_id: str):
    """Get a discharge record by ID."""
    sb = get_supabase()
    res = sb.table("discharge_requests").select("*").eq("id", discharge_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Discharge '{discharge_id}' not found")
    return _row_to_response(res.data[0])


@router.put("/discharge/{discharge_id}", response_model=DischargeResponse)
async def update_discharge(discharge_id: str, data: DischargeRequest, background_tasks: BackgroundTasks):
    """Update a discharge record and recompute revenue flags."""
    sb = get_supabase()

    check = sb.table("discharge_requests").select("id, pre_auth_id").eq("id", discharge_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Discharge '{discharge_id}' not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Use pre_auth_id from update payload or existing record
    pre_auth_id = data.pre_auth_id or check.data[0].get("pre_auth_id")
    pre_auth = None
    if pre_auth_id:
        pa_res = sb.table("pre_auth_requests").select("*").eq("id", pre_auth_id).execute()
        if pa_res.data:
            pre_auth = pa_res.data[0]

    flags = _compute_revenue_flags(updates, pre_auth)
    updates["revenue_flags"] = flags

    res = sb.table("discharge_requests").update(updates).eq("id", discharge_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Update failed")

    # Send discharge email to TPA in background
    try:
        from app.services.email_service import send_email, get_tpa_email
        from app.services.email_templates import discharge_email
        dis_row = res.data[0]
        if pre_auth:
            tpa_email = get_tpa_email(pre_auth.get("tpa_name"))
            subject, html = discharge_email(dis_row, pre_auth)
            background_tasks.add_task(send_email, tpa_email, subject, html)
            logger.info(f"Discharge email queued → {tpa_email}")
    except Exception as email_err:
        logger.warning(f"Failed to queue discharge email: {email_err}")

    return _row_to_response(res.data[0])


@router.post("/discharge/{discharge_id}/send-tpa-email")
async def send_discharge_tpa_email(discharge_id: str, background_tasks: BackgroundTasks):
    """Send the discharge intimation email to TPA immediately."""
    sb = get_supabase()
    dis_res = sb.table("discharge_requests").select("*").eq("id", discharge_id).execute()
    if not dis_res.data:
        raise HTTPException(status_code=404, detail=f"Discharge '{discharge_id}' not found")
    dis_row = dis_res.data[0]
    pre_auth = None
    if dis_row.get("pre_auth_id"):
        pa_res = sb.table("pre_auth_requests").select("*").eq("id", dis_row["pre_auth_id"]).execute()
        if pa_res.data:
            pre_auth = pa_res.data[0]
    if not pre_auth:
        raise HTTPException(status_code=404, detail="Pre-auth not found for this discharge")
    try:
        from app.services.email_service import send_email, get_tpa_email
        from app.services.email_templates import discharge_email
        tpa_email = get_tpa_email(pre_auth.get("tpa_name"))
        subject, html = discharge_email(dis_row, pre_auth)
        background_tasks.add_task(send_email, tpa_email, subject, html)
    except Exception as e:
        logger.warning(f"Failed to queue discharge email: {e}")
    return {"queued": True}


@router.post("/discharge/{discharge_id}/extract", response_model=DischargeExtract)
async def extract_discharge(
    discharge_id: str,
    file: UploadFile = File(...),
):
    """
    Upload a discharge summary / final bill PDF. OCR + Gemini extracts
    billing and clinical fields, updates the discharge record, recomputes flags.
    Returns the extracted fields.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    sb = get_supabase()
    check = sb.table("discharge_requests").select("*").eq("id", discharge_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Discharge '{discharge_id}' not found")

    existing = check.data[0]

    # OCR
    try:
        extracted_text, pdf_ref = await extract_pdf_text(pdf_bytes)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"OCR failed: {e}")

    quality = TextQualityChecker.get_quality_score(extracted_text) if extracted_text else 0.0
    page_images = None
    if quality < OCR_QUALITY_USABLE:
        page_images = render_gemini_thumbnails(pdf_ref)

    del pdf_ref
    gc.collect()

    # Gemini extraction
    try:
        extract = await extract_discharge_data(extracted_text, page_images)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Discharge extraction failed: {e}")
    finally:
        if page_images:
            for img in page_images:
                img.close()
            gc.collect()

    # Merge extracted fields into existing record
    merged = dict(existing)
    updates: dict = {k: v for k, v in extract.model_dump().items() if v is not None}
    merged.update(updates)
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Recompute flags
    pre_auth = None
    pre_auth_id = existing.get("pre_auth_id")
    if pre_auth_id:
        pa_res = sb.table("pre_auth_requests").select("*").eq("id", pre_auth_id).execute()
        if pa_res.data:
            pre_auth = pa_res.data[0]

    flags = _compute_revenue_flags(merged, pre_auth)
    updates["revenue_flags"] = flags

    sb.table("discharge_requests").update(updates).eq("id", discharge_id).execute()

    # ── Full FHIR pipeline (non-fatal) ────────────────────────────────────────
    # Every discharge document also flows through the standard FHIR pipeline so
    # discharge diagnoses, procedures, and final billing data are recorded in the
    # patients table and tagged with the episode's bill_no.
    try:
        bill_no = existing.get("bill_no")
        pre_auth_id_local = existing.get("pre_auth_id")

        # Resolve patient_id: prefer pre-auth's stored patient_id, then abha_id
        pid_for_fhir = None
        if pre_auth_id_local:
            pa = sb.table("pre_auth_requests") \
                .select("abha_id, patient_id") \
                .eq("id", pre_auth_id_local).execute()
            if pa.data:
                pid_for_fhir = pa.data[0].get("patient_id") or pa.data[0].get("abha_id")

        from app.services.llm import extract_structured_data
        from app.services.fhir_mapper import generate_fhir_bundle
        from app.services.patient_store import patient_store

        full_data = await extract_structured_data(extracted_text, "auto", None)
        fhir_bundle, billing_flags = await generate_fhir_bundle(full_data)

        patient_store.save_patient(
            structured_data=full_data,
            fhir_bundle=fhir_bundle,
            billing_flags=billing_flags,
            filename=file.filename or "discharge_summary.pdf",
            extracted_text=extracted_text,
            bill_no=bill_no,
            patient_id_override=pid_for_fhir,
            document_type_override="discharge_summary",
        )
        logger.info(f"FHIR stored for discharge {discharge_id}: patient={pid_for_fhir}, bill={bill_no}")
    except Exception as fhir_err:
        logger.warning(f"FHIR pipeline (discharge doc) non-fatal: {fhir_err}")

    return extract
