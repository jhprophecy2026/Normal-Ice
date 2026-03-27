"""
OCR Strategy implementations for different document types
"""
from .image_based import TesseractOCR
from .quality_checker import TextQualityChecker

__all__ = ['TesseractOCR', 'TextQualityChecker']
