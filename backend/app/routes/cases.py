"""
Cases API Routes — unified lifecycle view per bill number
GET /api/cases               — list all cases (pre_auth_requests with a bill_no)
GET /api/cases/{bill_no}     — full case detail (pre_auth + enhancements + discharge + settlement)
"""
import logging

from fastapi import APIRouter, HTTPException

from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/cases")
async def list_cases():
    """
    List all cases derived from pre_auth_requests that have a bill_no assigned.
    Joins with enhancement, discharge, and settlement tables to compute lifecycle flags.
    """
    sb = get_supabase()

    # Fetch all pre-auth rows that have a bill_no
    pa_res = sb.table("pre_auth_requests").select("*").not_.is_("bill_no", "null").order(
        "created_at", desc=True
    ).execute()

    rows = pa_res.data or []
    if not rows:
        return []

    bill_nos = [r["bill_no"] for r in rows if r.get("bill_no")]
    pre_auth_ids = [r["id"] for r in rows]

    # Batch-fetch enhancements, discharges, settlements
    enh_res = sb.table("enhancement_requests").select("pre_auth_id").in_(
        "pre_auth_id", pre_auth_ids
    ).execute() if pre_auth_ids else None

    dis_res = sb.table("discharge_requests").select("bill_no").in_(
        "bill_no", bill_nos
    ).execute() if bill_nos else None

    set_res = sb.table("settlement_requests").select("bill_no, status").in_(
        "bill_no", bill_nos
    ).execute() if bill_nos else None

    enh_pre_auth_ids = set(r["pre_auth_id"] for r in (enh_res.data or []) if r.get("pre_auth_id"))
    dis_bill_nos = set(r["bill_no"] for r in (dis_res.data or []) if r.get("bill_no"))
    # Map bill_no -> settlement status
    set_bill_status: dict = {}
    for r in (set_res.data or []):
        if r.get("bill_no"):
            set_bill_status[r["bill_no"]] = r.get("status", "pending")

    cases = []
    for r in rows:
        bill_no = r.get("bill_no")
        pre_auth_id = r["id"]
        cases.append({
            "bill_no": bill_no,
            "pre_auth_id": pre_auth_id,
            "patient_id": r.get("patient_id"),  # links to patients table
            "patient_name": r.get("patient_name"),
            "abha_id": r.get("abha_id"),
            "hospital_name": r.get("hospital_name"),
            "pre_auth_status": r.get("status", "draft"),
            "total_estimated_cost": r.get("total_estimated_cost"),
            "has_enhancement": pre_auth_id in enh_pre_auth_ids,
            "has_discharge": bill_no in dis_bill_nos if bill_no else False,
            "has_settlement": bill_no in set_bill_status if bill_no else False,
            "settlement_status": set_bill_status.get(bill_no) if bill_no else None,
            "created_at": r.get("created_at"),
        })

    return cases


@router.get("/cases/{bill_no}")
async def get_case(bill_no: str):
    """
    Return full case detail for the given bill number:
    pre_auth + enhancements + discharge + settlement.
    """
    sb = get_supabase()

    # Pre-auth
    pa_res = sb.table("pre_auth_requests").select("*").eq("bill_no", bill_no).execute()
    if not pa_res.data:
        raise HTTPException(status_code=404, detail=f"No case found for bill_no='{bill_no}'")

    pre_auth = pa_res.data[0]
    pre_auth_id = pre_auth["id"]

    # Enhancements
    enh_res = sb.table("enhancement_requests").select("*").eq(
        "pre_auth_id", pre_auth_id
    ).order("sequence_no").execute()
    enhancements = enh_res.data or []

    # Discharge
    dis_res = sb.table("discharge_requests").select("*").eq("bill_no", bill_no).execute()
    discharge = dis_res.data[0] if dis_res.data else None

    # Settlement
    set_res = sb.table("settlement_requests").select("*").eq("bill_no", bill_no).execute()
    settlement = set_res.data[0] if set_res.data else None

    return {
        "bill_no": bill_no,
        "pre_auth": pre_auth,
        "enhancements": enhancements,
        "discharge": discharge,
        "settlement": settlement,
    }
