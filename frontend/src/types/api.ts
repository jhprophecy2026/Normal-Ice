// ---------------------------------------------------------------------------
// Upload / process response
// ---------------------------------------------------------------------------
export interface BillingFlag {
  field: string;
  severity: 'critical' | 'warning';
  message: string;
}

export interface ProcessResponse {
  success: boolean;
  message: string;
  extracted_text?: string;
  fhir_bundle?: any;
  document_type?: string;
  billing_flags?: BillingFlag[];
  patient_id?: string;
  patient_action?: string; // "created" | "updated"
  error?: string;
}

export interface HealthResponse {
  status: string;
  message: string;
  gemini_configured: boolean;
}

// ---------------------------------------------------------------------------
// Patient store models
// ---------------------------------------------------------------------------
export interface PatientSummary {
  patient_id: string;
  name?: string;
  abha_id?: string;
  document_count: number;
  last_updated: string;
}

export interface DocumentRecord {
  filename: string;
  upload_date: string;
  document_type: string;
  extracted_text_preview?: string;
  bill_no?: string;   // episode identifier — present when uploaded via pre-auth/discharge flow
}

export interface StoredPatientRecord {
  patient_id: string;
  abha_id?: string;
  name?: string;
  age?: number;
  gender?: string;
  date_of_birth?: string;
  contact?: string;
  practitioner_name?: string;
  practitioner_id?: string;
  organization_name?: string;
  observations: any[];
  medications: any[];
  diagnoses: string[];
  fhir_bundles: any[];
  documents: DocumentRecord[];
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Billing flags / claim readiness
// ---------------------------------------------------------------------------
export interface StoredBillingFlag {
  id?: string;
  patient_id: string;
  field: string;
  severity: 'critical' | 'warning';
  message: string;
  resolved: boolean;
  created_at?: string;
  resolved_at?: string;
}

export interface FlagsResponse {
  success: boolean;
  patient_id: string;
  claim_ready: boolean;
  critical_count: number;
  warning_count: number;
  flags: StoredBillingFlag[];
}

// ---------------------------------------------------------------------------
// Pre-Authorization
// ---------------------------------------------------------------------------
export interface AbhaPatient {
  abha_id: string;
  name?: string;
  date_of_birth?: string;
  gender?: string;
  age?: number;
  contact?: string;
  address?: string;
  blood_group?: string;
  policy_no?: string;
  insured_card_id?: string;
  employee_id?: string;
  insurance_company?: string;
  tpa_name?: string;
  diabetes: boolean;
  hypertension: boolean;
  heart_disease: boolean;
  other_conditions?: string;
}

export interface PreAuthData {
  abha_id?: string;
  // Hospital
  hospital_name?: string;
  hospital_location?: string;
  hospital_email?: string;
  hospital_id?: string;
  rohini_id?: string;
  // Patient
  patient_name?: string;
  gender?: string;
  contact?: string;
  alternate_contact?: string;
  age?: number;
  age_months?: number;
  date_of_birth?: string;
  insured_card_id?: string;
  policy_no?: string;
  employee_id?: string;
  other_insurance?: boolean;
  other_insurance_insurer?: string;
  other_insurance_details?: string;
  family_physician_name?: string;
  family_physician_contact?: string;
  occupation?: string;
  patient_address?: string;
  // Doctor
  doctor_name?: string;
  doctor_contact?: string;
  // Medical
  presenting_complaints?: string;
  clinical_findings?: string;
  duration_of_illness?: string;
  date_of_first_consultation?: string;
  past_history?: string;
  provisional_diagnosis?: string;
  icd10_diagnosis_code?: string;
  // Treatment type
  treatment_medical_management?: boolean;
  treatment_surgical?: boolean;
  treatment_intensive_care?: boolean;
  treatment_investigation?: boolean;
  treatment_non_allopathic?: boolean;
  medical_management_details?: string;
  route_of_drug_administration?: string;
  surgery_name?: string;
  icd10_pcs_code?: string;
  other_treatment_details?: string;
  injury_details?: string;
  // Accident
  is_rta?: boolean;
  date_of_injury?: string;
  reported_to_police?: boolean;
  fir_no?: string;
  substance_abuse?: boolean;
  substance_abuse_test_done?: boolean;
  // Maternity
  maternity_g?: string;
  maternity_p?: string;
  maternity_l?: string;
  maternity_a?: string;
  expected_delivery_date?: string;
  // Admission
  admission_date?: string;
  admission_time?: string;
  admission_type?: string;
  expected_days_in_hospital?: number;
  days_in_icu?: number;
  room_type?: string;
  // Costs
  room_rent_per_day?: number;
  investigation_diagnostics_cost?: number;
  icu_charges_per_day?: number;
  ot_charges?: number;
  professional_fees?: number;
  medicines_consumables?: number;
  other_hospital_expenses?: number;
  package_charges?: number;
  total_estimated_cost?: number;
  // Past history
  diabetes?: boolean;
  diabetes_since?: string;
  heart_disease?: boolean;
  heart_disease_since?: string;
  hypertension?: boolean;
  hypertension_since?: string;
  hyperlipidemias?: boolean;
  hyperlipidemias_since?: string;
  osteoarthritis?: boolean;
  osteoarthritis_since?: string;
  asthma_copd?: boolean;
  asthma_copd_since?: string;
  cancer?: boolean;
  cancer_since?: string;
  alcohol_drug_abuse?: boolean;
  alcohol_drug_abuse_since?: string;
  hiv_std?: boolean;
  hiv_std_since?: string;
  other_conditions?: string;
  // Declaration
  doctor_qualification?: string;
  doctor_registration_no?: string;
  patient_email?: string;
}

export interface PreAuthResponse extends PreAuthData {
  id: string;
  bill_no?: string;
  patient_id?: string;   // links to patients table once a doc is uploaded
  status: string;
  missing_required_fields: string[];
  created_at?: string;
  updated_at?: string;
}

// ---------------------------------------------------------------------------
// Enhancement Requests
// ---------------------------------------------------------------------------
export interface EnhancementExtract {
  reason?: string;
  clinical_justification?: string;
  updated_diagnosis?: string;
  updated_icd10_code?: string;
  updated_line_of_treatment?: string;
  updated_surgery_name?: string;
  updated_icd10_pcs_code?: string;
  revised_room_rent_per_day?: number;
  revised_icu_charges_per_day?: number;
  revised_ot_charges?: number;
  revised_surgeon_fees?: number;
  revised_medicines_consumables?: number;
  revised_investigations?: number;
  revised_total_estimated_cost?: number;
}

export interface EnhancementData {
  pre_auth_id: string;
  abha_id?: string;
  reason: string;
  clinical_justification?: string;
  updated_diagnosis?: string;
  updated_icd10_code?: string;
  updated_line_of_treatment?: string;
  updated_surgery_name?: string;
  updated_icd10_pcs_code?: string;
  revised_room_rent_per_day?: number;
  revised_icu_charges_per_day?: number;
  revised_ot_charges?: number;
  revised_surgeon_fees?: number;
  revised_medicines_consumables?: number;
  revised_investigations?: number;
  revised_total_estimated_cost?: number;
}

export interface EnhancementResponse extends EnhancementData {
  id: string;
  sequence_no: number;
  status: string;
  tpa_remarks?: string;
  original_diagnosis?: string;
  original_icd10_code?: string;
  original_total_cost?: number;
  created_at?: string;
  updated_at?: string;
}

export interface PatientCaseHistory {
  pre_auth_id: string;
  patient_name?: string;
  abha_id?: string;
  provisional_diagnosis?: string;
  icd10_diagnosis_code?: string;
  admission_date?: string;
  admission_type?: string;
  hospital_name?: string;
  total_estimated_cost?: number;
  status: string;
  created_at?: string;
  enhancements: EnhancementResponse[];
}

export interface MedicalExtract {
  // Hospital
  hospital_name?: string;
  hospital_location?: string;
  hospital_email?: string;
  hospital_id?: string;
  rohini_id?: string;
  // Doctor
  doctor_name?: string;
  doctor_contact?: string;
  doctor_qualification?: string;
  doctor_registration_no?: string;
  // Medical
  presenting_complaints?: string;
  duration_of_illness?: string;
  date_of_first_consultation?: string;
  provisional_diagnosis?: string;
  icd10_diagnosis_code?: string;
  clinical_findings?: string;
  past_history?: string;
  // Treatment
  line_of_treatment?: string;
  treatment_medical_management?: boolean;
  treatment_surgical?: boolean;
  treatment_intensive_care?: boolean;
  treatment_investigation?: boolean;
  medical_management_details?: string;
  route_of_drug_administration?: string;
  surgery_name?: string;
  icd10_pcs_code?: string;
  // Admission
  admission_date?: string;
  admission_time?: string;
  admission_type?: string;
  expected_days_in_hospital?: number;
  days_in_icu?: number;
  room_type?: string;
  // Costs
  room_rent_per_day?: number;
  icu_charges_per_day?: number;
  ot_charges?: number;
  professional_fees?: number;
  medicines_consumables?: number;
  investigation_diagnostics_cost?: number;
  other_hospital_expenses?: number;
  total_estimated_cost?: number;
  // Past history
  diabetes?: boolean;
  diabetes_since?: string;
  hypertension?: boolean;
  hypertension_since?: string;
  heart_disease?: boolean;
  heart_disease_since?: string;
  hyperlipidemias?: boolean;
  osteoarthritis?: boolean;
  asthma_copd?: boolean;
  cancer?: boolean;
  alcohol_drug_abuse?: boolean;
  hiv_std?: boolean;
  other_conditions?: string;
  // Injury / RTA
  is_rta?: boolean;
  date_of_injury?: string;
  reported_to_police?: boolean;
  fir_no?: string;
  substance_abuse?: boolean;
  // Maternity
  maternity_g?: string;
  maternity_p?: string;
  maternity_l?: string;
  maternity_a?: string;
  expected_delivery_date?: string;
}

// ---------------------------------------------------------------------------
// Discharge
// ---------------------------------------------------------------------------
export interface DischargeData {
  bill_no: string;
  pre_auth_id?: string;
  abha_id?: string;
  discharge_date?: string;
  final_diagnosis?: string;
  final_icd10_codes?: string;
  procedure_codes?: string;
  discharge_summary_text?: string;
  room_charges?: number;
  icu_charges?: number;
  surgery_charges?: number;
  medicine_charges?: number;
  investigation_charges?: number;
  other_charges?: number;
  total_bill_amount?: number;
  status?: string;
}

export interface DischargeResponse extends DischargeData {
  id: string;
  revenue_flags: Array<{ field: string; severity: 'critical' | 'warning'; message: string }>;
  created_at?: string;
  updated_at?: string;
}

export interface DischargeExtract {
  discharge_date?: string;
  final_diagnosis?: string;
  final_icd10_codes?: string;
  procedure_codes?: string;
  room_charges?: number;
  icu_charges?: number;
  surgery_charges?: number;
  medicine_charges?: number;
  investigation_charges?: number;
  other_charges?: number;
  total_bill_amount?: number;
}

// ---------------------------------------------------------------------------
// Settlement
// ---------------------------------------------------------------------------
export interface SettlementData {
  bill_no: string;
  pre_auth_id?: string;
  discharge_id?: string;
  abha_id?: string;
  pre_auth_approved_amount?: number;
  claimed_amount?: number;
  deduction_amount?: number;
  deduction_reason?: string;
  final_settlement_amount?: number;
  status?: string;
  tpa_remarks?: string;
  settlement_date?: string;
}

export interface SettlementResponse extends SettlementData {
  id: string;
  created_at?: string;
  updated_at?: string;
}

// ---------------------------------------------------------------------------
// Cases
// ---------------------------------------------------------------------------
export interface CaseSummary {
  bill_no: string;
  pre_auth_id: string;
  patient_id?: string;   // links to patients table
  patient_name?: string;
  abha_id?: string;
  hospital_name?: string;
  pre_auth_status?: string;
  total_estimated_cost?: number;
  has_enhancement: boolean;
  has_discharge: boolean;
  has_settlement: boolean;
  created_at?: string;
}

export interface CaseDetail {
  bill_no: string;
  pre_auth: PreAuthResponse | null;
  enhancements: EnhancementResponse[];
  discharge: DischargeResponse | null;
  settlement: SettlementResponse | null;
}

// ---------------------------------------------------------------------------
// Financial Audit
// ---------------------------------------------------------------------------
export interface FinancialAuditClaim {
  year: number;
  event: string;
  admission_date: string;
  discharge_date: string;
  claimed_amount: number;
  settled_amount: number;
  deduction_amount: number;
  deduction_reason: string;
  tpa: string;
  status: string;
}

export interface FinancialAuditBenchmark {
  category: string;
  typical_range: string;
  basis: string;
  patient_note: string;
}

export interface FinancialAuditRiskFactor {
  factor: string;
  impact: string;
  detail: string;
}

export interface FinancialAuditInsurance {
  company: string;
  tpa: string;
  policy_no: string;
  sum_insured: number;
  utilized_ytd: number;
  available: number;
  room_eligibility: string;
  cashless_network: string;
  key_exclusions: string[];
}

export interface FinancialAudit {
  abha_id: string;
  patient_name: string;
  generated_date: string;
  risk_tier: 'Low' | 'Moderate' | 'High' | 'Critical';
  risk_color: 'green' | 'amber' | 'red';
  summary: string;
  past_claims: FinancialAuditClaim[];
  cost_benchmarks: FinancialAuditBenchmark[];
  risk_factors: FinancialAuditRiskFactor[];
  insurance: FinancialAuditInsurance;
  tpa_watch_points: string[];
  recommendations: string[];
}
