import google.generativeai as genai
from app.config import settings
from app.models.schemas import LabReportData, PrescriptionData
import json
import logging
from typing import Union, Dict, Any, List
from PIL import Image

logger = logging.getLogger(__name__)

# Configure Gemini API
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiExtractor:
    """Extract structured medical data using Gemini LLM"""
    
    def __init__(self):
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
    
    def _create_lab_report_prompt(self, text: str) -> str:
        """Create prompt for lab report extraction"""
        return f"""You are a medical data extraction system specialized in processing lab reports.

Extract structured information from the following lab report text and return ONLY a valid JSON object (no markdown, no code blocks, just raw JSON).

Lab Report Text:
{text}

Return a JSON object with this EXACT structure:
{{
  "document_type": "lab_report",
  "report_date": "YYYY-MM-DD or null",
  "service_date": "YYYY-MM-DD or null (date specimen was collected or service rendered)",
  "icd10_codes": ["ICD-10-CM code strings, e.g. E11.9, if visible in document — else empty array []"],
  "place_of_service": "string or null (e.g. office, hospital, laboratory)",
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null",
    "insurance_id": "string or null (member/subscriber ID if visible)"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "npi": "string or null (10-digit National Provider Identifier if present)",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "observations": [
    {{
      "test_name": "string (required)",
      "loinc_code": "string or null (LOINC code for this test if known, e.g. 1962-7)",
      "cpt_code": "string or null (CPT procedure code if present in document)",
      "value": "string or null",
      "unit": "string or null",
      "reference_range": "string or null",
      "status": "final",
      "interpretation": "normal/abnormal/high/low or null"
    }}
  ],
  "diagnosis": "string or null",
  "notes": "string or null"
}}

Important instructions:
- Extract ALL lab test results as separate observations
- Extract ICD-10 codes exactly as printed (e.g. "E11.9", "J18.9") — do NOT guess codes not in the document
- Extract LOINC codes only if explicitly printed — do NOT guess
- Extract NPI only if a 10-digit number is labeled as NPI
- Use null for missing fields, never omit required structure
- Normalize dates to YYYY-MM-DD format
- Include reference ranges exactly as shown
- Return ONLY the JSON object, no explanations or markdown formatting"""

    def _create_lab_report_multimodal_prompt(self, text: str) -> str:
        """Create prompt for lab report extraction using OCR text plus page images."""
        return f"""You are a medical data extraction system specialized in processing lab reports.

You will receive:
1. OCR text extracted from a PDF
2. One or more page images from the same document

The OCR text may be incomplete or noisy. Use the page images as the primary source of truth whenever they reveal more accurate information.

OCR Text:
{text}

Return ONLY a valid JSON object with this EXACT structure:
{{
  "document_type": "lab_report",
  "report_date": "YYYY-MM-DD or null",
  "service_date": "YYYY-MM-DD or null (date specimen was collected or service rendered)",
  "icd10_codes": ["ICD-10-CM code strings if visible — else empty array []"],
  "place_of_service": "string or null",
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null",
    "insurance_id": "string or null"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "npi": "string or null (10-digit NPI if present)",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "observations": [
    {{
      "test_name": "string (required)",
      "loinc_code": "string or null (LOINC code if explicitly printed)",
      "cpt_code": "string or null (CPT code if present)",
      "value": "string or null",
      "unit": "string or null",
      "reference_range": "string or null",
      "status": "final",
      "interpretation": "normal/abnormal/high/low or null"
    }}
  ],
  "diagnosis": "string or null",
  "notes": "string or null"
}}

Important instructions:
- Extract ALL lab test results visible in the images as separate observations
- Prefer page-image evidence when OCR text looks corrupted
- Extract ICD-10, LOINC, NPI codes only if they are explicitly printed — do NOT guess
- Use null for missing fields, never omit required structure
- Normalize dates to YYYY-MM-DD format
- Include reference ranges exactly as shown
- Return ONLY the JSON object, no explanations or markdown formatting"""

    def _create_prescription_prompt(self, text: str) -> str:
        """Create prompt for prescription extraction"""
        return f"""You are a medical data extraction system specialized in processing prescriptions.

Extract structured information from the following prescription text and return ONLY a valid JSON object (no markdown, no code blocks, just raw JSON).

Prescription Text:
{text}

Return a JSON object with this EXACT structure:
{{
  "document_type": "prescription",
  "prescription_date": "YYYY-MM-DD or null",
  "icd10_codes": ["ICD-10-CM code strings if visible in document — else empty array []"],
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null",
    "insurance_id": "string or null (member/subscriber ID if visible)"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "npi": "string or null (10-digit NPI if present)",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "medications": [
    {{
      "medication_name": "string (required)",
      "rxnorm_code": "string or null (RxNorm code if printed in document)",
      "dosage": "string or null",
      "frequency": "string or null",
      "duration": "string or null",
      "route": "oral/IV/topical/etc or null",
      "instructions": "string or null"
    }}
  ],
  "diagnosis": "string or null",
  "notes": "string or null"
}}

Important instructions:
- Extract ALL medications as separate entries
- Extract ICD-10 codes exactly as printed — do NOT guess codes not in the document
- Extract NPI only if a 10-digit number is labeled as NPI
- Use null for missing fields, never omit required structure
- Normalize dates to YYYY-MM-DD format
- Include dosage with units (e.g., "500mg", "10ml")
- Return ONLY the JSON object, no explanations or markdown formatting"""

    def _create_prescription_multimodal_prompt(self, text: str) -> str:
        """Create prompt for prescription extraction using OCR text plus page images."""
        return f"""You are a medical data extraction system specialized in processing prescriptions.

You will receive:
1. OCR text extracted from a PDF
2. One or more page images from the same document

The OCR text may be incomplete or noisy. Use the page images as the primary source of truth whenever they reveal more accurate information.

OCR Text:
{text}

Return ONLY a valid JSON object with this EXACT structure:
{{
  "document_type": "prescription",
  "prescription_date": "YYYY-MM-DD or null",
  "icd10_codes": ["ICD-10-CM code strings if visible — else empty array []"],
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null",
    "insurance_id": "string or null"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "npi": "string or null (10-digit NPI if present)",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "medications": [
    {{
      "medication_name": "string (required)",
      "rxnorm_code": "string or null (RxNorm code if printed)",
      "dosage": "string or null",
      "frequency": "string or null",
      "duration": "string or null",
      "route": "oral/IV/topical/etc or null",
      "instructions": "string or null"
    }}
  ],
  "diagnosis": "string or null",
  "notes": "string or null"
}}

Important instructions:
- Extract ALL medications visible in the images as separate entries
- Prefer page-image evidence when OCR text looks corrupted
- Extract ICD-10, NPI, RxNorm codes only if explicitly printed — do NOT guess
- Use null for missing fields, never omit required structure
- Normalize dates to YYYY-MM-DD format
- Include dosage with units
- Return ONLY the JSON object, no explanations or markdown formatting"""

    async def _call_gemini_with_retry(self, content, max_retries: int = 2) -> str:
        """
        Call Gemini and retry if the response is truncated.

        Checks finish_reason — if it's MAX_TOKENS or the JSON doesn't
        end with '}', retry with higher token limit.
        """
        token_limit = settings.GEMINI_MAX_TOKENS

        for attempt in range(1, max_retries + 1):
            response = self.model.generate_content(
                content,
                generation_config={
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_output_tokens": token_limit,
                    "response_mime_type": "application/json",
                },
            )

            response_text = response.text
            logger.info(f"Gemini attempt {attempt}: {len(response_text)} chars")

            # Check finish reason
            finish_reason = None
            try:
                finish_reason = response.candidates[0].finish_reason
                logger.info(f"Gemini finish_reason: {finish_reason}")
            except (IndexError, AttributeError):
                pass

            # finish_reason 2 = MAX_TOKENS in the protobuf enum
            is_truncated = (
                finish_reason in (2, "MAX_TOKENS", "STOP")
                and not response_text.rstrip().endswith("}")
            )

            if not is_truncated and response_text.rstrip().endswith("}"):
                return response_text

            # Response looks truncated — retry with 2x tokens
            logger.warning(
                f"Gemini response appears truncated (finish={finish_reason}, "
                f"ends_with_brace={response_text.rstrip()[-1:]}). "
                f"Retrying with higher token limit..."
            )
            token_limit = min(token_limit * 2, 65536)

        # Return whatever we got on last attempt
        logger.warning("All Gemini retries done — using best response available")
        return response_text

    def _clean_json_response(self, response_text: str) -> str:
        """Clean and extract JSON from LLM response"""
        import re
        
        # Remove markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Strip whitespace
        response_text = response_text.strip()
        
        # Try to find JSON object boundaries
        # Look for outermost { }
        start = response_text.find('{')
        end = response_text.rfind('}')
        
        if start != -1 and end != -1:
            response_text = response_text[start:end+1]
        
        # Remove any trailing commas before closing braces/brackets
        response_text = re.sub(r',(\s*[}\]])', r'\1', response_text)
        
        # Since we're using response_mime_type="application/json", 
        # the response should already be valid JSON. 
        # Only do minimal cleanup - don't try to "fix" property names or quotes
        # as this can corrupt valid string values containing colons
        
        return response_text
    
    def _repair_json(self, json_str: str) -> dict:
        """Attempt to repair malformed JSON"""
        import re
        
        # Try to parse as-is first
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
        
        # Try common fixes
        # 1. Remove trailing commas
        json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
        
        # 2. Fix unquoted property names
        json_str = re.sub(r'([{,]\s*)([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', json_str)
        
        # 3. Fix single quotes to double quotes
        json_str = json_str.replace("'", '"')
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Last resort: try to extract just the data we need
            raise ValueError("Cannot repair JSON")
    
    async def extract_lab_report(self, text: str, page_images: List[Image.Image] | None = None) -> LabReportData:
        """Extract structured data from lab report text"""
        response_text = ""
        try:
            if page_images:
                prompt = self._create_lab_report_multimodal_prompt(text)
                content = [prompt, *page_images]
            else:
                prompt = self._create_lab_report_prompt(text)
                content = prompt

            response_text = await self._call_gemini_with_retry(content)
            logger.info(f"Gemini raw response (first 1000 chars): {response_text[:1000]}")

            cleaned_json = self._clean_json_response(response_text)
            logger.info(f"Cleaned JSON length: {len(cleaned_json)} chars")

            data_dict = json.loads(cleaned_json)

            lab_data = LabReportData(**data_dict)
            logger.info(f"Successfully extracted lab report with {len(lab_data.observations)} observations")
            return lab_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Full response text:\n{response_text}")
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Lab report extraction error: {e}")
            raise ValueError(f"Failed to extract lab report data: {str(e)}")
    
    async def extract_prescription(self, text: str, page_images: List[Image.Image] | None = None) -> PrescriptionData:
        """Extract structured data from prescription text"""
        response_text = ""
        try:
            if page_images:
                prompt = self._create_prescription_multimodal_prompt(text)
                content = [prompt, *page_images]
            else:
                prompt = self._create_prescription_prompt(text)
                content = prompt

            response_text = await self._call_gemini_with_retry(content)
            logger.info(f"Gemini raw response (first 1000 chars): {response_text[:1000]}")

            cleaned_json = self._clean_json_response(response_text)
            logger.info(f"Cleaned JSON length: {len(cleaned_json)} chars")

            data_dict = json.loads(cleaned_json)

            prescription_data = PrescriptionData(**data_dict)
            logger.info(f"Successfully extracted prescription with {len(prescription_data.medications)} medications")
            return prescription_data

        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {e}")
            logger.error(f"Full response text:\n{response_text}")
            raise ValueError(f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Prescription extraction error: {e}")
            raise ValueError(f"Failed to extract prescription data: {str(e)}")
    
    async def auto_detect_and_extract(
        self,
        text: str,
        page_images: List[Image.Image] | None = None
    ) -> Union[LabReportData, PrescriptionData]:
        """Auto-detect document type and extract accordingly"""
        # Simple heuristic: check for common keywords
        text_lower = text.lower()
        
        # Keywords that indicate lab report
        lab_keywords = ["test", "result", "reference range", "specimen", "laboratory", "pathology"]
        
        # Keywords that indicate prescription
        rx_keywords = ["prescription", "medication", "dosage", "frequency", "rx", "tablet", "capsule"]
        
        lab_score = sum(1 for keyword in lab_keywords if keyword in text_lower)
        rx_score = sum(1 for keyword in rx_keywords if keyword in text_lower)
        
        logger.info(f"Document type detection - Lab score: {lab_score}, Rx score: {rx_score}")
        
        if lab_score >= rx_score:
            logger.info("Detected as lab report")
            return await self.extract_lab_report(text, page_images=page_images)
        else:
            logger.info("Detected as prescription")
            return await self.extract_prescription(text, page_images=page_images)

async def extract_structured_data(
    text: str,
    document_type: str = "auto",
    page_images: List[Image.Image] | None = None
) -> Union[LabReportData, PrescriptionData]:
    """
    Extract structured data from clinical document text using Gemini.
    
    Args:
        text: Extracted text from PDF
        document_type: "lab_report", "prescription", or "auto" for auto-detection
        
    Returns:
        Structured data (LabReportData or PrescriptionData)
    """
    extractor = GeminiExtractor()
    
    if document_type == "lab_report":
        return await extractor.extract_lab_report(text, page_images=page_images)
    elif document_type == "prescription":
        return await extractor.extract_prescription(text, page_images=page_images)
    else:
        return await extractor.auto_detect_and_extract(text, page_images=page_images)


async def extract_structured_data_batch(
    text_sections: List[str], 
    document_type: str = "auto"
) -> List[Union[LabReportData, PrescriptionData]]:
    """
    Extract structured data from multiple document sections in batch.
    
    Args:
        text_sections: List of text sections to process
        document_type: Document type for all sections
        
    Returns:
        List of structured data objects
    """
    logger.info(f"Starting batch extraction for {len(text_sections)} sections")
    
    results = []
    for i, text in enumerate(text_sections):
        try:
            logger.info(f"Processing section {i+1}/{len(text_sections)} ({len(text)} chars)")
            data = await extract_structured_data(text, document_type)
            results.append(data)
            logger.info(f"Section {i+1} processed successfully")
        except Exception as e:
            logger.error(f"Failed to process section {i+1}: {e}")
            # Continue with other sections even if one fails
            continue
    
    logger.info(f"Batch extraction complete: {len(results)}/{len(text_sections)} sections successful")
    return results


def merge_lab_report_data(reports: List[LabReportData]) -> LabReportData:
    """
    Merge multiple lab report data objects into one.
    
    Args:
        reports: List of LabReportData objects
        
    Returns:
        Single merged LabReportData
    """
    if not reports:
        raise ValueError("No reports to merge")
    
    if len(reports) == 1:
        return reports[0]
    
    # Use first report as base
    merged = reports[0]
    
    # Merge observations from all reports
    all_observations = []
    for report in reports:
        all_observations.extend(report.observations)
    
    merged.observations = all_observations
    
    # Collect notes
    notes_list = [r.notes for r in reports if r.notes]
    if notes_list:
        merged.notes = " | ".join(notes_list)
    
    logger.info(f"Merged {len(reports)} lab reports into one with {len(all_observations)} total observations")
    return merged


def merge_prescription_data(prescriptions: List[PrescriptionData]) -> PrescriptionData:
    """
    Merge multiple prescription data objects into one.
    
    Args:
        prescriptions: List of PrescriptionData objects
        
    Returns:
        Single merged PrescriptionData
    """
    if not prescriptions:
        raise ValueError("No prescriptions to merge")
    
    if len(prescriptions) == 1:
        return prescriptions[0]
    
    # Use first prescription as base
    merged = prescriptions[0]
    
    # Merge medications from all prescriptions
    all_medications = []
    for prescription in prescriptions:
        all_medications.extend(prescription.medications)
    
    merged.medications = all_medications
    
    # Collect notes
    notes_list = [p.notes for p in prescriptions if p.notes]
    if notes_list:
        merged.notes = " | ".join(notes_list)
    
    logger.info(f"Merged {len(prescriptions)} prescriptions into one with {len(all_medications)} total medications")
    return merged
