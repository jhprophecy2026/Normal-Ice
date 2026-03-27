import pdfplumber
import fitz  # PyMuPDF
from typing import Optional
import logging

logger = logging.getLogger(__name__)

class PDFExtractor:
    """Extract text from PDF documents using multiple methods"""
    
    @staticmethod
    def extract_with_pdfplumber(pdf_bytes: bytes) -> str:
        """Extract text using pdfplumber (good for text-based PDFs)"""
        try:
            import io
            text_parts = []
            
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"pdfplumber extraction failed: {e}")
            return ""
    
    @staticmethod
    def extract_with_pymupdf(pdf_bytes: bytes) -> str:
        """Extract text using PyMuPDF (good for scanned/image PDFs)"""
        try:
            text_parts = []
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text = page.get_text()
                if text:
                    text_parts.append(text)
            
            pdf_document.close()
            return "\n\n".join(text_parts)
        except Exception as e:
            logger.error(f"PyMuPDF extraction failed: {e}")
            return ""
    
    @classmethod
    def extract_text(cls, pdf_bytes: bytes) -> str:
        """
        Extract text from PDF using multiple methods.
        Try pdfplumber first, fallback to PyMuPDF if needed.
        """
        # Try pdfplumber first (better for structured PDFs)
        text = cls.extract_with_pdfplumber(pdf_bytes)
        
        # If pdfplumber didn't get much text, try PyMuPDF
        if not text or len(text.strip()) < 50:
            logger.info("pdfplumber yielded minimal text, trying PyMuPDF")
            text = cls.extract_with_pymupdf(pdf_bytes)
        
        if not text or len(text.strip()) < 10:
            raise ValueError("Could not extract meaningful text from PDF")
        
        return text.strip()

async def extract_pdf_text(pdf_bytes: bytes) -> str:
    """
    Main entry point for PDF text extraction.
    
    Args:
        pdf_bytes: PDF file as bytes
        
    Returns:
        Extracted text from PDF
        
    Raises:
        ValueError: If text extraction fails
    """
    try:
        extractor = PDFExtractor()
        text = extractor.extract_text(pdf_bytes)
        logger.info(f"Successfully extracted {len(text)} characters from PDF")
        return text
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        raise ValueError(f"Failed to extract text from PDF: {str(e)}")
