import gc

from fastapi import APIRouter, UploadFile, File, HTTPException
from app.models.schemas import ProcessResponse, HealthResponse, LabReportData, PrescriptionData
from app.services.ocr import extract_pdf_text, render_gemini_thumbnails
from app.services.llm import (
    extract_structured_data,
    extract_structured_data_batch,
    merge_lab_report_data,
    merge_prescription_data,
)
from app.services.fhir_mapper import generate_fhir_bundle
from app.services.document_splitter import split_document
from app.services.ocr_strategies.quality_checker import TextQualityChecker
from app.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------
BATCH_PROCESSING_THRESHOLD = 20000  # chars — above this we split + batch
OCR_QUALITY_GOOD = 75.0             # text-only to Gemini
OCR_QUALITY_USABLE = 40.0           # below this → images-only to Gemini


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="healthy",
        message="Healthcare FHIR API is running",
        gemini_configured=bool(settings.GEMINI_API_KEY),
    )


@router.post("/process-pdf", response_model=ProcessResponse)
async def process_pdf(
    file: UploadFile = File(..., description="PDF file (lab report or prescription)"),
):
    """
    Process a clinical PDF and generate a FHIR R4 bundle.

    Memory-optimized pipeline:
        1. Validate upload.
        2. PaddleOCR each page one-at-a-time (constant memory).
        3. Quality-gate the OCR output.
        4. Only render Gemini thumbnails if OCR quality is poor.
        5. Extract structured data via Gemini.
        6. Generate FHIR bundle.
    """
    try:
        # ------------------------------------------------------------------
        # 1. Validate upload
        # ------------------------------------------------------------------
        if not file.filename or not file.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail="Only PDF files are supported")

        pdf_bytes = await file.read()

        if len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty")

        if len(pdf_bytes) > settings.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {settings.MAX_FILE_SIZE // (1024 * 1024)}MB limit",
            )

        logger.info(f"Processing PDF: {file.filename} ({len(pdf_bytes)} bytes)")

        # ------------------------------------------------------------------
        # 2. OCR — page-at-a-time PaddleOCR (memory efficient)
        # ------------------------------------------------------------------
        try:
            extracted_text, pdf_bytes_ref = await extract_pdf_text(pdf_bytes)
        except ValueError as exc:
            logger.error(f"PDF rendering failed: {exc}")
            return ProcessResponse(
                success=False,
                message="Failed to render PDF pages for OCR",
                error=str(exc),
            )
        except Exception as exc:
            logger.error(f"OCR pipeline error: {exc}", exc_info=True)
            return ProcessResponse(
                success=False,
                message="Unexpected error during OCR extraction",
                error=str(exc),
            )

        # ------------------------------------------------------------------
        # 3. Quality gate — decide if we need Gemini multimodal
        # ------------------------------------------------------------------
        quality_score = TextQualityChecker.get_quality_score(extracted_text) if extracted_text else 0.0
        logger.info(f"OCR quality: {quality_score:.1f}/100 | {len(extracted_text)} chars")

        send_images = None

        if quality_score >= OCR_QUALITY_GOOD:
            # Good OCR → text-only (no extra images in RAM)
            logger.info("Strategy: text-only (good OCR)")
        elif quality_score >= OCR_QUALITY_USABLE:
            # Mediocre → render small thumbnails for Gemini to cross-reference
            logger.info("Strategy: text + thumbnails (mediocre OCR)")
            send_images = render_gemini_thumbnails(pdf_bytes_ref)
        else:
            # Poor/empty → Gemini reads the images directly
            logger.info("Strategy: thumbnails primary (poor/no OCR)")
            send_images = render_gemini_thumbnails(pdf_bytes_ref)
            if not extracted_text:
                extracted_text = ""

        # Free the PDF bytes now — we don't need them anymore
        del pdf_bytes_ref
        gc.collect()

        # ------------------------------------------------------------------
        # 4. Structured data extraction via Gemini
        # ------------------------------------------------------------------
        use_batch = len(extracted_text) > BATCH_PROCESSING_THRESHOLD
        sections = []

        if use_batch:
            logger.info(f"Large document ({len(extracted_text)} chars) — batch processing")

            # Free thumbnails before batch — batch uses text only
            if send_images:
                for img in send_images:
                    img.close()
                del send_images
                send_images = None
                gc.collect()

            try:
                sections = split_document(extracted_text, strategy="smart")
                logger.info(f"Split into {len(sections)} sections")
            except Exception as exc:
                logger.error(f"Document splitting failed: {exc}")
                return ProcessResponse(
                    success=False,
                    message="Failed to split large document for batch processing",
                    extracted_text=extracted_text,
                    error=str(exc),
                )

            try:
                results = await extract_structured_data_batch(sections, document_type="auto")
                if not results:
                    raise ValueError("No structured data extracted from any section")

                first = results[0]
                if isinstance(first, LabReportData):
                    structured_data = merge_lab_report_data(
                        [r for r in results if isinstance(r, LabReportData)]
                    )
                    document_type = "lab_report"
                else:
                    structured_data = merge_prescription_data(
                        [r for r in results if isinstance(r, PrescriptionData)]
                    )
                    document_type = "prescription"

            except Exception as exc:
                logger.error(f"Batch LLM extraction failed: {exc}")
                return ProcessResponse(
                    success=False,
                    message="Failed to extract structured data (batch)",
                    extracted_text=extracted_text,
                    error=str(exc),
                )
        else:
            # Standard single-pass extraction
            try:
                structured_data = await extract_structured_data(
                    extracted_text,
                    document_type="auto",
                    page_images=send_images,
                )
                document_type = structured_data.document_type
                logger.info(f"Extracted structured data: {document_type}")
            except Exception as exc:
                logger.error(f"LLM extraction failed: {exc}")
                return ProcessResponse(
                    success=False,
                    message="Failed to extract structured data from document",
                    extracted_text=extracted_text,
                    error=str(exc),
                )
            finally:
                # Free thumbnail images after Gemini call
                if send_images:
                    for img in send_images:
                        img.close()
                    del send_images
                    gc.collect()

        # ------------------------------------------------------------------
        # 5. Generate FHIR R4 Bundle + billing completeness check
        # ------------------------------------------------------------------
        try:
            fhir_bundle, billing_flags = await generate_fhir_bundle(structured_data)
            critical = sum(1 for f in billing_flags if f.severity == "critical")
            warning  = sum(1 for f in billing_flags if f.severity == "warning")
            logger.info(
                f"FHIR bundle: {len(fhir_bundle.get('entry', []))} resources | "
                f"billing flags: {critical} critical, {warning} warning"
            )
        except Exception as exc:
            logger.error(f"FHIR generation failed: {exc}")
            return ProcessResponse(
                success=False,
                message="Failed to generate FHIR bundle",
                extracted_text=extracted_text,
                error=str(exc),
            )

        # ------------------------------------------------------------------
        # 6. Success
        # ------------------------------------------------------------------
        message = f"Successfully processed {document_type}"
        if use_batch:
            message += f" (batch: {len(sections)} sections)"

        return ProcessResponse(
            success=True,
            message=message,
            extracted_text=extracted_text,
            fhir_bundle=fhir_bundle,
            document_type=document_type,
            billing_flags=billing_flags,
        )

    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error: {exc}", exc_info=True)
        return ProcessResponse(
            success=False,
            message="An unexpected error occurred while processing the PDF",
            error=str(exc),
        )
