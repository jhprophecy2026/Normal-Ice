"""
Document splitting utilities for batch processing large medical reports
"""
import logging
from typing import List, Dict, Any
import re

logger = logging.getLogger(__name__)

class DocumentSplitter:
    """Split large multi-report documents into individual sections"""
    
    # Common report end markers
    END_MARKERS = [
        "********** END OF THE REPORT **********",
        "END OF THE REPORT",
        "END OF REPORT",
        "--- END ---",
    ]
    
    # Maximum characters per batch (to stay well under token limits)
    MAX_BATCH_SIZE = 15000  # ~3750 tokens, leaves room for response
    
    @classmethod
    def split_by_markers(cls, text: str) -> List[str]:
        """
        Split document by report end markers.
        
        Args:
            text: Full document text
            
        Returns:
            List of individual report texts
        """
        # Try each marker
        for marker in cls.END_MARKERS:
            if marker in text:
                parts = text.split(marker)
                # Filter out empty parts and clean
                reports = []
                for part in parts:
                    cleaned = part.strip()
                    if cleaned and len(cleaned) > 100:  # Minimum viable report size
                        reports.append(cleaned)
                
                if reports:
                    logger.info(f"Split document into {len(reports)} reports using marker: {marker}")
                    return reports
        
        # No markers found
        logger.warning("No report end markers found")
        return []
    
    @classmethod
    def split_by_page_breaks(cls, text: str, pages_per_batch: int = 3) -> List[str]:
        """
        Split by page breaks (form feed characters or page indicators).
        
        Args:
            text: Full document text
            pages_per_batch: Number of pages to include per batch
            
        Returns:
            List of batched sections
        """
        # Split by form feed or common page break patterns
        pages = re.split(r'\f|Page \d+ of \d+', text)
        pages = [p.strip() for p in pages if p.strip()]
        
        # Batch pages together
        batches = []
        for i in range(0, len(pages), pages_per_batch):
            batch = "\n\n".join(pages[i:i+pages_per_batch])
            if batch:
                batches.append(batch)
        
        logger.info(f"Split document into {len(batches)} batches by page breaks")
        return batches
    
    @classmethod
    def split_by_size(cls, text: str, max_size: int = None) -> List[str]:
        """
        Split document by size to ensure each chunk fits in token limits.
        
        Args:
            text: Full document text
            max_size: Maximum characters per chunk
            
        Returns:
            List of text chunks
        """
        if max_size is None:
            max_size = cls.MAX_BATCH_SIZE
        
        if len(text) <= max_size:
            return [text]
        
        chunks = []
        current_chunk = ""
        
        # Split by paragraphs/sections to avoid breaking mid-sentence
        sections = text.split("\n\n")
        
        for section in sections:
            if len(current_chunk) + len(section) + 2 <= max_size:
                current_chunk += section + "\n\n"
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = section + "\n\n"
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        logger.info(f"Split document into {len(chunks)} chunks by size (max: {max_size} chars)")
        return chunks
    
    @classmethod
    def smart_split(cls, text: str) -> List[str]:
        """
        Intelligently split document using the best available method.
        
        Priority:
        1. Report end markers (most reliable)
        2. Size-based splitting (ensure token limits)
        
        Args:
            text: Full document text
            
        Returns:
            List of document sections ready for processing
        """
        logger.info(f"Smart splitting document of {len(text)} characters")
        
        # Try marker-based splitting first
        reports = cls.split_by_markers(text)
        
        if reports:
            # Check if any individual report is too large
            final_reports = []
            for i, report in enumerate(reports):
                if len(report) > cls.MAX_BATCH_SIZE:
                    logger.warning(f"Report {i+1} is too large ({len(report)} chars), splitting further")
                    sub_chunks = cls.split_by_size(report)
                    final_reports.extend(sub_chunks)
                else:
                    final_reports.append(report)
            
            logger.info(f"Final split: {len(final_reports)} processable sections")
            return final_reports
        
        # Fallback: size-based splitting
        logger.info("No markers found, using size-based splitting")
        return cls.split_by_size(text)

def split_document(text: str, strategy: str = "smart") -> List[str]:
    """
    Main entry point for document splitting.
    
    Args:
        text: Document text to split
        strategy: Splitting strategy ("smart", "markers", "size", "pages")
        
    Returns:
        List of document sections
    """
    splitter = DocumentSplitter()
    
    if strategy == "smart":
        return splitter.smart_split(text)
    elif strategy == "markers":
        return splitter.split_by_markers(text)
    elif strategy == "size":
        return splitter.split_by_size(text)
    elif strategy == "pages":
        return splitter.split_by_page_breaks(text)
    else:
        logger.warning(f"Unknown strategy '{strategy}', using smart split")
        return splitter.smart_split(text)
