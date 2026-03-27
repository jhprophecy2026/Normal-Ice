from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import ProcessResponse, HealthResponse
from app.services.ocr import extract_pdf_text
from app.services.llm import (
    extract_structured_data, 
    extract_structured_data_batch,
    merge_lab_report_data,
    merge_prescription_data
)
from app.services.fhir_mapper import generate_fhir_bundle, generate_fhir_bundles_batch, merge_fhir_bundles
from app.services.document_splitter import split_document
from app.config import settings
from app.models.schemas import LabReportData, PrescriptionData
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Threshold for using batch processing (in characters)
BATCH_PROCESSING_THRESHOLD = 20000  # ~5000 tokens

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    gemini_configured = bool(settings.GEMINI_API_KEY)
    
    return HealthResponse(
        status="healthy",
        message="Healthcare FHIR API is running",
        gemini_configured=gemini_configured
    )

@router.post("/process-pdf", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(..., description="PDF file (lab report or prescription)")
):
    """
    Process a clinical PDF document and generate FHIR bundle.
    
    Supports batch processing for large multi-report documents.
    
    Steps:
    1. Validate file
    2. Extract text using OCR
    3. Detect if document is large (needs batch processing)
    4. Extract structured data using Gemini LLM (with batching if needed)
    5. Generate FHIR R4 Bundle(s) and merge
    """
    try:
        # Validate file type
        if not file.filename or not file.filename.lower().endswith('.pdf'):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")
        
        # Read file
        pdf_bytes = await file.read()
        
        # Check file size
        if len(pdf_bytes) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")
        
        logger.info(f"Processing PDF: {file.filename}, size: {len(pdf_bytes)} bytes")
        
        # Step 1: Extract text from PDF
        try:
            extracted_text = await extract_pdf_text(pdf_bytes)
            logger.info(f"Extracted {len(extracted_text)} characters from PDF")
        except Exception as e:
            logger.error(f"OCR extraction failed: {e}")
            return ProcessResponse(
                success=False,
                message="Failed to extract text from PDF",
                error=str(e)
            )
        
        # Step 2: Determine if batch processing is needed
        use_batch_processing = len(extracted_text) > BATCH_PROCESSING_THRESHOLD
        sections = []  # Initialize sections list
        
        if use_batch_processing:
            logger.info(f"Document is large ({len(extracted_text)} chars), using batch processing")
            
            # Split document into sections
            try:
                sections = split_document(extracted_text, strategy="smart")
                logger.info(f"Split document into {len(sections)} sections")
            except Exception as e:
                logger.error(f"Document splitting failed: {e}")
                return ProcessResponse(
                    success=False,
                    message="Failed to split document for batch processing",
                    extracted_text=extracted_text,
                    error=str(e)
                )
            
            # Extract structured data from each section
            try:
                structured_data_list = await extract_structured_data_batch(sections, document_type="auto")
                logger.info(f"Extracted {len(structured_data_list)} structured data objects")
                
                if not structured_data_list:
                    raise ValueError("No data extracted from any section")
                
                # Merge all structured data into one
                first_item = structured_data_list[0]
                if isinstance(first_item, LabReportData):
                    # Filter to only LabReportData items
                    lab_reports = [d for d in structured_data_list if isinstance(d, LabReportData)]
                    merged_data = merge_lab_report_data(lab_reports)
                    document_type = "lab_report"
                else:
                    # Filter to only PrescriptionData items
                    prescriptions = [d for d in structured_data_list if isinstance(d, PrescriptionData)]
                    merged_data = merge_prescription_data(prescriptions)
                    document_type = "prescription"
                
                structured_data = merged_data
                
            except Exception as e:
                logger.error(f"Batch LLM extraction failed: {e}")
                return ProcessResponse(
                    success=False,
                    message="Failed to extract structured data from document sections",
                    extracted_text=extracted_text,
                    error=str(e)
                )
        else:
            # Standard single-pass processing for smaller documents
            logger.info(f"Document is small ({len(extracted_text)} chars), using standard processing")
            
            try:
                structured_data = await extract_structured_data(extracted_text, document_type="auto")
                logger.info(f"Extracted structured data: {structured_data.document_type}")
                document_type = structured_data.document_type
            except Exception as e:
                logger.error(f"LLM extraction failed: {e}")
                return ProcessResponse(
                    success=False,
                    message="Failed to extract structured data from text",
                    extracted_text=extracted_text,
                    error=str(e)
                )
        
        # Step 3: Generate FHIR Bundle
        try:
            fhir_bundle = await generate_fhir_bundle(structured_data)
            logger.info(f"Generated FHIR bundle with {len(fhir_bundle.get('entry', []))} resources")
        except Exception as e:
            logger.error(f"FHIR generation failed: {e}")
            return ProcessResponse(
                success=False,
                message="Failed to generate FHIR bundle",
                extracted_text=extracted_text,
                error=str(e)
            )
        
        # Success response
        message = f"Successfully processed {document_type}"
        if use_batch_processing:
            message += f" (batch processed {len(sections)} sections)"
        
        return ProcessResponse(
            success=True,
            message=message,
            extracted_text=extracted_text,
            fhir_bundle=fhir_bundle,
            document_type=document_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error processing PDF: {e}", exc_info=True)
        return ProcessResponse(
            success=False,
            message="An unexpected error occurred",
            error=str(e)
        )
