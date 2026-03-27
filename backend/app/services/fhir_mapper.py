from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner
from fhir.resources.organization import Organization
from fhir.resources.observation import Observation
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.medication import Medication
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.condition import Condition
from fhir.resources.humanname import HumanName
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.quantity import Quantity
from fhir.resources.dosage import Dosage

from app.models.schemas import LabReportData, PrescriptionData, PatientInfo, PractitionerInfo
from typing import Union, List, Optional
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

class FHIRBundleGenerator:
    """Generate FHIR R4 bundles from structured clinical data"""
    
    @staticmethod
    def _generate_id() -> str:
        """Generate a unique ID"""
        return str(uuid.uuid4())
    
    @staticmethod
    def _create_patient_resource(patient_info: Optional[PatientInfo]) -> Optional[Patient]:
        """Create FHIR Patient resource"""
        if not patient_info:
            return None
        
        try:
            patient = Patient(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Patient"
            )
            
            # Name
            if patient_info.name:
                patient.name = [HumanName(text=patient_info.name)]
            
            # Gender
            if patient_info.gender:
                gender_map = {
                    "male": "male", "m": "male", "man": "male",
                    "female": "female", "f": "female", "woman": "female",
                    "other": "other", "unknown": "unknown"
                }
                gender_lower = patient_info.gender.lower()
                patient.gender = gender_map.get(gender_lower, "unknown")
            
            # Birth date
            if patient_info.date_of_birth:
                patient.birthDate = patient_info.date_of_birth
            
            # Patient ID as identifier
            if patient_info.patient_id:
                from fhir.resources.identifier import Identifier
                patient.identifier = [Identifier(value=patient_info.patient_id, system="hospital-patient-id")]
            
            return patient
        except Exception as e:
            logger.error(f"Error creating Patient resource: {e}")
            return None
    
    @staticmethod
    def _create_practitioner_resource(practitioner_info: Optional[PractitionerInfo]) -> Optional[Practitioner]:
        """Create FHIR Practitioner resource"""
        if not practitioner_info or not practitioner_info.name:
            return None
        
        try:
            practitioner = Practitioner(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Practitioner"
            )
            
            practitioner.name = [HumanName(text=practitioner_info.name)]
            
            if practitioner_info.practitioner_id:
                from fhir.resources.identifier import Identifier
                practitioner.identifier = [Identifier(value=practitioner_info.practitioner_id)]
            
            return practitioner
        except Exception as e:
            logger.error(f"Error creating Practitioner resource: {e}")
            return None
    
    @staticmethod
    def _create_organization_resource(org_name: Optional[str]) -> Optional[Organization]:
        """Create FHIR Organization resource"""
        if not org_name:
            return None
        
        try:
            organization = Organization(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Organization",
                name=org_name
            )
            return organization
        except Exception as e:
            logger.error(f"Error creating Organization resource: {e}")
            return None
    
    @staticmethod
    def _create_observation_resource(
        obs_data,
        patient_ref: Optional[str] = None,
        report_date: Optional[str] = None
    ) -> Optional[Observation]:
        """Create FHIR Observation resource for lab results"""
        try:
            observation = Observation(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Observation",
                status=obs_data.status or "final",
                code=CodeableConcept(
                    text=obs_data.test_name
                )
            )
            
            # Patient reference
            if patient_ref:
                observation.subject = Reference(reference=patient_ref)
            
            # Effective date
            if report_date:
                observation.effectiveDateTime = report_date
            
            # Value
            if obs_data.value:
                # Try to create a Quantity if unit is available
                if obs_data.unit:
                    try:
                        # Try to convert value to float
                        numeric_value = float(obs_data.value)
                        observation.valueQuantity = Quantity(
                            value=numeric_value,
                            unit=obs_data.unit
                        )
                    except (ValueError, TypeError):
                        # If not numeric, use string
                        observation.valueString = obs_data.value
                else:
                    observation.valueString = obs_data.value
            
            # Reference range
            if obs_data.reference_range:
                from fhir.resources.observationreferencerange import ObservationReferenceRange
                observation.referenceRange = [
                    ObservationReferenceRange(text=obs_data.reference_range)
                ]
            
            # Interpretation
            if obs_data.interpretation:
                observation.interpretation = [
                    CodeableConcept(text=obs_data.interpretation)
                ]
            
            return observation
        except Exception as e:
            logger.error(f"Error creating Observation resource: {e}")
            return None
    
    @staticmethod
    def _create_diagnostic_report_resource(
        observations: List[Observation],
        patient_ref: Optional[str] = None,
        practitioner_ref: Optional[str] = None,
        report_date: Optional[str] = None
    ) -> Optional[DiagnosticReport]:
        """Create FHIR DiagnosticReport resource"""
        if not observations:
            return None
        
        try:
            report = DiagnosticReport(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="DiagnosticReport",
                status="final",
                code=CodeableConcept(text="Laboratory Report")
            )
            
            if patient_ref:
                report.subject = Reference(reference=patient_ref)
            
            if practitioner_ref:
                report.performer = [Reference(reference=practitioner_ref)]
            
            if report_date:
                report.effectiveDateTime = report_date
            
            # Add observation references
            report.result = [
                Reference(reference=f"Observation/{obs.id}")
                for obs in observations if obs and obs.id
            ]
            
            return report
        except Exception as e:
            logger.error(f"Error creating DiagnosticReport resource: {e}")
            return None
    
    @staticmethod
    def _create_medication_resource(medication_name: str) -> Optional[Medication]:
        """Create FHIR Medication resource"""
        try:
            medication = Medication(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Medication",
                code=CodeableConcept(text=medication_name)
            )
            return medication
        except Exception as e:
            logger.error(f"Error creating Medication resource: {e}")
            return None
    
    @staticmethod
    def _create_medication_request_resource(
        med_data,
        patient_ref: Optional[str] = None,
        practitioner_ref: Optional[str] = None,
        medication_ref: Optional[str] = None,
        prescription_date: Optional[str] = None
    ) -> Optional[MedicationRequest]:
        """Create FHIR MedicationRequest resource"""
        try:
            med_request = MedicationRequest(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="MedicationRequest",
                status="active",
                intent="order"
            )
            
            # Medication reference or CodeableConcept
            if medication_ref:
                med_request.medicationReference = Reference(reference=medication_ref)
            else:
                med_request.medicationCodeableConcept = CodeableConcept(
                    text=med_data.medication_name
                )
            
            # Patient reference
            if patient_ref:
                med_request.subject = Reference(reference=patient_ref)
            
            # Prescriber reference
            if practitioner_ref:
                med_request.requester = Reference(reference=practitioner_ref)
            
            # Authored date
            if prescription_date:
                med_request.authoredOn = prescription_date
            
            # Dosage instructions
            dosage_text_parts = []
            if med_data.dosage:
                dosage_text_parts.append(med_data.dosage)
            if med_data.frequency:
                dosage_text_parts.append(med_data.frequency)
            if med_data.duration:
                dosage_text_parts.append(f"for {med_data.duration}")
            
            if dosage_text_parts:
                med_request.dosageInstruction = [
                    Dosage(text=" ".join(dosage_text_parts))
                ]
            
            return med_request
        except Exception as e:
            logger.error(f"Error creating MedicationRequest resource: {e}")
            return None
    
    @staticmethod
    def _create_condition_resource(
        diagnosis: str,
        patient_ref: Optional[str] = None
    ) -> Optional[Condition]:
        """Create FHIR Condition resource for diagnosis"""
        try:
            condition = Condition(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Condition",
                code=CodeableConcept(text=diagnosis)
            )
            
            if patient_ref:
                condition.subject = Reference(reference=patient_ref)
            
            return condition
        except Exception as e:
            logger.error(f"Error creating Condition resource: {e}")
            return None
    
    @classmethod
    def generate_lab_report_bundle(cls, data: LabReportData) -> Bundle:
        """Generate FHIR Bundle from lab report data"""
        bundle = Bundle(
            id=cls._generate_id(),
            resourceType="Bundle",
            type="collection",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        entries = []
        
        # Create Patient
        patient = cls._create_patient_resource(data.patient)
        if patient:
            entries.append(BundleEntry(resource=patient))
            patient_ref = f"Patient/{patient.id}"
        else:
            patient_ref = None
        
        # Create Practitioner
        practitioner = cls._create_practitioner_resource(data.practitioner)
        if practitioner:
            entries.append(BundleEntry(resource=practitioner))
            practitioner_ref = f"Practitioner/{practitioner.id}"
        else:
            practitioner_ref = None
        
        # Create Organization
        organization = cls._create_organization_resource(data.organization_name)
        if organization:
            entries.append(BundleEntry(resource=organization))
        
        # Create Observations
        observations = []
        for obs_data in data.observations:
            obs = cls._create_observation_resource(obs_data, patient_ref, data.report_date)
            if obs:
                observations.append(obs)
                entries.append(BundleEntry(resource=obs))
        
        # Create DiagnosticReport
        if observations:
            diagnostic_report = cls._create_diagnostic_report_resource(
                observations, patient_ref, practitioner_ref, data.report_date
            )
            if diagnostic_report:
                entries.append(BundleEntry(resource=diagnostic_report))
        
        # Create Condition for diagnosis
        if data.diagnosis:
            condition = cls._create_condition_resource(data.diagnosis, patient_ref)
            if condition:
                entries.append(BundleEntry(resource=condition))
        
        bundle.entry = entries
        return bundle
    
    @classmethod
    def generate_prescription_bundle(cls, data: PrescriptionData) -> Bundle:
        """Generate FHIR Bundle from prescription data"""
        bundle = Bundle(
            id=cls._generate_id(),
            resourceType="Bundle",
            type="collection",
            timestamp=datetime.utcnow().isoformat() + "Z"
        )
        
        entries = []
        
        # Create Patient
        patient = cls._create_patient_resource(data.patient)
        if patient:
            entries.append(BundleEntry(resource=patient))
            patient_ref = f"Patient/{patient.id}"
        else:
            patient_ref = None
        
        # Create Practitioner
        practitioner = cls._create_practitioner_resource(data.practitioner)
        if practitioner:
            entries.append(BundleEntry(resource=practitioner))
            practitioner_ref = f"Practitioner/{practitioner.id}"
        else:
            practitioner_ref = None
        
        # Create Organization
        organization = cls._create_organization_resource(data.organization_name)
        if organization:
            entries.append(BundleEntry(resource=organization))
        
        # Create Medications and MedicationRequests
        for med_data in data.medications:
            medication = cls._create_medication_resource(med_data.medication_name)
            if medication:
                entries.append(BundleEntry(resource=medication))
                medication_ref = f"Medication/{medication.id}"
            else:
                medication_ref = None
            
            med_request = cls._create_medication_request_resource(
                med_data, patient_ref, practitioner_ref, medication_ref, data.prescription_date
            )
            if med_request:
                entries.append(BundleEntry(resource=med_request))
        
        # Create Condition for diagnosis
        if data.diagnosis:
            condition = cls._create_condition_resource(data.diagnosis, patient_ref)
            if condition:
                entries.append(BundleEntry(resource=condition))
        
        bundle.entry = entries
        return bundle

async def generate_fhir_bundle(data: Union[LabReportData, PrescriptionData]) -> dict:
    """
    Generate FHIR R4 Bundle from structured clinical data.
    
    Args:
        data: Structured lab report or prescription data
        
    Returns:
        FHIR Bundle as dictionary
    """
    try:
        generator = FHIRBundleGenerator()
        
        if isinstance(data, LabReportData):
            bundle = generator.generate_lab_report_bundle(data)
        elif isinstance(data, PrescriptionData):
            bundle = generator.generate_prescription_bundle(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")
        
        # Convert to dict
        bundle_dict = bundle.dict(exclude_none=True)
        logger.info(f"Generated FHIR bundle with {len(bundle.entry)} resources")
        return bundle_dict
        
    except Exception as e:
        logger.error(f"FHIR bundle generation error: {e}")
        raise ValueError(f"Failed to generate FHIR bundle: {str(e)}")


def merge_fhir_bundles(bundles: List[dict]) -> dict:
    """
    Merge multiple FHIR bundles into a single bundle.
    
    Args:
        bundles: List of FHIR bundle dictionaries
        
    Returns:
        Single merged FHIR bundle dictionary
    """
    if not bundles:
        raise ValueError("No bundles to merge")
    
    if len(bundles) == 1:
        return bundles[0]
    
    # Create a new merged bundle
    merged_bundle = {
        "resourceType": "Bundle",
        "id": FHIRBundleGenerator._generate_id(),
        "type": "collection",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": []
    }
    
    # Collect all entries from all bundles
    all_entries = []
    for bundle in bundles:
        if "entry" in bundle and bundle["entry"]:
            all_entries.extend(bundle["entry"])
    
    # Deduplicate resources by type and key identifiers
    # Keep patient, practitioner, organization unique
    seen_resources = {}
    unique_entries = []
    
    for entry in all_entries:
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")
        
        # For Patient, Practitioner, Organization - keep only first occurrence
        if resource_type in ["Patient", "Practitioner", "Organization"]:
            if resource_type not in seen_resources:
                seen_resources[resource_type] = True
                unique_entries.append(entry)
        else:
            # For Observation, Medication, etc - keep all
            unique_entries.append(entry)
    
    merged_bundle["entry"] = unique_entries
    
    logger.info(f"Merged {len(bundles)} bundles into one with {len(unique_entries)} total resources")
    return merged_bundle


async def generate_fhir_bundles_batch(
    data_list: List[Union[LabReportData, PrescriptionData]]
) -> List[dict]:
    """
    Generate FHIR bundles for multiple data objects.
    
    Args:
        data_list: List of structured clinical data
        
    Returns:
        List of FHIR bundle dictionaries
    """
    bundles = []
    for i, data in enumerate(data_list):
        try:
            logger.info(f"Generating FHIR bundle {i+1}/{len(data_list)}")
            bundle = await generate_fhir_bundle(data)
            bundles.append(bundle)
        except Exception as e:
            logger.error(f"Failed to generate bundle {i+1}: {e}")
            continue
    
    logger.info(f"Generated {len(bundles)}/{len(data_list)} FHIR bundles successfully")
    return bundles
