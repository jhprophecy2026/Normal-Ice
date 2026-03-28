"""
Patient persistence layer — Supabase backend.

Public API (unchanged from previous JSON implementation so process.py needs minimal edits):
    save_patient(structured_data, fhir_bundle, billing_flags, filename) -> (patient_id, action)
    get_patient(patient_id) -> StoredPatientRecord | None
    list_patients(search_query) -> List[PatientSummary]
    delete_patient(patient_id) -> bool
    get_patient_bundles(patient_id) -> List[dict]
    get_unresolved_flags(patient_id) -> List[dict]

Merge strategy (revenue reconciliation focus):
    - Demographics: fill NULL columns only — never overwrite existing data
    - Observations: deduplicate by test_name + value + unit
    - Medications: deduplicate by medication_name + dosage + frequency
    - Diagnoses / ICD-10: append new codes not already stored
    - FHIR bundles: always append (full history kept)
    - Billing flags: insert new flags; auto-resolve old flags for fields
      that are now populated in the latest upload
"""
import hashlib
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Union

from app.models.schemas import LabReportData, PrescriptionData, BillingFlag
from app.models.patient_store import StoredPatientRecord, PatientSummary, DocumentRecord
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Patient ID resolution
# ---------------------------------------------------------------------------

def _name_dob_hash(name: str, dob: str) -> str:
    key = f"{name.strip().lower()}|{dob.strip()}"
    return "h_" + hashlib.sha256(key.encode()).hexdigest()[:14]


def _resolve_patient_id(patient_info) -> tuple[str, bool]:
    """
    Returns (patient_id, is_existing).

    Priority:
    1. ABHA ID / explicit patient_id  → look up in DB
    2. Name + DOB hash                → look up in DB
    3. New UUID                       → create fresh record
    """
    sb = get_supabase()

    # 1. Match by explicit patient_id / ABHA
    if patient_info and patient_info.patient_id:
        pid = patient_info.patient_id.strip()
        res = sb.table("patients").select("patient_id").eq("patient_id", pid).execute()
        if res.data:
            return pid, True
        # Also check abha_id column
        res2 = sb.table("patients").select("patient_id").eq("abha_id", pid).execute()
        if res2.data:
            return res2.data[0]["patient_id"], True
        return pid, False

    # 2. Match by name + DOB hash
    if patient_info and patient_info.name and patient_info.date_of_birth:
        h = _name_dob_hash(patient_info.name, patient_info.date_of_birth)
        res = sb.table("patients").select("patient_id").eq("patient_id", h).execute()
        if res.data:
            return h, True
        return h, False

    # 3. New UUID
    return "p_" + str(uuid.uuid4())[:12], False


# ---------------------------------------------------------------------------
# Demographics merge (fill NULLs only)
# ---------------------------------------------------------------------------

def _build_demographics_upsert(
    patient_id: str,
    structured_data: Union[LabReportData, PrescriptionData],
    existing: Optional[dict],
) -> dict:
    """
    Build the dict to upsert into `patients`.
    For an existing record, only fields currently NULL are updated.
    """
    pi   = structured_data.patient
    prac = structured_data.practitioner

    def keep(col: str, new_val):
        """Return new_val only if the existing record has NULL for that column."""
        if existing and existing.get(col) is not None:
            return existing[col]
        return new_val

    row = {"patient_id": patient_id}

    if pi:
        row["abha_id"]       = keep("abha_id",       pi.patient_id)
        row["name"]          = keep("name",           pi.name)
        row["age"]           = keep("age",            pi.age)
        row["gender"]        = keep("gender",         pi.gender)
        row["date_of_birth"] = keep("date_of_birth",  pi.date_of_birth)
        row["contact"]       = keep("contact",        pi.contact)
        row["insurance_id"]  = keep("insurance_id",   pi.insurance_id)

    if prac:
        row["practitioner_name"] = keep("practitioner_name", prac.name)
        row["practitioner_npi"]  = keep("practitioner_npi",  prac.npi)
        row["practitioner_id"]   = keep("practitioner_id",   prac.practitioner_id)

    if structured_data.organization_name:
        row["organization_name"] = keep("organization_name", structured_data.organization_name)

    # Merge diagnoses and ICD-10 codes (array append, no duplicates)
    existing_diagnoses  = existing.get("diagnoses", [])  if existing else []
    existing_icd10      = existing.get("icd10_codes", []) if existing else []

    new_diagnoses = [structured_data.diagnosis] if structured_data.diagnosis else []
    new_icd10     = getattr(structured_data, "icd10_codes", []) or []

    merged_diagnoses = list(dict.fromkeys(existing_diagnoses + new_diagnoses))  # preserves order + dedup
    merged_icd10     = list(dict.fromkeys(existing_icd10     + new_icd10))

    row["diagnoses"]   = merged_diagnoses
    row["icd10_codes"] = merged_icd10
    row["updated_at"]  = _now()

    return row


# ---------------------------------------------------------------------------
# Observation / medication dedup helpers
# ---------------------------------------------------------------------------

def _obs_key(obs: dict) -> str:
    return f"{obs.get('test_name','')}|{obs.get('value','')}|{obs.get('unit','')}"


def _med_key(med: dict) -> str:
    return f"{med.get('medication_name','')}|{med.get('dosage','')}|{med.get('frequency','')}"


# ---------------------------------------------------------------------------
# Billing flag auto-resolution
# ---------------------------------------------------------------------------

def _resolve_flags_for_filled_fields(
    patient_id: str,
    structured_data: Union[LabReportData, PrescriptionData],
):
    """
    Mark previously critical/warning flags as resolved when the new upload
    provides the missing data.

    Example: previous upload had no DOB → flag created.
    New upload has DOB → that flag is now resolved.
    """
    sb = get_supabase()
    pi   = structured_data.patient
    prac = structured_data.practitioner

    fields_now_filled = []

    if pi:
        if pi.name:          fields_now_filled.append("patient.name")
        if pi.date_of_birth: fields_now_filled.append("patient.date_of_birth")
        if pi.patient_id:    fields_now_filled.append("patient.patient_id")

    if prac and prac.npi:
        fields_now_filled.append("practitioner.npi")

    if getattr(structured_data, "icd10_codes", []):
        fields_now_filled.append("icd10_codes")

    if isinstance(structured_data, LabReportData):
        if structured_data.observations:
            fields_now_filled.append("observations")
        if all(o.loinc_code for o in structured_data.observations):
            fields_now_filled.append("observations.loinc_code")

    if isinstance(structured_data, PrescriptionData):
        if structured_data.medications:
            fields_now_filled.append("medications")

    if not fields_now_filled:
        return

    now = _now()
    for field in fields_now_filled:
        sb.table("billing_flags") \
          .update({"resolved": True, "resolved_at": now}) \
          .eq("patient_id", patient_id) \
          .eq("field", field) \
          .eq("resolved", False) \
          .execute()

    logger.info(f"Auto-resolved flags for fields: {fields_now_filled}")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class PatientStore:

    def save_patient(
        self,
        structured_data: Union[LabReportData, PrescriptionData],
        fhir_bundle: dict,
        billing_flags: List[BillingFlag],
        filename: str,
        extracted_text: str = "",
        bill_no: Optional[str] = None,
        patient_id_override: Optional[str] = None,
        document_type_override: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Persist one processed document for a patient.

        Args:
            bill_no:              Episode identifier — tags all stored records with the pre-auth
                                  bill number so the full episode is queryable in one shot.
            patient_id_override:  Force a specific patient_id (e.g. ABHA ID from pre-auth)
                                  instead of deriving it from the extracted document.
            document_type_override: Override the auto-detected document type
                                  (e.g. "discharge_summary").

        Returns:
            (patient_id, action)  where action is "created" or "updated"
        """
        sb = get_supabase()

        # 1. Resolve patient identity
        if patient_id_override:
            # Prefer the caller-supplied identity (e.g. ABHA ID from pre-auth form)
            r = sb.table("patients").select("patient_id").eq("patient_id", patient_id_override).execute()
            if r.data:
                patient_id, is_existing = patient_id_override, True
            else:
                # Also try abha_id column (patient_id might be an ABHA-format string)
                r2 = sb.table("patients").select("patient_id").eq("abha_id", patient_id_override).execute()
                if r2.data:
                    patient_id, is_existing = r2.data[0]["patient_id"], True
                else:
                    patient_id, is_existing = patient_id_override, False
        else:
            patient_id, is_existing = _resolve_patient_id(structured_data.patient)

        # 2. Fetch current record if exists (needed for merge)
        existing = None
        if is_existing:
            res = sb.table("patients").select("*").eq("patient_id", patient_id).execute()
            existing = res.data[0] if res.data else None

        # 3. Upsert patient demographics
        demo_row = _build_demographics_upsert(patient_id, structured_data, existing)
        sb.table("patients").upsert(demo_row).execute()

        # 4. Insert document record
        doc_type = document_type_override or (
            "lab_report" if isinstance(structured_data, LabReportData) else "prescription"
        )
        doc_row: dict = {
            "patient_id":             patient_id,
            "filename":               filename,
            "document_type":          doc_type,
            "upload_date":            _now(),
            "extracted_text_preview": extracted_text[:500] if extracted_text else None,
        }
        if bill_no:
            doc_row["bill_no"] = bill_no
        doc_res = sb.table("patient_documents").insert(doc_row).execute()
        document_id = doc_res.data[0]["id"] if doc_res.data else None

        # 5. Insert observations (deduplicated)
        if isinstance(structured_data, LabReportData) and structured_data.observations:
            # Fetch existing keys for this patient
            existing_obs = sb.table("patient_observations") \
                             .select("test_name,value,unit") \
                             .eq("patient_id", patient_id).execute()
            existing_keys = {_obs_key(o) for o in (existing_obs.data or [])}

            service_date = getattr(structured_data, "service_date", None) or structured_data.report_date
            new_obs = []
            for obs in structured_data.observations:
                od = obs.model_dump()
                if _obs_key(od) not in existing_keys:
                    ob_row: dict = {
                        "patient_id":      patient_id,
                        "document_id":     document_id,
                        "test_name":       obs.test_name,
                        "loinc_code":      obs.loinc_code,
                        "cpt_code":        obs.cpt_code,
                        "value":           obs.value,
                        "unit":            obs.unit,
                        "reference_range": obs.reference_range,
                        "status":          obs.status or "final",
                        "interpretation":  obs.interpretation,
                        "service_date":    service_date,
                    }
                    if bill_no:
                        ob_row["bill_no"] = bill_no
                    new_obs.append(ob_row)
            if new_obs:
                sb.table("patient_observations").insert(new_obs).execute()

        # 6. Insert medications (deduplicated) — works for PrescriptionData and mixed LabReportData
        medications_to_save = []
        prescription_date = None
        if isinstance(structured_data, PrescriptionData):
            medications_to_save = structured_data.medications
            prescription_date   = structured_data.prescription_date
        elif isinstance(structured_data, LabReportData) and structured_data.medications:
            medications_to_save = structured_data.medications
            prescription_date   = structured_data.report_date

        if medications_to_save:
            existing_meds = sb.table("patient_medications") \
                              .select("medication_name,dosage,frequency") \
                              .eq("patient_id", patient_id).execute()
            existing_keys = {_med_key(m) for m in (existing_meds.data or [])}

            new_meds = []
            for med in structured_data.medications:
                md = med.model_dump()
                if _med_key(md) not in existing_keys:
                    med_row: dict = {
                        "patient_id":        patient_id,
                        "document_id":       document_id,
                        "medication_name":   med.medication_name,
                        "rxnorm_code":       med.rxnorm_code,
                        "dosage":            med.dosage,
                        "frequency":         med.frequency,
                        "duration":          med.duration,
                        "route":             med.route,
                        "instructions":      med.instructions,
                        "prescription_date": structured_data.prescription_date,
                    }
                    if bill_no:
                        med_row["bill_no"] = bill_no
                    new_meds.append(med_row)
            if new_meds:
                sb.table("patient_medications").insert(new_meds).execute()

        # 7. Insert FHIR bundle (tagged with bill_no when available)
        bundle_row: dict = {
            "patient_id":    patient_id,
            "document_id":   document_id,
            "document_type": doc_type,
            "bundle":        fhir_bundle,
        }
        if bill_no:
            bundle_row["bill_no"] = bill_no
        bundle_res = sb.table("fhir_bundles").insert(bundle_row).execute()
        bundle_id = bundle_res.data[0]["id"] if bundle_res.data else None

        # 8. Auto-resolve flags from previous uploads that are now filled
        if is_existing:
            _resolve_flags_for_filled_fields(patient_id, structured_data)

        # 9. Insert new billing flags
        if billing_flags and bundle_id:
            flag_rows = [
                {
                    "patient_id": patient_id,
                    "bundle_id":  bundle_id,
                    "field":      f.field,
                    "severity":   f.severity,
                    "message":    f.message,
                    "resolved":   False,
                }
                for f in billing_flags
            ]
            sb.table("billing_flags").insert(flag_rows).execute()

        action = "updated" if is_existing else "created"
        critical = sum(1 for f in billing_flags if f.severity == "critical")
        logger.info(
            f"Patient {patient_id} {action} | doc: {filename} | "
            f"{critical} critical billing flags"
        )
        return patient_id, action

    def get_patient(self, patient_id: str) -> Optional[StoredPatientRecord]:
        """Fetch full patient record with all accumulated clinical data."""
        sb = get_supabase()

        res = sb.table("patients").select("*").eq("patient_id", patient_id).execute()
        if not res.data:
            return None
        row = res.data[0]

        # Fetch related data
        obs_res  = sb.table("patient_observations").select("*").eq("patient_id", patient_id).execute()
        med_res  = sb.table("patient_medications").select("*").eq("patient_id", patient_id).execute()
        doc_res  = sb.table("patient_documents").select("*").eq("patient_id", patient_id).execute()
        bun_res  = sb.table("fhir_bundles").select("bundle").eq("patient_id", patient_id).execute()

        documents = [
            DocumentRecord(
                filename=d["filename"],
                upload_date=d["upload_date"],
                document_type=d["document_type"],
                extracted_text_preview=d.get("extracted_text_preview"),
                bill_no=d.get("bill_no"),
            )
            for d in (doc_res.data or [])
        ]

        return StoredPatientRecord(
            patient_id=row["patient_id"],
            abha_id=row.get("abha_id"),
            name=row.get("name"),
            age=row.get("age"),
            gender=row.get("gender"),
            date_of_birth=row.get("date_of_birth"),
            contact=row.get("contact"),
            practitioner_name=row.get("practitioner_name"),
            practitioner_id=row.get("practitioner_id"),
            organization_name=row.get("organization_name"),
            observations=obs_res.data or [],
            medications=med_res.data or [],
            diagnoses=row.get("diagnoses") or [],
            fhir_bundles=[b["bundle"] for b in (bun_res.data or [])],
            documents=documents,
            created_at=row.get("created_at", ""),
            updated_at=row.get("updated_at", ""),
        )

    def list_patients(self, search_query: Optional[str] = None) -> List[PatientSummary]:
        sb = get_supabase()

        query = sb.table("patients").select("patient_id,name,abha_id,updated_at")

        if search_query:
            q = search_query.strip()
            query = query.or_(
                f"name.ilike.%{q}%,abha_id.ilike.%{q}%,patient_id.ilike.%{q}%"
            )

        res = query.order("updated_at", desc=True).execute()

        summaries = []
        for row in (res.data or []):
            # Get document count
            count_res = sb.table("patient_documents") \
                          .select("id", count="exact") \
                          .eq("patient_id", row["patient_id"]).execute()
            doc_count = count_res.count or 0

            summaries.append(PatientSummary(
                patient_id=row["patient_id"],
                name=row.get("name"),
                abha_id=row.get("abha_id"),
                document_count=doc_count,
                last_updated=row.get("updated_at", ""),
            ))

        return summaries

    def delete_patient(self, patient_id: str) -> bool:
        sb = get_supabase()
        res = sb.table("patients").delete().eq("patient_id", patient_id).execute()
        return bool(res.data)

    def get_patient_bundles(self, patient_id: str) -> List[dict]:
        """Return all FHIR bundles for a patient, newest first."""
        sb = get_supabase()
        res = sb.table("fhir_bundles") \
                .select("id,document_type,created_at,bundle") \
                .eq("patient_id", patient_id) \
                .order("created_at", desc=True) \
                .execute()
        return res.data or []

    def get_unresolved_flags(self, patient_id: str) -> List[dict]:
        """Return all unresolved billing flags — the live revenue reconciliation report."""
        sb = get_supabase()
        res = sb.table("billing_flags") \
                .select("*") \
                .eq("patient_id", patient_id) \
                .eq("resolved", False) \
                .order("severity")  \
                .execute()
        return res.data or []

    def get_all_flags(self, patient_id: str) -> List[dict]:
        """Return full billing flag history (resolved + unresolved)."""
        sb = get_supabase()
        res = sb.table("billing_flags") \
                .select("*") \
                .eq("patient_id", patient_id) \
                .order("created_at", desc=True) \
                .execute()
        return res.data or []


# Module-level singleton — import this everywhere
patient_store = PatientStore()
