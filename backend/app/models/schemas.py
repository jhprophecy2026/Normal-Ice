from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal

class ProcessResponse(BaseModel):
    """Response model for PDF processing"""
    success: bool
    message: str
    extracted_text: Optional[str] = None
    fhir_bundle: Optional[Dict[str, Any]] = None
    document_type: Optional[str] = None
    error: Optional[str] = None

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    message: str
    gemini_configured: bool

class PatientInfo(BaseModel):
    """Extracted patient information"""
    name: Optional[str] = None
    age: Optional[int] = None
    gender: Optional[str] = None
    patient_id: Optional[str] = None
    date_of_birth: Optional[str] = None
    contact: Optional[str] = None

class PractitionerInfo(BaseModel):
    """Extracted practitioner information"""
    name: Optional[str] = None
    specialty: Optional[str] = None
    practitioner_id: Optional[str] = None
    contact: Optional[str] = None

class LabObservation(BaseModel):
    """Lab test observation"""
    test_name: str
    value: Optional[str] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    status: Optional[str] = "final"
    interpretation: Optional[str] = None

class MedicationInfo(BaseModel):
    """Prescription medication"""
    medication_name: str
    dosage: Optional[str] = None
    frequency: Optional[str] = None
    duration: Optional[str] = None
    route: Optional[str] = None
    instructions: Optional[str] = None

class LabReportData(BaseModel):
    """Structured lab report data"""
    document_type: Literal["lab_report"] = "lab_report"
    report_date: Optional[str] = None
    patient: Optional[PatientInfo] = None
    practitioner: Optional[PractitionerInfo] = None
    organization_name: Optional[str] = None
    observations: List[LabObservation] = []
    diagnosis: Optional[str] = None
    notes: Optional[str] = None

class PrescriptionData(BaseModel):
    """Structured prescription data"""
    document_type: Literal["prescription"] = "prescription"
    prescription_date: Optional[str] = None
    patient: Optional[PatientInfo] = None
    practitioner: Optional[PractitionerInfo] = None
    organization_name: Optional[str] = None
    medications: List[MedicationInfo] = []
    diagnosis: Optional[str] = None
    notes: Optional[str] = None
