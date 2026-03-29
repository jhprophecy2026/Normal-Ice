"""
Settlement API Routes
POST /api/settlement                     — create settlement
GET  /api/settlement/by-bill/{bill_no}   — get by bill_no  (MUST be before /{id})
GET  /api/settlement/{id}                — get settlement by id
PUT  /api/settlement/{id}                — update settlement
"""
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.models.settlement import SettlementRequest, SettlementResponse
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


def _row_to_response(row: dict) -> SettlementResponse:
    return SettlementResponse(**{k: v for k, v in row.items() if k in SettlementResponse.model_fields})


def _compute_settlement_amount(claimed: float | None, deduction: float) -> float | None:
    if claimed is None:
        return None
    return max(0.0, claimed - deduction)


# ---------------------------------------------------------------------------
# Routes — order matters: by-bill BEFORE /{id}
# ---------------------------------------------------------------------------

@router.get("/settlement/by-bill/{bill_no}", response_model=SettlementResponse)
async def get_settlement_by_bill(bill_no: str):
    """Get a settlement record by bill number."""
    sb = get_supabase()
    res = sb.table("settlement_requests").select("*").eq("bill_no", bill_no).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"No settlement record found for bill_no='{bill_no}'")
    return _row_to_response(res.data[0])


@router.post("/settlement", response_model=SettlementResponse)
async def create_settlement(data: SettlementRequest):
    """
    Create a new settlement record.
    Auto-populates pre_auth_approved_amount from pre_auth_requests.total_estimated_cost
    and claimed_amount from discharge_requests.total_bill_amount if not provided.
    """
    sb = get_supabase()

    row = {k: v for k, v in data.model_dump().items() if v is not None}
    row.setdefault("deduction_amount", 0.0)
    row.setdefault("status", "pending")

    # Auto-populate pre_auth_approved_amount
    if row.get("pre_auth_approved_amount") is None and row.get("pre_auth_id"):
        pa_res = sb.table("pre_auth_requests").select("total_estimated_cost").eq(
            "id", row["pre_auth_id"]
        ).execute()
        if pa_res.data and pa_res.data[0].get("total_estimated_cost") is not None:
            row["pre_auth_approved_amount"] = pa_res.data[0]["total_estimated_cost"]

    # Auto-populate claimed_amount from discharge
    if row.get("claimed_amount") is None:
        discharge_id = row.get("discharge_id")
        bill_no = row.get("bill_no")
        dr = None
        if discharge_id:
            dr_res = sb.table("discharge_requests").select("total_bill_amount").eq(
                "id", discharge_id
            ).execute()
            dr = dr_res.data[0] if dr_res.data else None
        elif bill_no:
            dr_res = sb.table("discharge_requests").select("total_bill_amount").eq(
                "bill_no", bill_no
            ).execute()
            dr = dr_res.data[0] if dr_res.data else None
        if dr and dr.get("total_bill_amount") is not None:
            row["claimed_amount"] = dr["total_bill_amount"]

    # Compute final_settlement_amount
    row["final_settlement_amount"] = _compute_settlement_amount(
        row.get("claimed_amount"), row.get("deduction_amount", 0.0)
    )

    res = sb.table("settlement_requests").insert(row).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Failed to create settlement record")
    return _row_to_response(res.data[0])


@router.get("/settlement/{settlement_id}", response_model=SettlementResponse)
async def get_settlement(settlement_id: str):
    """Get a settlement record by ID."""
    sb = get_supabase()
    res = sb.table("settlement_requests").select("*").eq("id", settlement_id).execute()
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found")
    return _row_to_response(res.data[0])


@router.post("/settlement/{settlement_id}/finance-action", response_model=SettlementResponse)
async def finance_settlement_action(settlement_id: str, body: dict):
    """
    Finance manager approves or denies a settlement.
    body: { "action": "approve" | "deny", "notes": optional str }
    Sets status to 'finance_approved' or 'finance_denied'.
    """
    action = body.get("action")
    if action not in ("approve", "deny"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'deny'")
    sb = get_supabase()
    check = sb.table("settlement_requests").select("id").eq("id", settlement_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found")
    # Fetch current record to recompute final amount if deduction provided
    current = sb.table("settlement_requests").select("*").eq("id", settlement_id).execute()
    current_row = current.data[0] if current.data else {}

    updates: dict = {
        "status": "finance_approved" if action == "approve" else "finance_denied",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    notes = body.get("notes", "")
    if notes:
        updates["tpa_remarks"] = notes

    # Apply auto-deduction if provided (finance manager passes 5-10% of claimed)
    deduction_amount = body.get("deduction_amount")
    if deduction_amount is not None and action == "approve":
        updates["deduction_amount"] = float(deduction_amount)
        claimed = current_row.get("claimed_amount")
        updates["final_settlement_amount"] = _compute_settlement_amount(claimed, float(deduction_amount))

    res = sb.table("settlement_requests").update(updates).eq("id", settlement_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Update failed")
    return _row_to_response(res.data[0])


@router.post("/settlement/{settlement_id}/close", response_model=SettlementResponse)
async def close_settlement_case(settlement_id: str):
    """Mark a finance-approved settlement as fully closed."""
    sb = get_supabase()
    check = sb.table("settlement_requests").select("id, status").eq("id", settlement_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found")
    res = sb.table("settlement_requests").update({
        "status": "closed",
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", settlement_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Update failed")
    return _row_to_response(res.data[0])


@router.put("/settlement/{settlement_id}", response_model=SettlementResponse)
async def update_settlement(settlement_id: str, data: SettlementRequest):
    """
    Update a settlement record (status, deductions, remarks).
    Recomputes final_settlement_amount = claimed_amount - deduction_amount.
    """
    sb = get_supabase()

    check = sb.table("settlement_requests").select("*").eq("id", settlement_id).execute()
    if not check.data:
        raise HTTPException(status_code=404, detail=f"Settlement '{settlement_id}' not found")

    existing = check.data[0]
    updates = {k: v for k, v in data.model_dump().items() if v is not None}
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    # Use updated values or fall back to existing
    claimed = updates.get("claimed_amount", existing.get("claimed_amount"))
    deduction = updates.get("deduction_amount", existing.get("deduction_amount", 0.0))
    updates["final_settlement_amount"] = _compute_settlement_amount(claimed, deduction or 0.0)

    res = sb.table("settlement_requests").update(updates).eq("id", settlement_id).execute()
    if not res.data:
        raise HTTPException(status_code=500, detail="Update failed")
    return _row_to_response(res.data[0])
