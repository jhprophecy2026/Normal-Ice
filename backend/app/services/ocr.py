"""
PDF text extraction pipeline (memory-optimized).

Pipeline:
  PDF bytes → detect if text-based (PyMuPDF native) or image-based (scanned)
    → text-based: extract directly via PyMuPDF (no OCR needed)
    → image-based: render ONE page at a time → PaddleOCR → collect text
  Then render lightweight thumbnails for Gemini multimodal fallback if needed.

Memory strategy:
  - OCR phase: render + OCR + discard each page individually (never hold all at once)
  - Gemini fallback: render small thumbnails (150 DPI, max 5 pages) only when needed
"""
import gc
import io
import logging
from typing import List, Optional

import fitz  # PyMuPDF – rendering pages to images AND native text extraction
from PIL import Image

from app.services.ocr_strategies.image_based import PaddleOCREngine
from app.services.ocr_strategies.quality_checker import TextQualityChecker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
OCR_DPI = 150          # 150 DPI is sufficient for PaddleOCR on typed medical docs — cuts image size ~44% vs 200 DPI
THUMBNAIL_DPI = 150    # Lower DPI for Gemini multimodal (it doesn't need 300)
MAX_OCR_PAGES = 50     # Safety cap for OCR
MAX_GEMINI_PAGES = 5   # Max pages to send as images to Gemini (token limit)

# Min average chars per page to consider the PDF "text-based"
_NATIVE_TEXT_THRESHOLD = 50


# ---------------------------------------------------------------------------
# Native text detection (text-based PDFs — no OCR needed)
# ---------------------------------------------------------------------------

def _detect_and_extract_native_text(pdf_document) -> tuple[str, bool]:
    """
    Try to extract embedded text directly from a PDF using PyMuPDF.

    Samples the first 3 pages to decide if the PDF has real embedded text.
    If yes, extracts all pages natively (fast, zero OCR cost).
    If no (scanned/image PDF), returns ("", False) so PaddleOCR takes over.

    Returns:
        (text, is_text_based)
    """
    page_count = pdf_document.page_count
    sample_n = min(page_count, 3)

    sample_chars = 0
    for i in range(sample_n):
        sample_chars += len(pdf_document[i].get_text("text").strip())

    avg_chars = sample_chars / sample_n if sample_n else 0
    is_text_based = avg_chars >= _NATIVE_TEXT_THRESHOLD

    if not is_text_based:
        logger.info(
            f"Native text check: {avg_chars:.0f} avg chars/page — image-based PDF, will use PaddleOCR"
        )
        return "", False

    logger.info(
        f"Native text check: {avg_chars:.0f} avg chars/page — text-based PDF, skipping PaddleOCR"
    )

    # Full extraction across all pages
    page_texts: List[str] = []
    for i in range(page_count):
        text = pdf_document[i].get_text("text").strip()
        if text:
            page_texts.append(text)

    return "\n\n".join(page_texts), True


# ---------------------------------------------------------------------------
# Page-at-a-time OCR (memory efficient — only for image-based PDFs)
# ---------------------------------------------------------------------------

def _render_single_page(pdf_document, page_num: int, dpi: int) -> Image.Image:
    """Render a single PDF page to a PIL Image and return it."""
    scale = dpi / 72.0
    matrix = fitz.Matrix(scale, scale)
    page = pdf_document[page_num]
    pixmap = page.get_pixmap(matrix=matrix, alpha=False)
    img = Image.open(io.BytesIO(pixmap.tobytes("png"))).convert("RGB")
    return img


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """
    Extract text from a PDF — native if text-based, PaddleOCR if image-based.

    Decision flow:
        1. Open the PDF with PyMuPDF.
        2. Sample first 3 pages for embedded text.
           → If text-based (≥50 avg chars/page): return native text immediately.
           → If image-based: fall through to page-at-a-time PaddleOCR.

    Args:
        pdf_bytes: Raw PDF bytes.

    Returns:
        Combined extracted text from all pages.

    Raises:
        ValueError: If the PDF cannot be opened.
        RuntimeError: If PaddleOCR is unavailable.
    """
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        raise ValueError(f"Cannot open PDF: {exc}") from exc

    if pdf_document.page_count == 0:
        pdf_document.close()
        raise ValueError("PDF has zero pages")

    try:
        # --- Step 1: try native text extraction (free, instant) ---
        native_text, is_text_based = _detect_and_extract_native_text(pdf_document)
        if is_text_based:
            return native_text

        # --- Step 2: image-based PDF — PaddleOCR page-at-a-time ---
        page_count = min(pdf_document.page_count, MAX_OCR_PAGES)
        page_texts: List[str] = []

        for page_num in range(page_count):
            try:
                img = _render_single_page(pdf_document, page_num, OCR_DPI)
                page_text = PaddleOCREngine.extract_text(img)
                img.close()
                del img

                if page_text:
                    page_texts.append(page_text)
                    logger.info(f"Page {page_num + 1}/{page_count}: {len(page_text)} chars")
                else:
                    logger.warning(f"Page {page_num + 1}/{page_count}: empty")

            except Exception as exc:
                logger.error(f"Page {page_num + 1}/{page_count} failed: {exc}")
                continue

            if (page_num + 1) % 5 == 0:
                gc.collect()

        return "\n\n".join(page_texts).strip()

    finally:
        pdf_document.close()
        gc.collect()


# ---------------------------------------------------------------------------
# Lightweight thumbnails for Gemini multimodal fallback
# ---------------------------------------------------------------------------

def render_gemini_thumbnails(pdf_bytes: bytes) -> List[Image.Image]:
    """
    Render a small number of low-res page thumbnails for Gemini multimodal.

    These are only created when OCR quality is poor and we need Gemini
    to read the document visually. Uses lower DPI and fewer pages to
    stay within Gemini's token limits and save memory.

    Args:
        pdf_bytes: Raw PDF bytes.

    Returns:
        List of PIL Images (max MAX_GEMINI_PAGES pages at THUMBNAIL_DPI).
    """
    try:
        pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:
        logger.error(f"Cannot open PDF for thumbnails: {exc}")
        return []

    page_count = min(pdf_document.page_count, MAX_GEMINI_PAGES)
    images: List[Image.Image] = []

    try:
        for page_num in range(page_count):
            try:
                img = _render_single_page(pdf_document, page_num, THUMBNAIL_DPI)
                images.append(img)
            except Exception as exc:
                logger.error(f"Thumbnail page {page_num + 1} failed: {exc}")
                continue
    finally:
        pdf_document.close()

    logger.info(f"Rendered {len(images)} Gemini thumbnails at {THUMBNAIL_DPI} DPI")
    return images


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def extract_pdf_text(pdf_bytes: bytes) -> tuple[str, bytes]:
    """
    Main entry point for PDF text extraction.

    Returns the extracted text and keeps the raw pdf_bytes reference
    so the caller can request Gemini thumbnails later if needed
    (only when OCR quality is poor — avoids rendering twice upfront).

    Pipeline:
        1. Detect if PDF is text-based (PyMuPDF native) or image-based.
           → text-based: extract natively, skip PaddleOCR entirely.
           → image-based: PaddleOCR each page one-at-a-time (memory efficient).
        2. Quality-score the result.
        3. Return (text, pdf_bytes) — caller decides about multimodal.

    Args:
        pdf_bytes: Raw PDF bytes.

    Returns:
        Tuple of (extracted_text, pdf_bytes).

    Raises:
        ValueError: If the PDF cannot be rendered at all.
    """
    # Step 1 — Native text if possible, PaddleOCR fallback for scanned PDFs
    extracted_text = ""
    try:
        extracted_text = extract_text_from_pdf(pdf_bytes)
        logger.info(f"Text extraction total: {len(extracted_text)} chars")
    except RuntimeError as exc:
        logger.error(f"PaddleOCR unavailable: {exc}")
    except ValueError:
        raise  # PDF couldn't be opened — bubble up
    except Exception as exc:
        logger.error(f"PaddleOCR error: {exc}")

    # Step 2 — Quality assessment
    if extracted_text:
        score = TextQualityChecker.get_quality_score(extracted_text)
        logger.info(f"OCR quality score: {score:.1f}/100")
    else:
        logger.warning("No text extracted — multimodal fallback will be needed")

    return extracted_text, pdf_bytes
