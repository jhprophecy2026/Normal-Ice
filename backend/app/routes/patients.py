"""
Patient management endpoints.

GET  /api/patients                     — list all patients (searchable)
GET  /api/patients/{patient_id}        — full patient record
GET  /api/patients/{patient_id}/bundles — all FHIR bundles
GET  /api/patients/{patient_id}/flags  — unresolved billing flags (RCM report)
GET  /api/patients/{patient_id}/flags/all — full flag history
DELETE /api/patients/{patient_id}      — delete patient record
"""
from fastapi import APIRouter, HTTPException, Query
from app.services.patient_store import patient_store
import logging

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/patients")
async def list_patients(search: str = Query(default="", description="Search by name, ABHA ID, or patient ID")):
    """List all patients. Optionally filter by search query."""
    try:
        patients = patient_store.list_patients(search_query=search or None)
        return {"success": True, "patients": [p.model_dump() for p in patients], "count": len(patients)}
    except Exception as e:
        logger.error(f"list_patients failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}")
async def get_patient(patient_id: str):
    """Get full patient record including all observations, medications, and diagnoses."""
    try:
        record = patient_store.get_patient(patient_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        return {"success": True, "patient": record.model_dump()}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_patient {patient_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/bundles")
async def get_patient_bundles(patient_id: str):
    """Return all FHIR R4 bundles generated for this patient, newest first."""
    try:
        bundles = patient_store.get_patient_bundles(patient_id)
        return {"success": True, "patient_id": patient_id, "bundles": bundles, "count": len(bundles)}
    except Exception as e:
        logger.error(f"get_patient_bundles {patient_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/flags")
async def get_unresolved_flags(patient_id: str):
    """
    Revenue reconciliation report — returns all unresolved billing flags.
    These are fields still missing that would cause claim denial.
    Flags are automatically resolved when a subsequent upload fills the gap.
    """
    try:
        flags = patient_store.get_unresolved_flags(patient_id)
        critical = [f for f in flags if f.get("severity") == "critical"]
        warnings  = [f for f in flags if f.get("severity") == "warning"]
        return {
            "success":        True,
            "patient_id":     patient_id,
            "claim_ready":    len(critical) == 0,
            "critical_count": len(critical),
            "warning_count":  len(warnings),
            "flags":          flags,
        }
    except Exception as e:
        logger.error(f"get_unresolved_flags {patient_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/patients/{patient_id}/flags/all")
async def get_all_flags(patient_id: str):
    """Full billing flag history — includes resolved flags with timestamps."""
    try:
        flags = patient_store.get_all_flags(patient_id)
        return {"success": True, "patient_id": patient_id, "flags": flags, "count": len(flags)}
    except Exception as e:
        logger.error(f"get_all_flags {patient_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: str):
    """Delete a patient record and all associated data."""
    try:
        deleted = patient_store.delete_patient(patient_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Patient '{patient_id}' not found")
        return {"success": True, "message": f"Patient {patient_id} deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"delete_patient {patient_id} failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
