import json
import hashlib
import threading
import uuid
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Union, Dict, Any

from app.models.schemas import LabReportData, PrescriptionData
from app.models.patient_store import (
    StoredPatientRecord,
    PatientSummary,
    DocumentRecord,
)
from app.config import settings

logger = logging.getLogger(__name__)


class PatientStore:
    """JSON file-based patient storage with thread-safe operations.

    Layout
    ------
    DATA_DIR/
        index.json              – Dict[patient_id, PatientSummary]
        {patient_id}.json       – Full StoredPatientRecord
    """

    _lock = threading.Lock()

    def __init__(self):
        self.data_dir = Path(settings.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.data_dir / "index.json"
        if not self.index_path.exists():
            self._save_index({})

    # ------------------------------------------------------------------
    # Index helpers
    # ------------------------------------------------------------------
    def _load_index(self) -> Dict[str, dict]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_index(self, index: Dict[str, dict]):
        self.index_path.write_text(
            json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    # ------------------------------------------------------------------
    # Patient file helpers
    # ------------------------------------------------------------------
    def _patient_path(self, patient_id: str) -> Path:
        return self.data_dir / f"{patient_id}.json"

    def _load_patient(self, patient_id: str) -> Optional[StoredPatientRecord]:
        path = self._patient_path(patient_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return StoredPatientRecord(**data)
        except Exception as e:
            logger.error(f"Failed to load patient {patient_id}: {e}")
            return None

    def _save_patient(self, record: StoredPatientRecord):
        path = self._patient_path(record.patient_id)
        path.write_text(
            json.dumps(record.model_dump(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    # ------------------------------------------------------------------
    # Patient ID resolution
    # ------------------------------------------------------------------
    @staticmethod
    def _name_dob_hash(name: str, dob: str) -> str:
        """Deterministic hash from name + DOB for matching without ABHA."""
        key = f"{name.strip().lower()}|{dob.strip()}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _resolve_patient_id(
        self,
        patient_info,
        index: Dict[str, dict],
    ) -> tuple[str, bool]:
        """Return (patient_id, is_existing).

        Priority:
        1. ABHA ID (patient_info.patient_id that looks like an ABHA)
        2. Name + DOB hash match
        3. Generate new UUID
        """
        abha_id = None
        if patient_info and patient_info.patient_id:
            abha_id = patient_info.patient_id.strip()

        # 1. Match by ABHA / patient_id
        if abha_id:
            for pid, summary in index.items():
                if summary.get("abha_id") == abha_id:
                    return pid, True
            # ABHA not seen before — use it as the patient_id
            return abha_id, False

        # 2. Match by name + DOB hash
        if patient_info and patient_info.name and patient_info.date_of_birth:
            h = self._name_dob_hash(patient_info.name, patient_info.date_of_birth)
            for pid, summary in index.items():
                if pid == h:
                    return pid, True
            return h, False

        # 3. Fallback: UUID
        return str(uuid.uuid4())[:12], False

    # ------------------------------------------------------------------
    # Data merging
    # ------------------------------------------------------------------
    @staticmethod
    def _observation_key(obs: dict) -> str:
        return f"{obs.get('test_name', '')}|{obs.get('value', '')}|{obs.get('unit', '')}"

    @staticmethod
    def _medication_key(med: dict) -> str:
        return f"{med.get('medication_name', '')}|{med.get('dosage', '')}|{med.get('frequency', '')}"

    def _merge_into(
        self,
        existing: StoredPatientRecord,
        new_data: Union[LabReportData, PrescriptionData],
        fhir_bundle: dict,
        filename: str,
    ) -> StoredPatientRecord:
        """Merge new extraction results into an existing patient record."""
        now = datetime.utcnow().isoformat() + "Z"

        # Update patient demographics (prefer non-None new values)
        pi = new_data.patient
        if pi:
            if pi.name:
                existing.name = pi.name
            if pi.age is not None:
                existing.age = pi.age
            if pi.gender:
                existing.gender = pi.gender
            if pi.date_of_birth:
                existing.date_of_birth = pi.date_of_birth
            if pi.contact:
                existing.contact = pi.contact

        # Practitioner / org
        if new_data.practitioner and new_data.practitioner.name:
            existing.practitioner_name = new_data.practitioner.name
            existing.practitioner_id = new_data.practitioner.practitioner_id
        if new_data.organization_name:
            existing.organization_name = new_data.organization_name

        # Observations — deduplicate by composite key
        if isinstance(new_data, LabReportData):
            existing_keys = {self._observation_key(o) for o in existing.observations}
            for obs in new_data.observations:
                obs_dict = obs.model_dump()
                if self._observation_key(obs_dict) not in existing_keys:
                    existing.observations.append(obs_dict)
                    existing_keys.add(self._observation_key(obs_dict))

        # Medications — deduplicate by composite key
        if isinstance(new_data, PrescriptionData):
            existing_keys = {self._medication_key(m) for m in existing.medications}
            for med in new_data.medications:
                med_dict = med.model_dump()
                if self._medication_key(med_dict) not in existing_keys:
                    existing.medications.append(med_dict)
                    existing_keys.add(self._medication_key(med_dict))

        # Diagnoses — deduplicate
        if new_data.diagnosis and new_data.diagnosis not in existing.diagnoses:
            existing.diagnoses.append(new_data.diagnosis)

        # FHIR bundles
        existing.fhir_bundles.append(fhir_bundle)

        # Document history
        doc_type = "lab_report" if isinstance(new_data, LabReportData) else "prescription"
        existing.documents.append(
            DocumentRecord(
                filename=filename,
                upload_date=now,
                document_type=doc_type,
                extracted_text_preview=None,
            )
        )

        existing.updated_at = now
        return existing

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def save_patient(
        self,
        structured_data: Union[LabReportData, PrescriptionData],
        fhir_bundle: dict,
        filename: str,
    ) -> tuple[str, str]:
        """Persist extraction results. Returns (patient_id, action).

        action is "created" or "updated".
        """
        with self._lock:
            index = self._load_index()
            patient_info = structured_data.patient
            patient_id, is_existing = self._resolve_patient_id(patient_info, index)

            if is_existing:
                record = self._load_patient(patient_id)
                if record is None:
                    # Index out of sync — treat as new
                    is_existing = False

            if is_existing and record:
                record = self._merge_into(record, structured_data, fhir_bundle, filename)
                action = "updated"
            else:
                # Build a fresh record
                now = datetime.utcnow().isoformat() + "Z"
                doc_type = (
                    "lab_report"
                    if isinstance(structured_data, LabReportData)
                    else "prescription"
                )
                observations = []
                medications = []
                if isinstance(structured_data, LabReportData):
                    observations = [o.model_dump() for o in structured_data.observations]
                if isinstance(structured_data, PrescriptionData):
                    medications = [m.model_dump() for m in structured_data.medications]

                diagnoses = [structured_data.diagnosis] if structured_data.diagnosis else []

                record = StoredPatientRecord(
                    patient_id=patient_id,
                    abha_id=patient_info.patient_id if patient_info else None,
                    name=patient_info.name if patient_info else None,
                    age=patient_info.age if patient_info else None,
                    gender=patient_info.gender if patient_info else None,
                    date_of_birth=patient_info.date_of_birth if patient_info else None,
                    contact=patient_info.contact if patient_info else None,
                    practitioner_name=(
                        structured_data.practitioner.name
                        if structured_data.practitioner
                        else None
                    ),
                    practitioner_id=(
                        structured_data.practitioner.practitioner_id
                        if structured_data.practitioner
                        else None
                    ),
                    organization_name=structured_data.organization_name,
                    observations=observations,
                    medications=medications,
                    diagnoses=diagnoses,
                    fhir_bundles=[fhir_bundle],
                    documents=[
                        DocumentRecord(
                            filename=filename,
                            upload_date=now,
                            document_type=doc_type,
                        )
                    ],
                    created_at=now,
                    updated_at=now,
                )
                action = "created"

            # Persist
            self._save_patient(record)

            # Update index
            index[patient_id] = PatientSummary(
                patient_id=record.patient_id,
                name=record.name,
                abha_id=record.abha_id,
                document_count=len(record.documents),
                last_updated=record.updated_at,
            ).model_dump()
            self._save_index(index)

            logger.info(f"Patient {patient_id} {action} ({len(record.documents)} docs)")
            return patient_id, action

    def get_patient(self, patient_id: str) -> Optional[StoredPatientRecord]:
        with self._lock:
            return self._load_patient(patient_id)

    def list_patients(self, search_query: Optional[str] = None) -> List[PatientSummary]:
        with self._lock:
            index = self._load_index()

        summaries = [PatientSummary(**v) for v in index.values()]

        if search_query:
            q = search_query.lower()
            summaries = [
                s
                for s in summaries
                if (s.name and q in s.name.lower())
                or (s.abha_id and q in s.abha_id.lower())
                or q in s.patient_id.lower()
            ]

        # Sort by last_updated descending
        summaries.sort(key=lambda s: s.last_updated, reverse=True)
        return summaries

    def delete_patient(self, patient_id: str) -> bool:
        with self._lock:
            index = self._load_index()
            if patient_id not in index:
                return False

            # Remove file
            path = self._patient_path(patient_id)
            if path.exists():
                path.unlink()

            # Remove from index
            del index[patient_id]
            self._save_index(index)

            logger.info(f"Deleted patient {patient_id}")
            return True


# Module-level singleton
patient_store = PatientStore()
