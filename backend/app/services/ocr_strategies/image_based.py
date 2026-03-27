"""
Image-based OCR using Tesseract
"""
import pytesseract
from pdf2image import convert_from_bytes
from PIL import Image, ImageEnhance
import logging
from typing import Optional
import io
import os

logger = logging.getLogger(__name__)

class TesseractOCR:
    """Tesseract-based OCR for scanned/image PDFs"""
    
    def __init__(self, tesseract_path: Optional[str] = None):
        """
        Initialize Tesseract OCR.
        
        Args:
            tesseract_path: Path to tesseract executable (Windows only)
        """
        # Configure Tesseract path (Windows)
        import platform
        if platform.system() == 'Windows':
            if tesseract_path:
                pytesseract.pytesseract.tesseract_cmd = tesseract_path
            else:
                # Default Windows installation path
                pytesseract.pytesseract.tesseract_cmd = (
                    r'C:\Program Files\Tesseract-OCR\tesseract.exe'
                )
        
        # Set Poppler path for pdf2image
        self.poppler_path = self._find_poppler_path()
    
    def _find_poppler_path(self) -> Optional[str]:
        """Find Poppler installation"""
        possible_paths = [
            r'/tmp/poppler/poppler-24.08.0/Library/bin',
            r'C:\Program Files\poppler\Library\bin',
            r'C:\poppler\Library\bin',
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                logger.info(f"Found Poppler at: {path}")
                return path
        
        logger.warning("Poppler not found, pdf2image may fail")
        return None
    
    def extract_from_pdf(self, pdf_bytes: bytes, dpi: int = 300) -> str:
        """
        Extract text from PDF using Tesseract OCR.
        
        Args:
            pdf_bytes: PDF file as bytes
            dpi: Resolution for PDF to image conversion (higher = better quality)
            
        Returns:
            Extracted text
        """
        try:
            logger.info("Converting PDF to images for Tesseract OCR...")
            
            # Convert PDF pages to images
            convert_kwargs = {
                'pdf_bytes': pdf_bytes,
                'dpi': dpi,
                'fmt': 'png'
            }
            
            if self.poppler_path:
                convert_kwargs['poppler_path'] = self.poppler_path
            
            images = convert_from_bytes(**convert_kwargs)
            
            logger.info(f"Processing {len(images)} pages with Tesseract OCR")
            
            text_parts = []
            for i, image in enumerate(images):
                logger.info(f"OCR processing page {i+1}/{len(images)}")
                
                # Preprocess image for better OCR
                processed_image = self._preprocess_image(image)
                
                # Run Tesseract OCR
                page_text = pytesseract.image_to_string(
                    processed_image,
                    config='--psm 6'  # Assume uniform text block
                )
                
                if page_text.strip():
                    text_parts.append(page_text)
                    logger.info(f"Page {i+1}: Extracted {len(page_text)} characters")
                else:
                    logger.warning(f"Page {i+1}: No text extracted")
            
            full_text = "\n\n--- PAGE BREAK ---\n\n".join(text_parts)
            logger.info(f"Tesseract OCR complete: {len(full_text)} total characters from {len(text_parts)} pages")
            
            return full_text
            
        except Exception as e:
            logger.error(f"Tesseract OCR failed: {e}", exc_info=True)
            raise ValueError(f"Failed to extract text with Tesseract: {str(e)}")
    
    def _preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image to improve OCR accuracy.
        
        Techniques:
        - Convert to grayscale
        - Increase contrast
        - Increase sharpness
        
        Args:
            image: PIL Image
            
        Returns:
            Preprocessed image
        """
        try:
            # Convert to grayscale
            image = image.convert('L')
            
            # Increase contrast
            enhancer = ImageEnhance.Contrast(image)
            image = enhancer.enhance(2.0)
            
            # Increase sharpness
            enhancer = ImageEnhance.Sharpness(image)
            image = enhancer.enhance(1.5)
            
            return image
        except Exception as e:
            logger.warning(f"Image preprocessing failed: {e}, using original")
            return image
    
    def get_confidence(self, pdf_bytes: bytes) -> float:
        """
        Get OCR confidence score for first page.
        
        Args:
            pdf_bytes: PDF file bytes
            
        Returns:
            Confidence score 0-100
        """
        try:
            convert_kwargs = {
                'pdf_bytes': pdf_bytes,
                'dpi': 150,
                'last_page': 1
            }
            
            if self.poppler_path:
                convert_kwargs['poppler_path'] = self.poppler_path
            
            images = convert_from_bytes(**convert_kwargs)
            
            if not images:
                return 0.0
            
            # Get detailed OCR data with confidence
            data = pytesseract.image_to_data(
                images[0], 
                output_type=pytesseract.Output.DICT
            )
            
            # Calculate average confidence
            confidences = [c for c in data['conf'] if c != -1]
            if confidences:
                avg_confidence = sum(confidences) / len(confidences)
                logger.info(f"Tesseract confidence: {avg_confidence:.1f}%")
                return avg_confidence
            
            return 0.0
            
        except Exception as e:
            logger.error(f"Confidence check failed: {e}")
            return 0.0
    
    def extract_from_image(self, image_bytes: bytes) -> str:
        """
        Extract text from a single image.
        
        Args:
            image_bytes: Image file as bytes
            
        Returns:
            Extracted text
        """
        try:
            image = Image.open(io.BytesIO(image_bytes))
            processed_image = self._preprocess_image(image)
            
            text = pytesseract.image_to_string(
                processed_image,
                config='--psm 6'
            )
            
            logger.info(f"Extracted {len(text)} characters from image")
            return text
            
        except Exception as e:
            logger.error(f"Image OCR failed: {e}")
            raise ValueError(f"Failed to extract text from image: {str(e)}")
