import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self, file_path: str):
        """
        Service for reading and extracting text from PDF files.
        """
        self.file_path = file_path

    def extract_text(self, start_page: int = 0, end_page: Optional[int] = None) -> str:
        """
        Extract text from a specific page range.
        start_page and end_page are 0-indexed (page 1 is 0).
        If end_page is not provided, it will read until the last page.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("Library 'PyMuPDF' is not installed. Please run 'pip install PyMuPDF'.")
            return ""

        text_content = ""
        try:
            with fitz.open(self.file_path) as doc:
                total_pages = len(doc)
                
                if end_page is None:
                    end_page = total_pages
                
                # Validate page range
                start_page = max(0, min(start_page, total_pages - 1))
                end_page = max(start_page + 1, min(end_page, total_pages))
                
                logger.info(f"Extracting text from '{self.file_path}' (Page {start_page+1} to {end_page})")
                
                for page_num in range(start_page, end_page):
                    page = doc.load_page(page_num)
                    # Using 'text' mode which extracts paragraph blocks naturally
                    text_content += f"--- PAGE {page_num + 1} ---\n"
                    text_content += page.get_text("text") + "\n\n"
                    
            return text_content
        except Exception as e:
            logger.error(f"Failed to read PDF file '{self.file_path}': {e}")
            return ""

    def extract_text_by_keywords(self, keywords: list) -> str:
        """
        Search for pages containing any of the given keywords (case-insensitive)
        and extract text only from those matching pages.
        """
        try:
            import fitz
        except ImportError:
            logger.error("Library 'PyMuPDF' is not installed.")
            return ""

        text_content = ""
        found_pages = []
        try:
            with fitz.open(self.file_path) as doc:
                keywords_lower = [k.lower() for k in keywords]
                
                logger.info(f"Searching for keywords {keywords} across all PDF pages...")
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    page_text = page.get_text("text").lower()
                    
                    if any(k in page_text for k in keywords_lower):
                        found_pages.append(page_num)
                
                if not found_pages:
                    logger.info(f"Keywords not found in PDF.")
                    return ""
                
                logger.info(f"Keywords found on pages: {[p+1 for p in found_pages]}")
                
                for page_num in found_pages:
                    page = doc.load_page(page_num)
                    text_content += f"--- PAGE {page_num + 1} ---\n"
                    text_content += page.get_text("text") + "\n\n"
                    
            return text_content
        except Exception as e:
            logger.error(f"Failed to extract text with keywords: {e}")
            return ""
