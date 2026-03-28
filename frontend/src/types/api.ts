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
