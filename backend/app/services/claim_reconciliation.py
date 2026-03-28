"""
India-specific Insurance Claim Reconciliation Engine
=====================================================

Two public functions:

1. check_upload_billing_flags(data)
   Called on every document upload (lab report / prescription).
   Flags patient identity, provider credentials, coding, and
   document-specific issues that will block or reduce claim payment.

2. compute_discharge_revenue_flags(discharge, pre_auth)
   Called when a discharge record is created/updated.
   Compares final bill against pre-auth estimates and applies
   IRDAI / TPA adjudication rules to flag claim risks.

Sources:
  - IRDAI Health Insurance Regulations 2016 + subsequent circulars
  - IRDA (TPA) Regulations 2016
  - Medi Assist / Vipul / Heritage TPA adjudication guidelines
  - NHA Cashless Claims Settlement SOP
  - Standard pre-auth form (Part C Revised) checks
  - CGHS rate schedule (surgical deductions reference)
"""
from __future__ import annotations

import logging
from typing import List, Union

from app.models.schemas import BillingFlag, LabReportData, PrescriptionData

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _c(field: str, message: str) -> BillingFlag:
    """Shorthand for a critical billing flag."""
    return BillingFlag(field=field, severity="critical", message=message)


def _w(field: str, message: str) -> BillingFlag:
    """Shorthand for a warning billing flag."""
    return BillingFlag(field=field, severity="warning", message=message)


def _discharge_flag(field: str, severity: str, message: str) -> dict:
    return {"field": field, "severity": severity, "message": message}


# ---------------------------------------------------------------------------
# 1. Upload-time billing flags (Lab Report / Prescription)
# ---------------------------------------------------------------------------

def check_upload_billing_flags(
    data: Union[LabReportData, PrescriptionData],
) -> List[BillingFlag]:
    """
    India-specific claim completeness check run on every uploaded document.

    Covers IRDAI mandatory fields, TPA matching requirements, ICD-10 coding,
    and document-type-specific completeness (lab values, prescription dosages).
    """
    flags: List[BillingFlag] = []

    # ── A. PATIENT IDENTITY ────────────────────────────────────────────────
    if not data.patient:
        flags.append(_c("patient",
            "No patient information extracted — claim cannot be submitted without patient identity."))
    else:
        p = data.patient
        if not p.name:
            flags.append(_c("patient.name",
                "Patient name missing — required on all insurance claim types (IRDAI Reg. 2016)."))

        if not p.date_of_birth:
            flags.append(_c("patient.date_of_birth",
                "Date of birth missing — required for TPA member identity verification; "
                "mismatch between hospital record and policy triggers claim hold."))

        if not p.gender:
            flags.append(_w("patient.gender",
                "Gender missing — required for maternity benefit eligibility checks "
                "and gender-specific procedure coverage verification."))

        if not p.patient_id:
            flags.append(_w("patient.patient_id",
                "ABHA ID / Member ID / Insured Card ID missing — TPA may be unable to "
                "match record to active policy; claim may be held pending clarification."))

    # ── B. PROVIDER CREDENTIALS ───────────────────────────────────────────
    if not data.practitioner or not data.practitioner.name:
        flags.append(_c("practitioner.name",
            "Treating doctor name missing — mandatory for TPA empanelment verification "
            "and specialist/surgical claim adjudication."))

    if data.practitioner and not data.practitioner.npi:
        # npi field stores MCI/NMC registration number in this India-context system
        flags.append(_w("practitioner.registration_no",
            "Doctor's MCI/NMC registration number missing — required for surgical, "
            "specialist, and high-value claims; insurer may deduct or query without it."))

    if not data.organization_name:
        flags.append(_w("organization_name",
            "Hospital / lab name missing — required for provider empanelment verification. "
            "Non-empanelled providers are not covered under cashless."))

    # ── C. DIAGNOSIS CODING ───────────────────────────────────────────────
    if not data.icd10_codes:
        flags.append(_c("icd10_codes",
            "ICD-10-CM diagnosis code missing — medical necessity cannot be established. "
            "IRDAI mandates coded diagnosis for all cashless and reimbursement claims; "
            "claim will be denied without a valid ICD-10 code."))

    # ── D. SERVICE DATE ───────────────────────────────────────────────────
    service_date = (
        getattr(data, "report_date", None)
        or getattr(data, "prescription_date", None)
        or getattr(data, "service_date", None)
    )
    if not service_date:
        flags.append(_c("service_date",
            "Date of service missing — required for claim period validation and "
            "pre/post-hospitalization expense window calculation (30/60 days)."))

    # ── E. LAB REPORT SPECIFIC ────────────────────────────────────────────
    if isinstance(data, LabReportData):
        if not data.observations:
            flags.append(_c("observations",
                "No lab test results extracted — nothing to support diagnosis or bill; "
                "investigation claim will have no line items."))
        else:
            missing_value = [o.test_name for o in data.observations if o.value is None]
            missing_unit  = [o.test_name for o in data.observations if not o.unit]
            no_loinc      = [o.test_name for o in data.observations if not o.loinc_code]
            no_reference  = [o.test_name for o in data.observations if not o.reference_range]

            if missing_value:
                flags.append(_w("observations.value",
                    f"{len(missing_value)} test(s) have no result value: "
                    f"{', '.join(missing_value[:3])}{'…' if len(missing_value) > 3 else ''}. "
                    "Insurers may reject investigation claims without documented results."))

            if missing_unit:
                flags.append(_w("observations.unit",
                    f"{len(missing_unit)} test(s) missing unit of measurement — "
                    "required for reference range validation by TPA clinical team."))

            if no_loinc:
                flags.append(_w("observations.loinc_code",
                    f"{len(no_loinc)} test(s) have no LOINC code: "
                    f"{', '.join(no_loinc[:3])}{'…' if len(no_loinc) > 3 else ''}. "
                    "LOINC codes required for ABDM/FHIR-based digital claim submission."))

            # Abnormal results without interpretation — a clinical risk flag
            abnormal = [
                o.test_name for o in data.observations
                if o.interpretation and o.interpretation.upper() in ("H", "L", "HH", "LL", "A", "ABNORMAL", "HIGH", "LOW")
                and not o.reference_range
            ]
            if abnormal:
                flags.append(_w("observations.reference_range",
                    f"{len(abnormal)} abnormal result(s) have no reference range — "
                    "clinical team cannot assess severity; may cause audit query."))

    # ── F. PRESCRIPTION SPECIFIC ──────────────────────────────────────────
    elif isinstance(data, PrescriptionData):
        if not data.medications:
            flags.append(_c("medications",
                "No medications extracted — nothing to bill in pharmacy claim."))
        else:
            missing_dosage = [m.medication_name for m in data.medications if not m.dosage]
            missing_freq   = [m.medication_name for m in data.medications if not m.frequency]
            missing_dur    = [m.medication_name for m in data.medications if not m.duration]
            no_rxnorm      = [m.medication_name for m in data.medications if not m.rxnorm_code]

            if missing_dosage:
                flags.append(_w("medications.dosage",
                    f"{len(missing_dosage)} medication(s) missing dosage strength: "
                    f"{', '.join(missing_dosage[:3])}{'…' if len(missing_dosage) > 3 else ''}. "
                    "TPA pharmacy auditors reject bills where dosage is not specified."))

            if missing_freq:
                flags.append(_w("medications.frequency",
                    f"{len(missing_freq)} medication(s) missing frequency — "
                    "required for quantity-per-day verification against pharmacy bills."))

            if missing_dur:
                flags.append(_w("medications.duration",
                    f"{len(missing_dur)} medication(s) missing duration — "
                    "insurer cannot verify if quantity billed matches prescription."))

            if no_rxnorm:
                flags.append(_w("medications.rxnorm_code",
                    f"{len(no_rxnorm)} medication(s) have no RxNorm code — "
                    "required for ABDM digital prescription interoperability."))

    critical_count = sum(1 for f in flags if f.severity == "critical")
    warning_count  = sum(1 for f in flags if f.severity == "warning")
    logger.info(
        f"Upload billing flags: {critical_count} critical, {warning_count} warning "
        f"[doc_type={data.document_type}]"
    )
    return flags


# ---------------------------------------------------------------------------
# 2. Discharge revenue reconciliation flags
# ---------------------------------------------------------------------------

def compute_discharge_revenue_flags(
    discharge: dict,
    pre_auth: dict | None,
) -> List[dict]:
    """
    Revenue reconciliation for cashless hospitalization discharge.

    Applies IRDAI / TPA adjudication rules:
      A. Critical documentation completeness
      B. Bill itemization integrity
      C. Diagnosis & procedure code matching
      D. Per-category financial variance vs pre-auth
      E. Policy compliance (RTA, PED, maternity, substance abuse)
      F. Standalone bill sanity checks
    """
    flags: List[dict] = []

    def _cf(field, msg):
        flags.append(_discharge_flag(field, "critical", msg))

    def _wf(field, msg):
        flags.append(_discharge_flag(field, "warning", msg))

    # ── A. CRITICAL DOCUMENTATION ─────────────────────────────────────────

    if not discharge.get("discharge_date"):
        _cf("discharge_date",
            "Discharge date missing — required for claim period calculation, "
            "post-hospitalization expense window (60 days), and TPA file closure.")

    if not discharge.get("final_diagnosis"):
        _cf("final_diagnosis",
            "Final diagnosis missing from discharge summary — IRDAI mandates confirmed "
            "diagnosis on settlement; claim cannot be adjudicated without it.")

    if not discharge.get("final_icd10_codes"):
        _cf("final_icd10_codes",
            "Final ICD-10 diagnosis code missing — required for IRDAI-compliant cashless "
            "settlement; TPA systems reject claims without a coded diagnosis.")

    if not discharge.get("total_bill_amount"):
        _cf("total_bill_amount",
            "Total bill amount not captured — settlement cannot proceed without a final bill figure.")

    procedure_codes = (discharge.get("procedure_codes") or "").strip()
    if not procedure_codes:
        _wf("procedure_codes",
            "Procedure codes (ICD-10 PCS / CPT) not provided — mandatory for all surgical "
            "and interventional claims; TPA will hold payment pending code clarification.")

    # ── B. BILL ITEMIZATION INTEGRITY ─────────────────────────────────────

    line_items = {
        "room_charges":          discharge.get("room_charges") or 0,
        "icu_charges":           discharge.get("icu_charges") or 0,
        "surgery_charges":       discharge.get("surgery_charges") or 0,
        "medicine_charges":      discharge.get("medicine_charges") or 0,
        "investigation_charges": discharge.get("investigation_charges") or 0,
        "other_charges":         discharge.get("other_charges") or 0,
    }
    computed_total = sum(line_items.values())
    stated_total   = discharge.get("total_bill_amount") or 0

    if computed_total > 0 and stated_total > 0:
        diff = abs(stated_total - computed_total)
        if diff > stated_total * 0.05:
            _wf("total_bill_amount",
                f"Bill line items sum (₹{computed_total:,.0f}) differs from stated total "
                f"(₹{stated_total:,.0f}) by ₹{diff:,.0f} — itemized bill does not reconcile; "
                "TPA auditor will flag this as a discrepancy.")

    # Surgery billed but no procedure code
    if line_items["surgery_charges"] > 0 and not procedure_codes:
        _cf("procedure_codes",
            f"Surgery/OT charges of ₹{line_items['surgery_charges']:,.0f} billed but no "
            "procedure code provided — insurers will not settle surgical claims without "
            "ICD-10 PCS or CPT codes on the final bill.")

    # Procedure codes present but surgery charges = 0
    if procedure_codes and line_items["surgery_charges"] == 0:
        _wf("surgery_charges",
            "Procedure codes are listed but surgery/OT charges are ₹0 — possible billing "
            "omission or package rate not broken out; TPA may query itemization.")

    # ── C. DIAGNOSIS & PROCEDURE CODE MATCHING ────────────────────────────

    if pre_auth:
        discharge_icd = (discharge.get("final_icd10_codes") or "").strip()
        preauth_icd   = (pre_auth.get("icd10_diagnosis_code") or "").strip()

        if discharge_icd and preauth_icd:
            d_prefix = discharge_icd.split(",")[0].strip()[:3].upper()
            p_prefix = preauth_icd[:3].upper()
            if d_prefix and p_prefix and d_prefix != p_prefix:
                _cf("final_icd10_codes",
                    f"Diagnosis code mismatch: pre-auth='{preauth_icd}' vs discharge='{discharge_icd}'. "
                    "A change in principal diagnosis category requires an Enhancement Request with clinical "
                    "justification; insurer may deny or short-settle without prior approval.")

        # Diagnosis text divergence (word-overlap heuristic)
        d_diag = (discharge.get("final_diagnosis") or "").lower()
        p_diag = (pre_auth.get("provisional_diagnosis") or "").lower()
        if d_diag and p_diag:
            stopwords = {"the","of","and","with","for","due","to","in","a","an","or","by","on","at","as"}
            d_words = set(d_diag.split()) - stopwords
            p_words = set(p_diag.split()) - stopwords
            if d_words and p_words:
                overlap = len(d_words & p_words) / max(len(d_words), len(p_words))
                if overlap < 0.2:
                    _wf("final_diagnosis",
                        f"Discharge diagnosis ('{discharge.get('final_diagnosis')}') differs significantly "
                        f"from pre-auth provisional diagnosis ('{pre_auth.get('provisional_diagnosis')}'). "
                        "If treatment plan changed substantially, an Enhancement Request is required.")

        # Pre-auth listed surgery but discharge has no procedure code
        surgery_name = (pre_auth.get("surgery_name") or "").strip()
        if surgery_name and not procedure_codes:
            _wf("procedure_codes",
                f"Pre-auth listed surgery '{surgery_name}' but discharge has no procedure code — "
                "ICD-10 PCS/CPT code required for surgical claim settlement.")

        # ── D. PER-CATEGORY FINANCIAL VARIANCE ────────────────────────────

        total_bill     = discharge.get("total_bill_amount") or 0
        total_estimate = pre_auth.get("total_estimated_cost") or 0

        if total_bill > 0 and total_estimate > 0:
            pct = ((total_bill - total_estimate) / total_estimate) * 100
            if pct > 30:
                _cf("total_bill_amount",
                    f"Final bill (₹{total_bill:,.0f}) exceeds pre-auth estimate (₹{total_estimate:,.0f}) "
                    f"by {pct:.1f}% — above 30% triggers mandatory re-authorization. "
                    "Insurer will short-settle to pre-authorized amount without a valid Enhancement Request.")
            elif pct > 10:
                _wf("total_bill_amount",
                    f"Final bill (₹{total_bill:,.0f}) exceeds pre-auth estimate (₹{total_estimate:,.0f}) "
                    f"by {pct:.1f}% — submit an Enhancement Request with clinical justification "
                    "before discharge to avoid proportional deduction across all claim heads.")

        # Room charges vs pre-authorized rate × expected days
        room_bill     = line_items["room_charges"]
        room_rate_pa  = pre_auth.get("room_rent_per_day") or 0
        exp_days      = pre_auth.get("expected_days_in_hospital") or 0
        if room_bill > 0 and room_rate_pa > 0 and exp_days > 0:
            expected_room = room_rate_pa * exp_days
            if room_bill > expected_room * 1.15:
                _wf("room_charges",
                    f"Room charges (₹{room_bill:,.0f}) exceed pre-auth estimate "
                    f"(₹{room_rate_pa:,.0f}/day × {exp_days} days = ₹{expected_room:,.0f}) by >15%. "
                    "If room type upgraded, insurer applies proportional deduction to ALL claim heads "
                    "under the room rent sub-limit clause — this is the most common cause of bulk deductions.")

        # ICU charges
        icu_bill      = line_items["icu_charges"]
        icu_rate_pa   = pre_auth.get("icu_charges_per_day") or 0
        icu_days_pa   = pre_auth.get("days_in_icu") or 0
        if icu_bill > 0 and icu_days_pa == 0 and icu_rate_pa == 0:
            _wf("icu_charges",
                f"ICU charges of ₹{icu_bill:,.0f} billed but ICU stay was not pre-authorized — "
                "TPA will query clinical necessity; attach ICU admission note and intensivist records.")
        elif icu_bill > 0 and icu_rate_pa > 0 and icu_days_pa > 0:
            expected_icu = icu_rate_pa * icu_days_pa
            if icu_bill > expected_icu * 1.2:
                _wf("icu_charges",
                    f"ICU charges (₹{icu_bill:,.0f}) exceed pre-authorized amount "
                    f"(₹{icu_rate_pa:,.0f}/day × {icu_days_pa} days = ₹{expected_icu:,.0f}) by >20%.")

        # Surgery / OT charges
        surg_bill = line_items["surgery_charges"]
        surg_pa   = pre_auth.get("ot_charges") or 0
        if surg_bill > 0 and surg_pa > 0 and surg_bill > surg_pa * 1.25:
            _wf("surgery_charges",
                f"Surgery/OT charges (₹{surg_bill:,.0f}) exceed pre-auth estimate "
                f"(₹{surg_pa:,.0f}) by >25% — insurer may limit reimbursement to "
                "pre-authorized amount. Surgeon fee schedule (CGHS rates) applies.")

        # Medicine / consumables
        med_bill = line_items["medicine_charges"]
        med_pa   = pre_auth.get("medicines_consumables") or 0
        if med_bill > 0 and med_pa > 0 and med_bill > med_pa * 1.3:
            _wf("medicine_charges",
                f"Medicine/consumables (₹{med_bill:,.0f}) exceed pre-auth estimate "
                f"(₹{med_pa:,.0f}) by >30%. Common non-payable items deducted by TPAs: "
                "disposable gloves, syringes, diapers, cotton, bandages. "
                "Ensure these are not included in pharmacy bills.")

        # ── E. POLICY COMPLIANCE ──────────────────────────────────────────

        # RTA without FIR
        if pre_auth.get("is_rta") and not (pre_auth.get("fir_no") or "").strip():
            _cf("fir_no",
                "Case is marked as Road Traffic Accident (RTA) but FIR number is missing — "
                "all insurers mandatorily require FIR copy for RTA claims. "
                "Claim will be outright rejected without it. Also attach MLC certificate.")

        # Substance abuse
        if pre_auth.get("substance_abuse"):
            _cf("substance_abuse",
                "Substance abuse noted in patient history — most standard health policies "
                "exclude claims where injury or illness is directly caused by alcohol or narcotics. "
                "Verify policy exclusion clause; claim may be repudiated.")

        # Pre-existing disease (PED) related to discharge diagnosis
        ped_map = {
            "diabetes":     (["diabet", "dka", "hyperglycaem", "hypoglycaem", "neuropath", "retinopathy", "nephropathy"],
                             "Diabetes"),
            "hypertension": (["hypertens", "htn", "stroke", "cerebrovascular", "cva", "hemorrhagic"],
                             "Hypertension"),
            "heart_disease":(["cardiac", "heart failure", "myocardial", "angina", "coronary", "cad", "ami", "acs",
                               "stemi", "nstemi", "lvf"],
                             "Heart Disease"),
        }
        d_diag_lower = (discharge.get("final_diagnosis") or "").lower()
        for ped_field, (keywords, ped_label) in ped_map.items():
            if pre_auth.get(ped_field) and any(kw in d_diag_lower for kw in keywords):
                _wf(ped_field,
                    f"Discharge diagnosis appears related to pre-existing {ped_label} (declared in pre-auth). "
                    f"Insurer will verify that the policy's PED waiting period (typically 2–4 years) "
                    f"has been completed. Ensure all {ped_label.lower()} history documentation is attached.")

        # Maternity
        if (pre_auth.get("maternity_g") or "").strip():
            maternity_keywords = ["delivery","labour","labor","obstetric","maternity","neonatal",
                                  "cesarean","c-section","lscs","vaginal","puerperal"]
            if any(kw in d_diag_lower for kw in maternity_keywords):
                _wf("maternity",
                    "Maternity claim detected — verify 9-month to 2-year waiting period is completed per policy. "
                    "Required attachments: pre-natal records, G/P/L/A obstetric history, "
                    "delivery type documentation (normal/LSCS), neonatal records if newborn admitted.")

    # ── F. STANDALONE CHECKS (no pre-auth comparison) ─────────────────────

    # High investigation charges relative to total bill (outlier detection)
    inv_bill = line_items["investigation_charges"]
    if stated_total > 0 and inv_bill > 0:
        inv_pct = (inv_bill / stated_total) * 100
        if inv_pct > 40:
            _wf("investigation_charges",
                f"Investigation charges (₹{inv_bill:,.0f}) are {inv_pct:.0f}% of total bill — "
                "unusually high; TPA may audit for inflated diagnostics or duplicate billing. "
                "Ensure each investigation is supported by a doctor's written request.")

    # Other charges as catch-all — if large, flag for itemization
    other_charges = line_items["other_charges"]
    if stated_total > 0 and other_charges > 0:
        other_pct = (other_charges / stated_total) * 100
        if other_pct > 20:
            _wf("other_charges",
                f"'Other charges' (₹{other_charges:,.0f}) represent {other_pct:.0f}% of total bill — "
                "TPAs require itemized breakout of miscellaneous charges; lump-sum 'other' heads "
                "are routinely deducted. Break down into: attendant charges, equipment rental, "
                "prosthetics, blood transfusion, etc.")

    critical_count = sum(1 for f in flags if f["severity"] == "critical")
    warning_count  = sum(1 for f in flags if f["severity"] == "warning")
    logger.info(
        f"Discharge revenue flags: {critical_count} critical, {warning_count} warning"
    )
    return flags
