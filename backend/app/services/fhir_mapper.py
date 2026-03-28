from fhir.resources.bundle import Bundle, BundleEntry
from fhir.resources.patient import Patient
from fhir.resources.practitioner import Practitioner
from fhir.resources.organization import Organization
from fhir.resources.observation import Observation
from fhir.resources.diagnosticreport import DiagnosticReport
from fhir.resources.medication import Medication
from fhir.resources.medicationrequest import MedicationRequest
from fhir.resources.condition import Condition
from fhir.resources.servicerequest import ServiceRequest
from fhir.resources.codeablereference import CodeableReference
from fhir.resources.humanname import HumanName
from fhir.resources.codeableconcept import CodeableConcept
from fhir.resources.coding import Coding
from fhir.resources.reference import Reference
from fhir.resources.quantity import Quantity
from fhir.resources.dosage import Dosage
from fhir.resources.extension import Extension

from app.models.schemas import (
    LabReportData, PrescriptionData, PatientInfo, PractitionerInfo, BillingFlag
)
from typing import Union, List, Optional, Tuple
from datetime import datetime
import logging
import uuid

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants — code system URIs (swap these if requirements change)
# ---------------------------------------------------------------------------
_DATA_ABSENT_REASON_URL = "http://hl7.org/fhir/StructureDefinition/data-absent-reason"
_LOINC_SYSTEM           = "http://loinc.org"
_ICD10_SYSTEM           = "http://hl7.org/fhir/sid/icd-10-cm"
_RXNORM_SYSTEM          = "http://www.nlm.nih.gov/research/umls/rxnorm"
_CPT_SYSTEM             = "http://www.ama-assn.org/go/cpt"
_SNOMED_SYSTEM          = "http://snomed.info/sct"
_NPI_SYSTEM             = "http://hl7.org/fhir/sid/us-npi"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _data_absent_ext(reason: str = "unknown") -> Extension:
    """
    Returns a FHIR dataAbsentReason extension.
    Used on required billing fields that could not be extracted from the document.
    reason codes: unknown | not-asked | not-applicable | error | masked
    """
    return Extension(
        url=_DATA_ABSENT_REASON_URL,
        valueCode=reason,
    )


def _codeable_concept(text: str, system: str = None, code: str = None) -> CodeableConcept:
    """Build a CodeableConcept, optionally with a standard coding."""
    if system and code:
        return CodeableConcept(
            coding=[Coding(system=system, code=code, display=text)],
            text=text,
        )
    return CodeableConcept(text=text)


# ---------------------------------------------------------------------------
# Billing completeness check
# ---------------------------------------------------------------------------

def check_billing_completeness(
    data: Union[LabReportData, PrescriptionData]
) -> List[BillingFlag]:
    """
    Inspect the structured data and flag fields that are missing or incomplete
    and would cause claim denials or revenue loss.

    Returns a list of BillingFlag objects (empty = all critical fields present).

    This is designed to be swappable: the rules live here, the rest of the
    pipeline just consumes the list.
    """
    flags: List[BillingFlag] = []

    # --- Patient ---
    if not data.patient:
        flags.append(BillingFlag(
            field="patient",
            severity="critical",
            message="No patient information extracted — claim cannot be submitted without patient identity.",
        ))
    else:
        p = data.patient
        if not p.name:
            flags.append(BillingFlag(
                field="patient.name",
                severity="critical",
                message="Patient name missing — required on all claim types.",
            ))
        if not p.date_of_birth:
            flags.append(BillingFlag(
                field="patient.date_of_birth",
                severity="critical",
                message="Patient date of birth missing — triggers MA63 remark code denial.",
            ))
        if not p.patient_id:
            flags.append(BillingFlag(
                field="patient.patient_id",
                severity="warning",
                message="No patient/member ID found — may cause matching issues with payer.",
            ))

    # --- Practitioner / NPI ---
    if not data.practitioner or not data.practitioner.name:
        flags.append(BillingFlag(
            field="practitioner.name",
            severity="critical",
            message="Provider name missing — required for claim submission.",
        ))
    if not data.practitioner or not data.practitioner.npi:
        flags.append(BillingFlag(
            field="practitioner.npi",
            severity="critical",
            message="Provider NPI missing — triggers N290 denial (missing/invalid NPI).",
        ))

    # --- Diagnosis / ICD-10 ---
    if not data.icd10_codes:
        flags.append(BillingFlag(
            field="icd10_codes",
            severity="critical",
            message="No ICD-10-CM diagnosis codes — medical necessity cannot be established, CO-16 denial likely.",
        ))

    # --- Service date ---
    service_date = getattr(data, "report_date", None) or getattr(data, "prescription_date", None)
    if not service_date:
        flags.append(BillingFlag(
            field="service_date",
            severity="critical",
            message="Date of service missing — required on Claim.item.servicedDate.",
        ))

    # --- Document-type-specific checks ---
    if isinstance(data, LabReportData):
        obs_without_loinc = [o.test_name for o in data.observations if not o.loinc_code]
        if obs_without_loinc:
            flags.append(BillingFlag(
                field="observations.loinc_code",
                severity="warning",
                message=f"{len(obs_without_loinc)} observation(s) have no LOINC code: "
                        f"{', '.join(obs_without_loinc[:3])}{'...' if len(obs_without_loinc) > 3 else ''}. "
                        "LOINC codes required for lab billing.",
            ))
        if not data.observations:
            flags.append(BillingFlag(
                field="observations",
                severity="critical",
                message="No lab observations extracted — nothing to bill.",
            ))

    elif isinstance(data, PrescriptionData):
        if not data.medications:
            flags.append(BillingFlag(
                field="medications",
                severity="critical",
                message="No medications extracted — nothing to bill.",
            ))
        meds_without_rxnorm = [m.medication_name for m in data.medications if not m.rxnorm_code]
        if meds_without_rxnorm:
            flags.append(BillingFlag(
                field="medications.rxnorm_code",
                severity="warning",
                message=f"{len(meds_without_rxnorm)} medication(s) have no RxNorm code: "
                        f"{', '.join(meds_without_rxnorm[:3])}{'...' if len(meds_without_rxnorm) > 3 else ''}.",
            ))

    critical_count = sum(1 for f in flags if f.severity == "critical")
    warning_count  = sum(1 for f in flags if f.severity == "warning")
    logger.info(f"Billing completeness: {critical_count} critical, {warning_count} warning flags")
    return flags


# ---------------------------------------------------------------------------
# FHIR resource builders
# ---------------------------------------------------------------------------

class FHIRBundleGenerator:
    """Generate FHIR R4 bundles from structured clinical data."""

    @staticmethod
    def _generate_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _create_patient_resource(patient_info: Optional[PatientInfo]) -> Optional[Patient]:
        if not patient_info:
            return None
        try:
            patient = Patient(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Patient",
            )
            if patient_info.name:
                patient.name = [HumanName(text=patient_info.name)]

            if patient_info.gender:
                gender_map = {
                    "male": "male", "m": "male", "man": "male",
                    "female": "female", "f": "female", "woman": "female",
                    "other": "other", "unknown": "unknown",
                }
                patient.gender = gender_map.get(patient_info.gender.lower(), "unknown")

            if patient_info.date_of_birth:
                patient.birthDate = patient_info.date_of_birth

            from fhir.resources.identifier import Identifier
            identifiers = []
            if patient_info.patient_id:
                identifiers.append(Identifier(
                    value=patient_info.patient_id,
                    system="hospital-patient-id",
                ))
            if patient_info.insurance_id:
                identifiers.append(Identifier(
                    value=patient_info.insurance_id,
                    system="insurance-member-id",
                    type=_codeable_concept("Insurance Member ID"),
                ))
            if identifiers:
                patient.identifier = identifiers

            return patient
        except Exception as e:
            logger.error(f"Error creating Patient resource: {e}")
            return None

    @staticmethod
    def _create_practitioner_resource(
        practitioner_info: Optional[PractitionerInfo],
    ) -> Optional[Practitioner]:
        if not practitioner_info or not practitioner_info.name:
            return None
        try:
            from fhir.resources.identifier import Identifier

            practitioner = Practitioner(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Practitioner",
            )
            practitioner.name = [HumanName(text=practitioner_info.name)]

            identifiers = []
            if practitioner_info.npi:
                # NPI present — add as standard identifier
                identifiers.append(Identifier(
                    system=_NPI_SYSTEM,
                    value=practitioner_info.npi,
                ))
            else:
                # NPI absent — flag with dataAbsentReason so downstream systems know
                npi_identifier = Identifier(
                    system=_NPI_SYSTEM,
                    extension=[_data_absent_ext("unknown")],
                )
                identifiers.append(npi_identifier)
                logger.warning("Practitioner NPI missing — added dataAbsentReason on identifier")

            if practitioner_info.practitioner_id:
                identifiers.append(Identifier(value=practitioner_info.practitioner_id))

            practitioner.identifier = identifiers
            return practitioner
        except Exception as e:
            logger.error(f"Error creating Practitioner resource: {e}")
            return None

    @staticmethod
    def _create_organization_resource(org_name: Optional[str]) -> Optional[Organization]:
        if not org_name:
            return None
        try:
            return Organization(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Organization",
                name=org_name,
            )
        except Exception as e:
            logger.error(f"Error creating Organization resource: {e}")
            return None

    @staticmethod
    def _create_observation_resource(
        obs_data,
        patient_ref: Optional[str] = None,
        report_date: Optional[str] = None,
    ) -> Optional[Observation]:
        try:
            # Build code — prefer LOINC when available
            if obs_data.loinc_code:
                obs_code = _codeable_concept(obs_data.test_name, _LOINC_SYSTEM, obs_data.loinc_code)
            else:
                obs_code = CodeableConcept(text=obs_data.test_name)

            observation = Observation(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Observation",
                status=obs_data.status or "final",
                code=obs_code,
            )

            if patient_ref:
                observation.subject = Reference(reference=patient_ref)
            if report_date:
                observation.effectiveDateTime = report_date

            # Value
            if obs_data.value:
                if obs_data.unit:
                    try:
                        observation.valueQuantity = Quantity(
                            value=float(obs_data.value),
                            unit=obs_data.unit,
                        )
                    except (ValueError, TypeError):
                        observation.valueString = obs_data.value
                else:
                    observation.valueString = obs_data.value

            if obs_data.reference_range:
                from fhir.resources.observation import ObservationReferenceRange
                observation.referenceRange = [
                    ObservationReferenceRange(text=obs_data.reference_range)
                ]

            if obs_data.interpretation:
                observation.interpretation = [CodeableConcept(text=obs_data.interpretation)]

            return observation
        except Exception as e:
            logger.error(f"Error creating Observation resource: {e}")
            return None

    @staticmethod
    def _create_service_request_resource(
        obs_data,
        patient_ref: Optional[str] = None,
        practitioner_ref: Optional[str] = None,
        service_date: Optional[str] = None,
    ) -> Optional[ServiceRequest]:
        """
        Create a ServiceRequest (lab order) for a single observation.
        Links the order to the DiagnosticReport for revenue cycle traceability.
        Uses CPT code when available, falls back to LOINC, then plain text.

        Note: fhir.resources R5-style requires CodeableReference for ServiceRequest.code.
        """
        try:
            if obs_data.cpt_code:
                concept = _codeable_concept(obs_data.test_name, _CPT_SYSTEM, obs_data.cpt_code)
            elif obs_data.loinc_code:
                concept = _codeable_concept(obs_data.test_name, _LOINC_SYSTEM, obs_data.loinc_code)
            else:
                concept = CodeableConcept(text=obs_data.test_name)

            sr_data = dict(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="ServiceRequest",
                status="completed",
                intent="order",
                code=CodeableReference(concept=concept),
                subject=Reference(reference=patient_ref) if patient_ref else Reference(reference="Patient/unknown"),
            )
            if practitioner_ref:
                sr_data["requester"] = Reference(reference=practitioner_ref)
            if service_date:
                sr_data["authoredOn"] = service_date

            return ServiceRequest(**sr_data)
        except Exception as e:
            logger.error(f"Error creating ServiceRequest resource: {e}")
            return None

    @staticmethod
    def _create_diagnostic_report_resource(
        observations: List[Observation],
        service_requests: List[ServiceRequest],
        patient_ref: Optional[str] = None,
        practitioner_ref: Optional[str] = None,
        report_date: Optional[str] = None,
    ) -> Optional[DiagnosticReport]:
        if not observations:
            return None
        try:
            report = DiagnosticReport(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="DiagnosticReport",
                status="final",
                code=_codeable_concept("Laboratory Report"),
            )
            if patient_ref:
                report.subject = Reference(reference=patient_ref)
            if practitioner_ref:
                report.performer = [Reference(reference=practitioner_ref)]
            if report_date:
                report.effectiveDateTime = report_date

            report.result = [
                Reference(reference=f"Observation/{obs.id}")
                for obs in observations if obs and obs.id
            ]
            # Link service requests (basedOn) so payers can trace order → result
            if service_requests:
                report.basedOn = [
                    Reference(reference=f"ServiceRequest/{sr.id}")
                    for sr in service_requests if sr and sr.id
                ]
            return report
        except Exception as e:
            logger.error(f"Error creating DiagnosticReport resource: {e}")
            return None

    @staticmethod
    def _create_condition_resource(
        diagnosis: str,
        icd10_codes: List[str],
        patient_ref: Optional[str] = None,
    ) -> Optional[Condition]:
        """
        Create a FHIR Condition with ICD-10-CM coding when available.
        Uses dataAbsentReason on code when no ICD-10 code was extracted.
        """
        try:
            subject = Reference(reference=patient_ref) if patient_ref else Reference(reference="Patient/unknown")

            # Build diagnosis code
            if icd10_codes:
                primary_code = icd10_codes[0]
                diag_code = CodeableConcept(
                    coding=[
                        Coding(system=_ICD10_SYSTEM, code=primary_code, display=diagnosis)
                    ],
                    text=diagnosis,
                )
            else:
                # No ICD-10 — mark with dataAbsentReason so payers know it's missing
                diag_code = CodeableConcept(
                    text=diagnosis,
                    extension=[_data_absent_ext("unknown")],
                )
                logger.warning(f"Condition '{diagnosis}' has no ICD-10 code — added dataAbsentReason")

            condition = Condition(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Condition",
                clinicalStatus=CodeableConcept(
                    coding=[Coding(
                        system="http://terminology.hl7.org/CodeSystem/condition-clinical",
                        code="active",
                    )]
                ),
                subject=subject,
                code=diag_code,
            )
            return condition
        except Exception as e:
            logger.error(f"Error creating Condition resource: {e}")
            return None

    @staticmethod
    def _create_medication_resource(
        medication_name: str, rxnorm_code: Optional[str] = None
    ) -> Optional[Medication]:
        try:
            med_code = (
                _codeable_concept(medication_name, _RXNORM_SYSTEM, rxnorm_code)
                if rxnorm_code
                else _codeable_concept(medication_name)
            )
            return Medication(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="Medication",
                code=med_code,
            )
        except Exception as e:
            logger.error(f"Error creating Medication resource: {e}")
            return None

    @staticmethod
    def _create_medication_request_resource(
        med_data,
        patient_ref: Optional[str] = None,
        practitioner_ref: Optional[str] = None,
        medication_ref: Optional[str] = None,
        prescription_date: Optional[str] = None,
    ) -> Optional[MedicationRequest]:
        try:
            med_request = MedicationRequest(
                id=FHIRBundleGenerator._generate_id(),
                resourceType="MedicationRequest",
                status="active",
                intent="order",
            )
            if medication_ref:
                med_request.medicationReference = Reference(reference=medication_ref)
            else:
                med_request.medicationCodeableConcept = _codeable_concept(med_data.medication_name)

            if patient_ref:
                med_request.subject = Reference(reference=patient_ref)
            if practitioner_ref:
                med_request.requester = Reference(reference=practitioner_ref)
            if prescription_date:
                med_request.authoredOn = prescription_date

            dosage_parts = [
                p for p in [
                    med_data.dosage,
                    med_data.frequency,
                    f"for {med_data.duration}" if med_data.duration else None,
                ]
                if p
            ]
            if dosage_parts:
                med_request.dosageInstruction = [Dosage(text=" ".join(dosage_parts))]

            return med_request
        except Exception as e:
            logger.error(f"Error creating MedicationRequest resource: {e}")
            return None

    # -----------------------------------------------------------------------
    # Bundle assemblers
    # -----------------------------------------------------------------------

    @classmethod
    def generate_lab_report_bundle(cls, data: LabReportData) -> Bundle:
        bundle = Bundle(
            id=cls._generate_id(),
            resourceType="Bundle",
            type="collection",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        entries = []

        # Patient
        patient = cls._create_patient_resource(data.patient)
        patient_ref = None
        if patient:
            entries.append(BundleEntry(resource=patient))
            patient_ref = f"Patient/{patient.id}"

        # Practitioner
        practitioner = cls._create_practitioner_resource(data.practitioner)
        practitioner_ref = None
        if practitioner:
            entries.append(BundleEntry(resource=practitioner))
            practitioner_ref = f"Practitioner/{practitioner.id}"

        # Organization
        organization = cls._create_organization_resource(data.organization_name)
        if organization:
            entries.append(BundleEntry(resource=organization))

        # Effective service date (prefer service_date, fall back to report_date)
        effective_date = data.service_date or data.report_date

        # Observations + ServiceRequests (one ServiceRequest per test order)
        observations: List[Observation] = []
        service_requests: List[ServiceRequest] = []

        for obs_data in data.observations:
            obs = cls._create_observation_resource(obs_data, patient_ref, effective_date)
            if obs:
                observations.append(obs)
                entries.append(BundleEntry(resource=obs))

            sr = cls._create_service_request_resource(
                obs_data, patient_ref, practitioner_ref, effective_date
            )
            if sr:
                service_requests.append(sr)
                entries.append(BundleEntry(resource=sr))

        # DiagnosticReport (references all observations + service requests)
        if observations:
            diagnostic_report = cls._create_diagnostic_report_resource(
                observations, service_requests,
                patient_ref, practitioner_ref, effective_date,
            )
            if diagnostic_report:
                entries.append(BundleEntry(resource=diagnostic_report))

        # Condition (with ICD-10 codes)
        if data.diagnosis:
            condition = cls._create_condition_resource(
                data.diagnosis, data.icd10_codes, patient_ref
            )
            if condition:
                entries.append(BundleEntry(resource=condition))

        # Additional conditions for each extra ICD-10 code beyond the primary
        for icd_code in data.icd10_codes[1:]:
            condition = cls._create_condition_resource(icd_code, [icd_code], patient_ref)
            if condition:
                entries.append(BundleEntry(resource=condition))

        bundle.entry = entries
        return bundle

    @classmethod
    def generate_prescription_bundle(cls, data: PrescriptionData) -> Bundle:
        bundle = Bundle(
            id=cls._generate_id(),
            resourceType="Bundle",
            type="collection",
            timestamp=datetime.utcnow().isoformat() + "Z",
        )
        entries = []

        # Patient
        patient = cls._create_patient_resource(data.patient)
        patient_ref = None
        if patient:
            entries.append(BundleEntry(resource=patient))
            patient_ref = f"Patient/{patient.id}"

        # Practitioner
        practitioner = cls._create_practitioner_resource(data.practitioner)
        practitioner_ref = None
        if practitioner:
            entries.append(BundleEntry(resource=practitioner))
            practitioner_ref = f"Practitioner/{practitioner.id}"

        # Organization
        organization = cls._create_organization_resource(data.organization_name)
        if organization:
            entries.append(BundleEntry(resource=organization))

        # Medications + MedicationRequests
        for med_data in data.medications:
            medication = cls._create_medication_resource(
                med_data.medication_name, med_data.rxnorm_code
            )
            medication_ref = None
            if medication:
                entries.append(BundleEntry(resource=medication))
                medication_ref = f"Medication/{medication.id}"

            med_request = cls._create_medication_request_resource(
                med_data, patient_ref, practitioner_ref,
                medication_ref, data.prescription_date,
            )
            if med_request:
                entries.append(BundleEntry(resource=med_request))

        # Condition (primary diagnosis with ICD-10)
        if data.diagnosis:
            condition = cls._create_condition_resource(
                data.diagnosis, data.icd10_codes, patient_ref
            )
            if condition:
                entries.append(BundleEntry(resource=condition))

        # Additional ICD-10 conditions
        for icd_code in data.icd10_codes[1:]:
            condition = cls._create_condition_resource(icd_code, [icd_code], patient_ref)
            if condition:
                entries.append(BundleEntry(resource=condition))

        bundle.entry = entries
        return bundle


# ---------------------------------------------------------------------------
# Public entry points
# ---------------------------------------------------------------------------

async def generate_fhir_bundle(
    data: Union[LabReportData, PrescriptionData],
) -> Tuple[dict, List[BillingFlag]]:
    """
    Generate a FHIR R4 Bundle from structured clinical data.

    Returns:
        (bundle_dict, billing_flags)
        billing_flags — list of missing/incomplete fields that affect revenue.
                        Empty list means all critical billing fields are present.
    """
    try:
        generator = FHIRBundleGenerator()

        if isinstance(data, LabReportData):
            bundle = generator.generate_lab_report_bundle(data)
        elif isinstance(data, PrescriptionData):
            bundle = generator.generate_prescription_bundle(data)
        else:
            raise ValueError(f"Unsupported data type: {type(data)}")

        billing_flags = check_billing_completeness(data)
        bundle_dict = bundle.dict(exclude_none=True)

        logger.info(
            f"Generated FHIR bundle: {len(bundle.entry)} resources, "
            f"{sum(1 for f in billing_flags if f.severity == 'critical')} critical billing flags"
        )
        return bundle_dict, billing_flags

    except Exception as e:
        logger.error(f"FHIR bundle generation error: {e}")
        raise ValueError(f"Failed to generate FHIR bundle: {str(e)}")


def merge_fhir_bundles(bundles: List[dict]) -> dict:
    """Merge multiple FHIR bundles into a single bundle, deduplicating Patient/Practitioner/Organization."""
    if not bundles:
        raise ValueError("No bundles to merge")
    if len(bundles) == 1:
        return bundles[0]

    merged_bundle = {
        "resourceType": "Bundle",
        "id": FHIRBundleGenerator._generate_id(),
        "type": "collection",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "entry": [],
    }

    seen_singleton_types = set()
    unique_entries = []

    for bundle in bundles:
        for entry in bundle.get("entry", []):
            resource_type = entry.get("resource", {}).get("resourceType")
            if resource_type in ("Patient", "Practitioner", "Organization"):
                if resource_type not in seen_singleton_types:
                    seen_singleton_types.add(resource_type)
                    unique_entries.append(entry)
            else:
                unique_entries.append(entry)

    merged_bundle["entry"] = unique_entries
    logger.info(f"Merged {len(bundles)} bundles → {len(unique_entries)} resources")
    return merged_bundle
