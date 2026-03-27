import google.generativeai as genai
from app.config import settings
from app.models.schemas import LabReportData, PrescriptionData
import json
import logging
from typing import Union, Dict, Any, List

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
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "observations": [
    {{
      "test_name": "string (required)",
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
  "patient": {{
    "name": "string or null",
    "age": number or null,
    "gender": "string or null",
    "patient_id": "string or null",
    "date_of_birth": "YYYY-MM-DD or null",
    "contact": "string or null"
  }},
  "practitioner": {{
    "name": "string or null",
    "specialty": "string or null",
    "practitioner_id": "string or null",
    "contact": "string or null"
  }},
  "organization_name": "string or null",
  "medications": [
    {{
      "medication_name": "string (required)",
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
- Use null for missing fields, never omit required structure
- Normalize dates to YYYY-MM-DD format
- Include dosage with units (e.g., "500mg", "10ml")
- Return ONLY the JSON object, no explanations or markdown formatting"""

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
    
    async def extract_lab_report(self, text: str) -> LabReportData:
        """Extract structured data from lab report text"""
        response_text = ""
        try:
            prompt = self._create_lab_report_prompt(text)
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_output_tokens": settings.GEMINI_MAX_TOKENS,
                    "response_mime_type": "application/json"  # Force JSON output
                }
            )
            
            # Extract and clean response
            response_text = response.text
            logger.info(f"Gemini raw response length: {len(response_text)} chars")
            logger.info(f"Gemini raw response (first 1000 chars): {response_text[:1000]}")
            
            cleaned_json = self._clean_json_response(response_text)
            logger.info(f"Cleaned JSON length: {len(cleaned_json)} chars")
            
            data_dict = json.loads(cleaned_json)
            
            # Validate and parse with Pydantic
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
    
    async def extract_prescription(self, text: str) -> PrescriptionData:
        """Extract structured data from prescription text"""
        response_text = ""
        try:
            prompt = self._create_prescription_prompt(text)
            
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "temperature": settings.GEMINI_TEMPERATURE,
                    "max_output_tokens": settings.GEMINI_MAX_TOKENS,
                    "response_mime_type": "application/json"  # Force JSON output
                }
            )
            
            # Extract and clean response
            response_text = response.text
            logger.info(f"Gemini raw response length: {len(response_text)} chars")
            logger.info(f"Gemini raw response (first 1000 chars): {response_text[:1000]}")
            
            cleaned_json = self._clean_json_response(response_text)
            logger.info(f"Cleaned JSON length: {len(cleaned_json)} chars")
            
            data_dict = json.loads(cleaned_json)
            
            # Validate and parse with Pydantic
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
    
    async def auto_detect_and_extract(self, text: str) -> Union[LabReportData, PrescriptionData]:
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
            return await self.extract_lab_report(text)
        else:
            logger.info("Detected as prescription")
            return await self.extract_prescription(text)

async def extract_structured_data(text: str, document_type: str = "auto") -> Union[LabReportData, PrescriptionData]:
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
        return await extractor.extract_lab_report(text)
    elif document_type == "prescription":
        return await extractor.extract_prescription(text)
    else:
        return await extractor.auto_detect_and_extract(text)


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
