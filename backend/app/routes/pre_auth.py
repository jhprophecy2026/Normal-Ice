"""
Pre-Authorization API Routes
GET  /api/abha/{abha_id}                    — lookup patient from ABHA registry
POST /api/pre-auth                          — create a new pre-auth request
GET  /api/pre-auth                          — list all pre-auth requests
GET  /api/pre-auth/{id}                     — get a single pre-auth request
PUT  /api/pre-auth/{id}                     — update / save pre-auth request
POST /api/pre-auth/{id}/extract-medical     — upload PDF → Gemini fills medical fields
POST /api/pre-auth/{id}/generate-pdf        — generate downloadable PDF
"""
import gc
import logging
import random
import string
from fastapi import APIRouter, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.responses import Response


def _generate_bill_no() -> str:
    from datetime import datetime
    return f"BILL-{datetime.now().strftime('%Y%m%d')}-{''.join(random.choices(string.ascii_uppercase + string.digits, k=4))}"

from app.models.pre_auth import (
    AbhaPatient, PreAuthRequest, PreAuthResponse,
    MedicalExtract, get_missing_required,
)
from app.services.supabase_client import get_supabase
from app.services.ocr import extract_pdf_text, render_gemini_thumbnails
from app.services.pre_auth_extractor import extract_medical_for_preauth
from app.services.pdf_generator import generate_pre_auth_pdf
from app.services.ocr_strategies.quality_checker import TextQualityChecker
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

OCR_QUALITY_GOOD   = 75.0
OCR_QUALITY_USABLE = 40.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _row_to_response(row: dict) -> PreAuthResponse:
    missing = get_missing_required(PreAuthRequest(**{
        k: v for k, v in row.items()
        if k in PreAuthRequest.model_fields
    }))
    return PreAuthResponse(
        **{k: v for k, v in row.items() if k in PreAuthResponse.model_fields},
        missing_required_fields=missing,
    )


# ---------------------------------------------------------------------------
# ABHA Lookup
# ---------------------------------------------------------------------------

@router.get("/abha/{abha_id}", response_model=AbhaPatient)
async def lookup_abha(abha_id: str):
    """Fetch patient demographics and insurance details from the ABHA registry."""
    sb = get_supabase()
    res = sb.table("abha_registry").select("*").eq("abha_id", abha_id.strip()).execute()
    if not res.data:
        raise HTTPException(
            status_code=404,
            detail=f"No patient found with ABHA ID '{abha_id}'. Please fill the details manually.",
        )
    return AbhaPatient(**res.data[0])


# ---------------------------------------------------------------------------
# Pre-Auth CRUD
# ---------------------------------------------------------------------------

@router.post("/pre-auth", response_model=PreAuthResponse)
async def create_pre_auth(data: PreAuthRequest):
    """Create a new pre-auth request (starts as draft)."""
    sb = get_supabase()
    row = {k: v for k, v in data.model_dump().items() if v is not None}
    row["status"] = "draft"
    row["bill_no"] = _generate_bill_no()
    res = sb.table("pre_auth_requests").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create pre-auth request")
    return _row_to_response(res.data[0])


@router.get("/pre-auth", response_model=list[PreAuthResponse])
async def list_pre_auths():
    """List all pre-auth requests, newest first."""
    sb = get_supabase()
    res = sb.table("pre_auth_requests").select("*").order("created_at", desc=True).execute()
    return [_row_to_response(r) for r in (res.data or [])]


@router.get("/pre-auth/{pre_auth_id}", response_model=PreAuthResponse)
async def get_pre_auth(pre_auth_id: str):
    """Get a single pre-auth request by ID."""
    sb = get_supabase()
    res = sb.table("pre_auth_requests").select("*").eq("id", pre_auth_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Pre-auth '{pre_auth_id}' not found")
    return _row_to_response(res.data[0])


@router.put("/pre-auth/{pre_auth_id}", response_model=PreAuthResponse)
async def update_pre_auth(pre_auth_id: str, data: PreAuthRequest):
    """Update an existing pre-auth request with new field values."""
    from datetime import datetime, timezone
    sb = get_supabase()

    # Verify it exists
    check = sb.table("pre_auth_requests").select("id").eq("id", pre_auth_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Pre-auth '{pre_auth_id}' not found")

    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    res = sb.table("pre_auth_requests").update(updates).eq("id", pre_auth_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Update failed")
    return _row_to_response(res.data[0])


# ---------------------------------------------------------------------------
# Medical Extraction from uploaded PDF
# ---------------------------------------------------------------------------

@router.post("/pre-auth/{pre_auth_id}/extract-medical", response_model=MedicalExtract)
async def extract_medical(
    pre_auth_id: str,
    file: UploadFile = File(...),
):
    """
    Upload a clinical PDF. OCR + Gemini extracts medical fields and
    auto-updates the pre-auth record. Returns the extracted fields.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(pdf_bytes) > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

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
        extract = await extract_medical_for_preauth(extracted_text, page_images)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Medical extraction failed: {e}")
    finally:
        if page_images:
            for img in page_images:
                img.close()
            gc.collect()

    # Persist extracted fields into the pre-auth record (only non-null values)
    from datetime import datetime, timezone
    sb = get_supabase()
    updates = {k: v for k, v in extract.model_dump().items() if v is not None}
    if updates:
        updates["updated_at"] = datetime.now(timezone.utc).isoformat()
        sb.table("pre_auth_requests").update(updates).eq("id", pre_auth_id).execute()

    # ── Full FHIR pipeline (non-fatal) ────────────────────────────────────────
    # Run the same pipeline as the simple upload route so that every document
    # uploaded through the pre-auth flow also creates a FHIR bundle, updates
    # patient observations/medications, and populates the patients table.
    # All records are tagged with the episode's bill_no for full traceability.
    try:
        pa_meta = sb.table("pre_auth_requests") \
            .select("bill_no, abha_id, patient_id") \
            .eq("id", pre_auth_id).execute()
        if pa_meta.data:
            bill_no  = pa_meta.data[0].get("bill_no")
            abha_id  = pa_meta.data[0].get("abha_id")

            from app.services.llm import extract_structured_data
            from app.services.fhir_mapper import generate_fhir_bundle
            from app.services.patient_store import patient_store

            full_data = await extract_structured_data(extracted_text, "auto", None)
            fhir_bundle, billing_flags = await generate_fhir_bundle(full_data)

            pid, _ = patient_store.save_patient(
                structured_data=full_data,
                fhir_bundle=fhir_bundle,
                billing_flags=billing_flags,
                filename=file.filename or "medical_report.pdf",
                extracted_text=extracted_text,
                bill_no=bill_no,
                patient_id_override=abha_id,
            )
            # Back-link pre_auth to the patient record (idempotent update)
            if pid:
                sb.table("pre_auth_requests") \
                    .update({"patient_id": pid, "updated_at": datetime.now(timezone.utc).isoformat()}) \
                    .eq("id", pre_auth_id).execute()
            logger.info(f"FHIR stored for pre-auth {pre_auth_id}: patient={pid}, bill={bill_no}")
    except Exception as fhir_err:
        logger.warning(f"FHIR pipeline (pre-auth doc) non-fatal: {fhir_err}")

    return extract


# ---------------------------------------------------------------------------
# PDF Generation
# ---------------------------------------------------------------------------

@router.post("/pre-auth/{pre_auth_id}/generate-pdf")
async def generate_pdf(pre_auth_id: str, background_tasks: BackgroundTasks):
    """
    Generate and return a downloadable pre-auth PDF.
    Works even if some required fields are missing (they appear as red placeholders).
    """
    sb = get_supabase()
    res = sb.table("pre_auth_requests").select("*").eq("id", pre_auth_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Pre-auth '{pre_auth_id}' not found")

    row = res.data[0]
    pre_auth = PreAuthRequest(**{k: v for k, v in row.items() if k in PreAuthRequest.model_fields})

    try:
        pdf_bytes = generate_pre_auth_pdf(pre_auth, pre_auth_id=pre_auth_id)
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {e}")

    # Update status to submitted
    from datetime import datetime, timezone
    sb.table("pre_auth_requests").update({
        "status": "submitted",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", pre_auth_id).execute()

    # Send pre-auth email to TPA in background
    try:
        from app.services.email_service import send_email, get_tpa_email
        from app.services.email_templates import preauth_email
        tpa_email = get_tpa_email(row.get("tpa_name"))
        subject, html = preauth_email(row)
        background_tasks.add_task(send_email, tpa_email, subject, html)
        logger.info(f"Pre-auth email queued → {tpa_email}")
    except Exception as email_err:
        logger.warning(f"Failed to queue pre-auth email: {email_err}")

    filename = f"pre_auth_{pre_auth_id[:8]}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ---------------------------------------------------------------------------
# Send TPA email on demand
# ---------------------------------------------------------------------------

@router.post("/pre-auth/{pre_auth_id}/send-tpa-email")
async def send_pre_auth_tpa_email(pre_auth_id: str, background_tasks: BackgroundTasks):
    """Send the pre-auth verification email to TPA immediately."""
    sb = get_supabase()
    res = sb.table("pre_auth_requests").select("*").eq("id", pre_auth_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Pre-auth '{pre_auth_id}' not found")
    row = res.data[0]
    try:
        from app.services.email_service import send_email, get_tpa_email
        from app.services.email_templates import preauth_email
        tpa_email = get_tpa_email(row.get("tpa_name"))
        subject, html = preauth_email(row)
        background_tasks.add_task(send_email, tpa_email, subject, html)
    except Exception as e:
        logger.warning(f"Failed to queue pre-auth email: {e}")
    return {"queued": True}


# ---------------------------------------------------------------------------
# Cost Estimation — auto-fill billing fields from disease dataset
# ---------------------------------------------------------------------------

@router.get("/pre-auth/estimate-costs")
async def estimate_costs(
    icd10: str = "",
    diagnosis: str = "",
):
    """
    Given an ICD-10 code and/or diagnosis text, return estimated cost
    breakdown from the embedded disease cost dataset.

    Returns pre-auth form cost fields ready to be auto-filled:
        room_rent_per_day, icu_charges_per_day, ot_charges,
        professional_fees, medicines_consumables,
        investigation_diagnostics_cost, total_estimated_cost,
        expected_days_in_hospital, days_in_icu, room_type,
        surgery_name, icd10_pcs_code
    """
    from app.services.cost_estimator import estimate_costs as _estimate
    result = _estimate(icd10_code=icd10 or None, diagnosis_text=diagnosis or None)
    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"No cost estimate found for icd10='{icd10}' diagnosis='{diagnosis}'. "
                   "Fill costs manually.",
        )
    return result


# ---------------------------------------------------------------------------
# Dummy / Seed Data — pre-fill form with realistic test data
# ---------------------------------------------------------------------------

DUMMY_CASES = [
    {
        "label": "STEMI — Cardiac (PTCA)",
        "data": {
            "hospital_name": "Apollo Hospitals",
            "hospital_location": "Jubilee Hills, Hyderabad",
            "hospital_email": "claims@apollohyd.com",
            "rohini_id": "H-AP-HYD-001",
            "patient_name": "Ramesh Kumar Sharma",
            "gender": "male",
            "age": 54,
            "date_of_birth": "1970-03-15",
            "contact": "9876543210",
            "policy_no": "HDFC-HI-2024-88321",
            "insured_card_id": "IC-88321-A",
            "doctor_name": "Dr. Suresh Reddy",
            "doctor_contact": "9900112233",
            "presenting_complaints": "Severe chest pain radiating to left arm for 3 hours, diaphoresis, shortness of breath",
            "duration_of_illness": "3 hours",
            "date_of_first_consultation": "2026-03-28",
            "provisional_diagnosis": "ST-Elevation Myocardial Infarction (Anterior Wall STEMI)",
            "icd10_diagnosis_code": "I21.0",
            "clinical_findings": "ECG: ST elevation in V1-V4, Troponin I raised (12.4 ng/mL), BP 90/60 mmHg",
            "treatment_surgical": True,
            "surgery_name": "Percutaneous Transluminal Coronary Angioplasty (PTCA with Drug-Eluting Stent)",
            "icd10_pcs_code": "02703ZZ",
            "admission_date": "2026-03-28",
            "admission_time": "14:30",
            "admission_type": "Emergency",
            "expected_days_in_hospital": 7,
            "days_in_icu": 3,
            "room_type": "single",
        },
    },
    {
        "label": "Knee Replacement — Orthopedic (TKR)",
        "data": {
            "hospital_name": "Fortis Memorial Research Institute",
            "hospital_location": "Gurugram, Haryana",
            "hospital_email": "cashless@fortishealth.com",
            "rohini_id": "H-FR-GGN-005",
            "patient_name": "Sunita Devi Agarwal",
            "gender": "female",
            "age": 62,
            "date_of_birth": "1963-07-22",
            "contact": "9811234567",
            "policy_no": "MAX-GHI-2023-44512",
            "insured_card_id": "IC-44512-B",
            "doctor_name": "Dr. Ashok Rajgopal",
            "doctor_contact": "9810099887",
            "presenting_complaints": "Severe bilateral knee pain for 2 years, unable to walk more than 100 metres, failed conservative management",
            "duration_of_illness": "2 years",
            "date_of_first_consultation": "2026-03-01",
            "provisional_diagnosis": "Primary Osteoarthritis of Knee (Grade IV Bilateral)",
            "icd10_diagnosis_code": "M17.1",
            "clinical_findings": "X-ray: Grade IV OA with bone-on-bone contact, varus deformity 12 degrees",
            "treatment_surgical": True,
            "surgery_name": "Total Knee Replacement (TKR) - Left Knee",
            "icd10_pcs_code": "0SRC0J9",
            "admission_date": "2026-04-05",
            "admission_time": "08:00",
            "admission_type": "Planned",
            "expected_days_in_hospital": 7,
            "days_in_icu": 0,
            "room_type": "single",
            "diabetes": True,
            "diabetes_since": "2015",
            "hypertension": True,
            "hypertension_since": "2018",
        },
    },
    {
        "label": "Appendicitis — General Surgery (Laparoscopic)",
        "data": {
            "hospital_name": "Manipal Hospitals",
            "hospital_location": "Whitefield, Bengaluru",
            "hospital_email": "tpa@manipalbangalore.com",
            "rohini_id": "H-MN-BLR-012",
            "patient_name": "Vikram Singh Chauhan",
            "gender": "male",
            "age": 28,
            "date_of_birth": "1998-11-05",
            "contact": "7654321098",
            "policy_no": "STAR-HI-2025-19834",
            "insured_card_id": "IC-19834-C",
            "doctor_name": "Dr. Priya Menon",
            "doctor_contact": "9845001122",
            "presenting_complaints": "Acute pain right iliac fossa for 12 hours, fever 101°F, nausea",
            "duration_of_illness": "12 hours",
            "date_of_first_consultation": "2026-03-28",
            "provisional_diagnosis": "Acute Appendicitis",
            "icd10_diagnosis_code": "K35.2",
            "clinical_findings": "Tenderness at McBurney's point, rebound tenderness present, TLC 14,800",
            "treatment_surgical": True,
            "surgery_name": "Laparoscopic Appendicectomy",
            "icd10_pcs_code": "0DTJ4ZZ",
            "admission_date": "2026-03-28",
            "admission_time": "22:15",
            "admission_type": "Emergency",
            "expected_days_in_hospital": 4,
            "days_in_icu": 0,
            "room_type": "twin-sharing",
        },
    },
    {
        "label": "Pneumonia — Respiratory (Medical Management)",
        "data": {
            "hospital_name": "Medanta The Medicity",
            "hospital_location": "Sector 38, Gurugram",
            "hospital_email": "cashless@medanta.org",
            "rohini_id": "H-MD-GGN-002",
            "patient_name": "Kavita Rani Mishra",
            "gender": "female",
            "age": 45,
            "date_of_birth": "1981-01-30",
            "contact": "9312456789",
            "policy_no": "BAJAJ-AHI-2024-67123",
            "insured_card_id": "IC-67123-D",
            "doctor_name": "Dr. Randeep Guleria",
            "doctor_contact": "9810055000",
            "presenting_complaints": "High fever 103°F for 4 days, productive cough with yellow sputum, breathlessness",
            "duration_of_illness": "4 days",
            "date_of_first_consultation": "2026-03-25",
            "provisional_diagnosis": "Severe Community-Acquired Pneumonia (CAP)",
            "icd10_diagnosis_code": "J18.9",
            "clinical_findings": "SpO2 88% on room air, bilateral crepitations, CXR: right lower lobe consolidation",
            "treatment_medical_management": True,
            "medical_management_details": "IV Piperacillin-Tazobactam, IV Azithromycin, oxygen support, nebulisation",
            "admission_date": "2026-03-28",
            "admission_time": "10:00",
            "admission_type": "Emergency",
            "expected_days_in_hospital": 7,
            "days_in_icu": 2,
            "room_type": "twin-sharing",
            "diabetes": True,
            "diabetes_since": "2019",
        },
    },
    {
        "label": "LSCS — Obstetrics (Maternity)",
        "data": {
            "hospital_name": "Rainbow Children's Hospital",
            "hospital_location": "Banjara Hills, Hyderabad",
            "hospital_email": "tpa@rainbowhospitals.in",
            "rohini_id": "H-RB-HYD-008",
            "patient_name": "Anjali Reddy",
            "gender": "female",
            "age": 29,
            "date_of_birth": "1996-06-12",
            "contact": "9988776655",
            "policy_no": "NIAC-GHI-2022-33214",
            "insured_card_id": "IC-33214-E",
            "doctor_name": "Dr. Mohana Venugopal",
            "doctor_contact": "9849001234",
            "presenting_complaints": "38 weeks gestation, labour pains, prior C-section history",
            "duration_of_illness": "38 weeks",
            "date_of_first_consultation": "2026-03-28",
            "provisional_diagnosis": "Pregnancy 38 Weeks - Elective Lower Segment Caesarean Section",
            "icd10_diagnosis_code": "O82.0",
            "clinical_findings": "Foetal heart rate normal, previous LSCS scar, cephalic presentation",
            "treatment_surgical": True,
            "surgery_name": "Lower Segment Caesarean Section (LSCS)",
            "icd10_pcs_code": "10D00Z1",
            "admission_date": "2026-04-01",
            "admission_time": "07:30",
            "admission_type": "Planned",
            "expected_days_in_hospital": 5,
            "days_in_icu": 0,
            "room_type": "twin-sharing",
            "maternity_g": "G2",
            "maternity_p": "P1",
            "maternity_l": "L1",
            "maternity_a": "A0",
        },
    },
]


@router.get("/pre-auth/dummy-cases")
async def list_dummy_cases():
    """Return list of dummy case labels for the seed UI."""
    return [{"index": i, "label": c["label"]} for i, c in enumerate(DUMMY_CASES)]


@router.get("/pre-auth/dummy-cases/{index}")
async def get_dummy_case(index: int):
    """
    Return a dummy pre-auth form payload for the given index.
    Costs are auto-calculated from the disease dataset.
    """
    from app.services.cost_estimator import estimate_costs as _estimate

    if index < 0 or index >= len(DUMMY_CASES):
        raise HTTPException(status_code=404, detail="Dummy case index out of range")

    case = DUMMY_CASES[index]
    form_data = dict(case["data"])

    # Auto-calculate costs from the disease dataset
    icd10 = form_data.get("icd10_diagnosis_code")
    diagnosis = form_data.get("provisional_diagnosis")
    costs = _estimate(icd10_code=icd10, diagnosis_text=diagnosis)

    if costs:
        form_data.setdefault("room_rent_per_day",              costs["room_rent_per_day"])
        form_data.setdefault("icu_charges_per_day",            costs["icu_charges_per_day"])
        form_data.setdefault("ot_charges",                     costs["ot_charges"])
        form_data.setdefault("professional_fees",              costs["professional_fees"])
        form_data.setdefault("medicines_consumables",          costs["medicines_consumables"])
        form_data.setdefault("investigation_diagnostics_cost", costs["investigation_diagnostics_cost"])
        form_data.setdefault("other_hospital_expenses",        costs["other_hospital_expenses"])
        form_data.setdefault("total_estimated_cost",           costs["total_estimated_cost"])
        if costs.get("surgery_name") and not form_data.get("surgery_name"):
            form_data["surgery_name"] = costs["surgery_name"]
        if costs.get("icd10_pcs_code") and not form_data.get("icd10_pcs_code"):
            form_data["icd10_pcs_code"] = costs["icd10_pcs_code"]

    return {"label": case["label"], "data": form_data}
