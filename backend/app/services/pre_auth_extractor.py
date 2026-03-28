"""
Gemini-based extractor for pre-authorization medical fields.
Given OCR text (and optionally page images) from a clinical document,
returns a MedicalExtract with the fields needed to fill a pre-auth form.
"""
import json
import logging
from typing import List, Optional
from PIL import Image

import google.generativeai as genai

from app.config import settings
from app.models.pre_auth import MedicalExtract
from app.services.llm import GeminiExtractor   # reuse retry + clean helpers

logger = logging.getLogger(__name__)


_JSON_SCHEMA = """{{
  "hospital_name": "string or null — hospital/clinic name from letterhead",
  "hospital_location": "string or null — city/address of the hospital",
  "hospital_email": "string or null — hospital contact email",
  "hospital_id": "string or null — hospital registration / empanelment ID",
  "rohini_id": "string or null — ROHINI ID of the hospital (format H##XX######)",

  "doctor_name": "string or null — full name with Dr. prefix",
  "doctor_contact": "string or null — doctor's phone/mobile number",
  "doctor_qualification": "string or null — e.g. MBBS, MS, MD, DNB",
  "doctor_registration_no": "string or null — medical council registration number",

  "presenting_complaints": "string or null — chief complaints / reason for admission",
  "duration_of_illness": "string or null — e.g. '2 days', '3 weeks'",
  "date_of_first_consultation": "YYYY-MM-DD or null",
  "provisional_diagnosis": "string or null — primary diagnosis text",
  "icd10_diagnosis_code": "string or null — ICD-10-CM code; infer from diagnosis if not printed",
  "clinical_findings": "string or null — vitals, examination findings, lab/investigation highlights",
  "past_history": "string or null — significant past medical and surgical history",

  "line_of_treatment": "string or null — free-text description of proposed treatment",
  "treatment_medical_management": "true/false/null — is treatment purely medical (medicines/IV)?",
  "treatment_surgical": "true/false/null — does treatment involve surgery?",
  "treatment_intensive_care": "true/false/null — does treatment require ICU/HDU?",
  "treatment_investigation": "true/false/null — is admission for investigation only?",
  "medical_management_details": "string or null — IV drugs, nebulisation, specific regimen details",
  "route_of_drug_administration": "string or null — IV | Oral | IM | Other",
  "surgery_name": "string or null — full name of proposed surgery/procedure",
  "icd10_pcs_code": "string or null — ICD-10-PCS code; infer from surgery name if not printed",

  "admission_date": "YYYY-MM-DD or null",
  "admission_time": "HH:MM (24h) or null",
  "admission_type": "Emergency or Planned or null",
  "expected_days_in_hospital": "integer or null — total expected length of stay",
  "days_in_icu": "integer or null — expected days in ICU/HDU (0 if none)",
  "room_type": "single or twin-sharing or general or null",

  "room_rent_per_day": "number (INR) or null — extract ONLY if printed in document",
  "icu_charges_per_day": "number (INR) or null — extract ONLY if printed",
  "ot_charges": "number (INR) or null — extract ONLY if printed",
  "professional_fees": "number (INR) or null — surgeon + anaesthetist fees if printed",
  "medicines_consumables": "number (INR) or null — extract ONLY if printed",
  "investigation_diagnostics_cost": "number (INR) or null — extract ONLY if printed",
  "other_hospital_expenses": "number (INR) or null — extract ONLY if printed",
  "total_estimated_cost": "number (INR) or null — extract ONLY if printed",

  "diabetes": "true/false/null — does patient have diabetes?",
  "diabetes_since": "string or null — year or date since diabetes diagnosed",
  "hypertension": "true/false/null",
  "hypertension_since": "string or null",
  "heart_disease": "true/false/null",
  "heart_disease_since": "string or null",
  "hyperlipidemias": "true/false/null",
  "osteoarthritis": "true/false/null",
  "asthma_copd": "true/false/null",
  "cancer": "true/false/null",
  "alcohol_drug_abuse": "true/false/null",
  "hiv_std": "true/false/null",
  "other_conditions": "string or null — any other chronic illness details",

  "is_rta": "true/false/null — is this a Road Traffic Accident case?",
  "date_of_injury": "YYYY-MM-DD or null",
  "reported_to_police": "true/false/null",
  "fir_no": "string or null — FIR number if reported",
  "substance_abuse": "true/false/null — alcohol/drug involvement in injury",

  "maternity_g": "string or null — Gravida number e.g. G2",
  "maternity_p": "string or null — Para number e.g. P1",
  "maternity_l": "string or null — Living children e.g. L1",
  "maternity_a": "string or null — Abortions e.g. A0",
  "expected_delivery_date": "YYYY-MM-DD or null"
}}"""

_PROMPT_TEMPLATE = """You are a medical data extraction assistant for a hospital pre-authorization (cashless hospitalization) system in India.

Extract every available field from the clinical document text below and return a single valid JSON object.

Document Text:
{text}

Return ONLY this JSON structure (use null for any field not found):
{schema}

Rules:
- Hospital name, ROHINI ID, email are usually on the letterhead — extract them
- Infer ICD-10-CM code from diagnosis text if not explicitly printed (e.g. Acute Appendicitis → K35.2)
- Infer ICD-10-PCS code from surgery name if not explicitly printed (e.g. Laparoscopic Appendectomy → 0DTJ4ZZ)
- Set treatment_surgical=true if surgery is mentioned; treatment_medical_management=true if only medicines/IV
- Infer treatment_intensive_care=true if ICU/HDU/CCU stay is mentioned
- Extract past history booleans from the "Past Medical History" section (diabetes, hypertension, etc.)
- Extract since-dates for chronic conditions if mentioned (e.g. "DM since 2015" → diabetes_since: "2015")
- Do NOT guess cost fields — only extract if a rupee/INR amount is explicitly printed
- For maternity cases extract G/P/L/A obstetric notation
- Return ONLY the JSON object, no markdown, no explanation
""".replace("{schema}", _JSON_SCHEMA)

_MULTIMODAL_PROMPT_TEMPLATE = """You are a medical data extraction assistant for a hospital pre-authorization (cashless hospitalization) system in India.

You will receive OCR text AND page images from a clinical document.
Use images as the primary source when OCR text is noisy or incomplete.

OCR Text:
{text}

Return ONLY this JSON structure (use null for any field not found):
{schema}

Rules:
- Hospital name, ROHINI ID, email are usually on the letterhead — extract from image if OCR missed them
- Infer ICD-10-CM code from diagnosis text if not explicitly printed
- Infer ICD-10-PCS code from surgery name if not explicitly printed
- Set treatment_surgical=true if surgery is mentioned; treatment_medical_management=true if only medicines/IV
- Extract past history booleans and since-dates from the Past Medical History section
- Do NOT guess cost fields — only extract if a rupee/INR amount is explicitly printed
- Return ONLY the JSON object, no markdown, no explanation
""".replace("{schema}", _JSON_SCHEMA)


async def extract_medical_for_preauth(
    text: str,
    page_images: Optional[List[Image.Image]] = None,
) -> MedicalExtract:
    """
    Run Gemini over the OCR text (+ optional page images) and return
    the pre-auth medical fields as a MedicalExtract instance.
    """
    # Reuse GeminiExtractor's retry + clean helpers
    extractor = GeminiExtractor()

    if page_images:
        prompt = _MULTIMODAL_PROMPT_TEMPLATE.format(text=text)
        content = [prompt, *page_images]
    else:
        prompt = _PROMPT_TEMPLATE.format(text=text)
        content = prompt

    response_text = await extractor._call_gemini_with_retry(content)
    logger.info(f"Pre-auth extract Gemini response ({len(response_text)} chars)")

    cleaned = extractor._clean_json_response(response_text)
    data = json.loads(cleaned)

    extract = MedicalExtract(**{k: v for k, v in data.items() if k in MedicalExtract.model_fields})
    logger.info(f"Pre-auth extract done: diagnosis={extract.provisional_diagnosis!r}")
    return extract
