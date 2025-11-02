"""
PDF text extraction with OCR fallback
"""
import io
from typing import List, Dict
from PyPDF2 import PdfReader
import pytesseract
from pdf2image import convert_from_path
from PIL import Image

from app.logger import logger


def extract_pdf_pages(pdf_path: str, ocr_fallback: bool = True) -> List[Dict]:
    """
    Extract text from PDF file, returning list of page dicts
    
    Args:
        pdf_path: Path to PDF file
        ocr_fallback: Whether to use OCR if PyPDF2 extraction is insufficient
        
    Returns:
        List of dicts with structure: {"page_no": int, "text": str}
    """
    pages = []
    
    try:
        # Try PyPDF2 first (faster)
        with open(pdf_path, 'rb') as f:
            reader = PdfReader(f)
            
            for page_no, page in enumerate(reader.pages, 1):
                page_text = page.extract_text() or ""
                pages.append({
                    "page_no": page_no,
                    "text": page_text
                })
        
        # Check if extraction was successful
        total_text = "".join(p["text"] for p in pages)
        
        if total_text.strip() and len(total_text.strip()) > 100:
            logger.info(f"Extracted {len(pages)} pages from {pdf_path} using PyPDF2")
            return pages
        
        # Fallback to OCR if text is insufficient
        if ocr_fallback:
            logger.warning(f"PyPDF2 extraction insufficient for {pdf_path}, using OCR")
            pages = _extract_with_ocr(pdf_path)
            logger.info(f"Extracted {len(pages)} pages from {pdf_path} using OCR")
            return pages
        
        logger.warning(f"Minimal text extracted from {pdf_path}")
        return pages
        
    except Exception as e:
        logger.error(f"Error extracting text from {pdf_path}: {e}", exc_info=True)
        raise


def _extract_with_ocr(pdf_path: str) -> List[Dict]:
    """Extract text using OCR (Tesseract)"""
    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path)
        
        pages = []
        for page_no, image in enumerate(images, 1):
            # Run OCR on each page
            page_text = pytesseract.image_to_string(image)
            pages.append({
                "page_no": page_no,
                "text": page_text
            })
            logger.debug(f"OCR page {page_no}: {len(page_text)} chars")
        
        return pages
        
    except Exception as e:
        logger.error(f"OCR extraction failed: {e}", exc_info=True)
        raise


class PDFExtractor:
    """Extract text from PDF with OCR fallback (Legacy class for backward compatibility)"""
    
    def __init__(self, ocr_fallback: bool = True):
        self.ocr_fallback = ocr_fallback
    
    async def extract_text(self, pdf_bytes: bytes, filename: str) -> str:
        """
        Extract text from PDF bytes
        
        Args:
            pdf_bytes: PDF file content
            filename: Original filename for logging
            
        Returns:
            Extracted text
        """
        try:
            # Try PyPDF2 first (faster)
            text = self._extract_with_pypdf(pdf_bytes)
            
            if text and len(text.strip()) > 50:
                logger.info(f"Extracted {len(text)} chars from {filename} using PyPDF2")
                return text
            
            logger.warning(f"Minimal text extracted from {filename}")
            return text or ""
            
        except Exception as e:
            logger.error(f"Error extracting text from {filename}: {e}")
            raise
    
    def _extract_with_pypdf(self, pdf_bytes: bytes) -> str:
        """Extract text using PyPDF2"""
        try:
            pdf_file = io.BytesIO(pdf_bytes)
            reader = PdfReader(pdf_file)
            
            text_parts = []
            for page_num, page in enumerate(reader.pages, 1):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"PyPDF2 extraction failed: {e}")
            return ""