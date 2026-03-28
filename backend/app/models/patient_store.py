from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class DocumentRecord(BaseModel):
    """Metadata for a single uploaded document."""
    filename: str
    upload_date: str
    document_type: str  # "lab_report" or "prescription"
    extracted_text_preview: Optional[str] = None
    bill_no: Optional[str] = None  # episode identifier — links document to a cashless case


class StoredPatientRecord(BaseModel):
    """Master patient record persisted to local JSON storage."""
    patient_id: str
    abha_id: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    date_of_birth: Optional[str] = None
    contact: Optional[str] = None

    # Clinical context
    practitioner_name: Optional[str] = None
    practitioner_id: Optional[str] = None
    organization_name: Optional[str] = None

    # Accumulated clinical data
    observations: List[Dict[str, Any]] = []
    medications: List[Dict[str, Any]] = []
    diagnoses: List[str] = []

    # All generated FHIR bundles
    fhir_bundles: List[Dict[str, Any]] = []

    # Upload history
    documents: List[DocumentRecord] = []

    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class PatientSummary(BaseModel):
    """Lightweight model for the patient list / index."""
    patient_id: str
    name: Optional[str] = None
    abha_id: Optional[str] = None
    document_count: int = 0
    last_updated: str = ""


class ClaimCheck(BaseModel):
    """Single check within a claim-readiness analysis."""
    name: str
    passed: bool
    detail: str
    points: float = 0.0
    max_points: float = 0.0


class ClaimReadinessResult(BaseModel):
    """Output of the claim-readiness analyzer."""
    patient_id: str
    patient_name: Optional[str] = None
    is_ready: bool
    readiness_score: float  # 0-100
    checks: List[ClaimCheck] = []
    missing_fields: List[str] = []
    recommendations: List[str] = []
