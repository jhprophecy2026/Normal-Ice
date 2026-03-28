from pydantic import BaseModel
from typing import Optional, List


# ---------------------------------------------------------------------------
# ABHA Registry
# ---------------------------------------------------------------------------

class AbhaPatient(BaseModel):
    abha_id: str
    name: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    age: Optional[int] = None
    contact: Optional[str] = None
    address: Optional[str] = None
    blood_group: Optional[str] = None
    policy_no: Optional[str] = None
    insured_card_id: Optional[str] = None
    employee_id: Optional[str] = None
    insurance_company: Optional[str] = None
    tpa_name: Optional[str] = None
    diabetes: bool = False
    hypertension: bool = False
    heart_disease: bool = False
    other_conditions: Optional[str] = None


# ---------------------------------------------------------------------------
# Pre-Auth Form — mirrors the Medi Assist "Part C (Revised)" form exactly
# ---------------------------------------------------------------------------

class PreAuthRequest(BaseModel):
    abha_id: Optional[str] = None

    # ── Hospital Details (top of form) ──────────────────────────────────────
    hospital_name: Optional[str] = None
    hospital_location: Optional[str] = None
    hospital_email: Optional[str] = None
    hospital_id: Optional[str] = None
    rohini_id: Optional[str] = None

    # ── Section: Patient / Insured Details ─────────────────────────────────
    patient_name: Optional[str] = None
    gender: Optional[str] = None            # Male | Female | Third gender
    contact: Optional[str] = None
    alternate_contact: Optional[str] = None
    age: Optional[int] = None               # years
    age_months: Optional[int] = None        # months component
    date_of_birth: Optional[str] = None
    insured_card_id: Optional[str] = None   # Insurer ID card no.
    policy_no: Optional[str] = None         # Policy number / Name of corporate
    employee_id: Optional[str] = None
    other_insurance: Optional[bool] = None  # currently has other medical insurance?
    other_insurance_insurer: Optional[str] = None
    other_insurance_details: Optional[str] = None
    family_physician_name: Optional[str] = None
    family_physician_contact: Optional[str] = None
    occupation: Optional[str] = None
    patient_address: Optional[str] = None

    # ── Section: Treating Doctor / Hospital ────────────────────────────────
    doctor_name: Optional[str] = None
    doctor_contact: Optional[str] = None

    # Medical
    presenting_complaints: Optional[str] = None
    clinical_findings: Optional[str] = None
    duration_of_illness: Optional[str] = None
    date_of_first_consultation: Optional[str] = None
    past_history: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    icd10_diagnosis_code: Optional[str] = None

    # Treatment type (checkboxes — store as comma-separated or individual bools)
    treatment_medical_management: bool = False
    treatment_surgical: bool = False
    treatment_intensive_care: bool = False
    treatment_investigation: bool = False
    treatment_non_allopathic: bool = False

    # Medical/investigation management
    medical_management_details: Optional[str] = None
    route_of_drug_administration: Optional[str] = None  # IV | Oral | Other

    # Surgical
    surgery_name: Optional[str] = None
    icd10_pcs_code: Optional[str] = None

    # Other treatment
    other_treatment_details: Optional[str] = None

    # Injury
    injury_details: Optional[str] = None    # how did injury occur

    # Accident details
    is_rta: Optional[bool] = None
    date_of_injury: Optional[str] = None
    reported_to_police: Optional[bool] = None
    fir_no: Optional[str] = None
    substance_abuse: Optional[bool] = None
    substance_abuse_test_done: Optional[bool] = None

    # Maternity
    maternity_g: Optional[str] = None
    maternity_p: Optional[str] = None
    maternity_l: Optional[str] = None
    maternity_a: Optional[str] = None
    expected_delivery_date: Optional[str] = None

    # ── Section: Admission Details ─────────────────────────────────────────
    admission_date: Optional[str] = None
    admission_time: Optional[str] = None
    admission_type: Optional[str] = None    # Emergency | Planned
    expected_days_in_hospital: Optional[int] = None
    days_in_icu: Optional[int] = None
    room_type: Optional[str] = None

    # ── Section: Estimated Cost ────────────────────────────────────────────
    room_rent_per_day: Optional[float] = None
    investigation_diagnostics_cost: Optional[float] = None
    icu_charges_per_day: Optional[float] = None
    ot_charges: Optional[float] = None
    professional_fees: Optional[float] = None   # surgeon + anaesthetist + consultation
    medicines_consumables: Optional[float] = None
    other_hospital_expenses: Optional[float] = None
    package_charges: Optional[float] = None
    total_estimated_cost: Optional[float] = None

    # ── Section: Past Medical History (chronic illness with since dates) ────
    diabetes: bool = False
    diabetes_since: Optional[str] = None
    heart_disease: bool = False
    heart_disease_since: Optional[str] = None
    hypertension: bool = False
    hypertension_since: Optional[str] = None
    hyperlipidemias: bool = False
    hyperlipidemias_since: Optional[str] = None
    osteoarthritis: bool = False
    osteoarthritis_since: Optional[str] = None
    asthma_copd: bool = False
    asthma_copd_since: Optional[str] = None
    cancer: bool = False
    cancer_since: Optional[str] = None
    alcohol_drug_abuse: bool = False
    alcohol_drug_abuse_since: Optional[str] = None
    hiv_std: bool = False
    hiv_std_since: Optional[str] = None
    other_conditions: Optional[str] = None     # "any other ailment give details"

    # ── Declaration ────────────────────────────────────────────────────────
    doctor_qualification: Optional[str] = None
    doctor_registration_no: Optional[str] = None
    patient_email: Optional[str] = None


class PreAuthResponse(PreAuthRequest):
    id: str
    bill_no: Optional[str] = None
    patient_id: Optional[str] = None   # links to patients table
    status: str = "draft"
    missing_required_fields: List[str] = []
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Gemini medical extraction result
# ---------------------------------------------------------------------------

class MedicalExtract(BaseModel):
    # Hospital
    hospital_name: Optional[str] = None
    hospital_location: Optional[str] = None
    hospital_email: Optional[str] = None
    hospital_id: Optional[str] = None
    rohini_id: Optional[str] = None

    # Doctor
    doctor_name: Optional[str] = None
    doctor_contact: Optional[str] = None
    doctor_qualification: Optional[str] = None
    doctor_registration_no: Optional[str] = None

    # Medical history & complaints
    presenting_complaints: Optional[str] = None
    duration_of_illness: Optional[str] = None
    date_of_first_consultation: Optional[str] = None
    provisional_diagnosis: Optional[str] = None
    icd10_diagnosis_code: Optional[str] = None
    clinical_findings: Optional[str] = None
    past_history: Optional[str] = None

    # Treatment
    line_of_treatment: Optional[str] = None
    treatment_medical_management: Optional[bool] = None
    treatment_surgical: Optional[bool] = None
    treatment_intensive_care: Optional[bool] = None
    treatment_investigation: Optional[bool] = None
    medical_management_details: Optional[str] = None
    route_of_drug_administration: Optional[str] = None
    surgery_name: Optional[str] = None
    icd10_pcs_code: Optional[str] = None

    # Admission
    admission_date: Optional[str] = None
    admission_time: Optional[str] = None
    admission_type: Optional[str] = None        # Emergency | Planned
    expected_days_in_hospital: Optional[int] = None
    days_in_icu: Optional[int] = None
    room_type: Optional[str] = None             # single | twin-sharing | general

    # Estimated costs (INR — extract only if explicitly printed in the document)
    room_rent_per_day: Optional[float] = None
    icu_charges_per_day: Optional[float] = None
    ot_charges: Optional[float] = None
    professional_fees: Optional[float] = None
    medicines_consumables: Optional[float] = None
    investigation_diagnostics_cost: Optional[float] = None
    other_hospital_expenses: Optional[float] = None
    total_estimated_cost: Optional[float] = None

    # Past medical history with since-dates
    diabetes: Optional[bool] = None
    diabetes_since: Optional[str] = None
    hypertension: Optional[bool] = None
    hypertension_since: Optional[str] = None
    heart_disease: Optional[bool] = None
    heart_disease_since: Optional[str] = None
    hyperlipidemias: Optional[bool] = None
    osteoarthritis: Optional[bool] = None
    asthma_copd: Optional[bool] = None
    cancer: Optional[bool] = None
    alcohol_drug_abuse: Optional[bool] = None
    hiv_std: Optional[bool] = None
    other_conditions: Optional[str] = None

    # Injury / RTA
    is_rta: Optional[bool] = None
    date_of_injury: Optional[str] = None
    reported_to_police: Optional[bool] = None
    fir_no: Optional[str] = None
    substance_abuse: Optional[bool] = None

    # Maternity
    maternity_g: Optional[str] = None
    maternity_p: Optional[str] = None
    maternity_l: Optional[str] = None
    maternity_a: Optional[str] = None
    expected_delivery_date: Optional[str] = None


# ---------------------------------------------------------------------------
# Required fields
# ---------------------------------------------------------------------------

REQUIRED_FIELDS: List[str] = [
    "patient_name",
    "date_of_birth",
    "contact",
    "policy_no",
    "hospital_name",
    "rohini_id",
    "doctor_name",
    "presenting_complaints",
    "provisional_diagnosis",
    "icd10_diagnosis_code",
    "admission_date",
    "admission_type",
    "total_estimated_cost",
]


def get_missing_required(data: PreAuthRequest) -> List[str]:
    missing = []
    for field in REQUIRED_FIELDS:
        val = getattr(data, field, None)
        if val is None or (isinstance(val, str) and not val.strip()):
            missing.append(field)
    return missing
