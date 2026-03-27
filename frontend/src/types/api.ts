export interface ProcessResponse {
  success: boolean;
  message: string;
  extracted_text?: string;
  fhir_bundle?: any;
  document_type?: string;
  error?: string;
}

export interface HealthResponse {
  status: string;
  message: string;
  gemini_configured: boolean;
}
