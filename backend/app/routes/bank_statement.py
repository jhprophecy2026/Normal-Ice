"""
Bank Statement API
POST /api/bank-statement/{bill_no}/upload  — upload payment confirmation, Gemini extracts fields
GET  /api/bank-statement/{bill_no}         — get extracted bank statement for a case
"""
import logging

from fastapi import APIRouter, HTTPException, UploadFile, File

from app.models.bank_statement import BankStatementResponse
from app.services.supabase_client import get_supabase
from app.services.ocr import extract_pdf_text, render_gemini_thumbnails
from app.services.bank_statement_extractor import extract_bank_statement
from app.services.ocr_strategies.quality_checker import TextQualityChecker

logger = logging.getLogger(__name__)
router = APIRouter()

OCR_QUALITY_USABLE = 35.0


def _row_to_response(row: dict) -> BankStatementResponse:
    return BankStatementResponse(**{k: v for k, v in row.items() if k in BankStatementResponse.model_fields})


@router.get("/bank-statement/{bill_no}", response_model=BankStatementResponse)
async def get_bank_statement(bill_no: str):
    sb = get_supabase()
    res = sb.table("bank_statement_uploads").select("*").eq("bill_no", bill_no).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail="No bank statement found for this case.")
    return _row_to_response(res.data[0])


@router.post("/bank-statement/{bill_no}/upload", response_model=BankStatementResponse)
async def upload_bank_statement(bill_no: str, file: UploadFile = File(...)):
    sb = get_supabase()

    # Verify the case exists
    case_res = sb.table("pre_auth_requests").select("id").eq("bill_no", bill_no).execute()
    if not case_res.data:
        raise HTTPException(status_code=404, detail=f"No case found for bill_no='{bill_no}'")

    # Get settlement id if available
    sett_res = sb.table("settlement_requests").select("id").eq("bill_no", bill_no).execute()
    settlement_id = sett_res.data[0]["id"] if sett_res.data else None

    # Read file
    content = await file.read()

    # OCR
    text = ""
    images = None
    try:
        text = extract_pdf_text(content, file.filename or "upload.pdf")
        quality = TextQualityChecker.score(text)
        if quality < OCR_QUALITY_USABLE:
            images = render_gemini_thumbnails(content)
    except Exception as e:
        logger.warning(f"OCR failed for bank statement: {e}")

    # Gemini extraction
    extracted = extract_bank_statement(text, images)

    row = {
        "bill_no":       bill_no,
        "settlement_id": settlement_id,
        **{k: v for k, v in extracted.model_dump().items() if v is not None},
    }

    # Upsert — one record per bill_no
    existing = sb.table("bank_statement_uploads").select("id").eq("bill_no", bill_no).execute()
    if existing.data:
        res = sb.table("bank_statement_uploads").update(row).eq("bill_no", bill_no).execute()
    else:
        res = sb.table("bank_statement_uploads").insert(row).execute()

    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to save bank statement")

    return _row_to_response(res.data[0])
