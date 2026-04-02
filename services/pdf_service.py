import logging
from typing import Optional

logger = logging.getLogger(__name__)

class PDFService:
    def __init__(self, file_path: str):
        """
        Service untuk membaca dan mengekstrak teks dari file PDF.
        """
        self.file_path = file_path

    def extract_text(self, start_page: int = 0, end_page: Optional[int] = None) -> str:
        """
        Mengekstrak teks dari rentang halaman tertentu.
        start_page dan end_page bersifat 0-indexed (halaman 1 adalah 0).
        Jika end_page tidak diisi, akan membaca sampai halaman terakhir.
        """
        try:
            import fitz  # PyMuPDF
        except ImportError:
            logger.error("Library 'PyMuPDF' belum diinstall. Silakan jalankan 'pip install PyMuPDF'.")
            return ""

        text_content = ""
        try:
            with fitz.open(self.file_path) as doc:
                total_pages = len(doc)
                
                if end_page is None:
                    end_page = total_pages
                
                # Validasi range halaman
                start_page = max(0, min(start_page, total_pages - 1))
                end_page = max(start_page + 1, min(end_page, total_pages))
                
                logger.info(f"Mengekstrak baris teks dari '{self.file_path}' (Halaman {start_page+1} hingga {end_page})")
                
                for page_num in range(start_page, end_page):
                    page = doc.load_page(page_num)
                    # Menggunakan mode 'text' yang mengekstrak blok paragraf secara natural
                    text_content += f"--- HALAMAN {page_num + 1} ---\n"
                    text_content += page.get_text("text") + "\n\n"
                    
            return text_content
        except Exception as e:
            logger.error(f"Gagal membaca file PDF '{self.file_path}': {e}")
            return ""

    def extract_text_by_keywords(self, keywords: list) -> str:
        """
        Mencari halaman yang mengandung salah satu kata kunci (case-insensitive)
        Lalu mengekstrak teks hanya dari halaman yang ditemukan tersebut.
        """
        try:
            import fitz
        except ImportError:
            logger.error("Library 'PyMuPDF' belum diinstall.")
            return ""

        text_content = ""
        found_pages = []
        try:
            with fitz.open(self.file_path) as doc:
                keywords_lower = [k.lower() for k in keywords]
                
                logger.info(f"Mencari kata kunci {keywords} di seluruh halaman PDF...")
                for page_num in range(len(doc)):
                    page = doc.load_page(page_num)
                    page_text = page.get_text("text").lower()
                    
                    if any(k in page_text for k in keywords_lower):
                        found_pages.append(page_num)
                
                if not found_pages:
                    logger.info(f"Kata kunci tidak ditemukan di PDF.")
                    return ""
                
                logger.info(f"Kata kunci ditemukan pada halaman: {[p+1 for p in found_pages]}")
                
                for page_num in found_pages:
                    page = doc.load_page(page_num)
                    text_content += f"--- HALAMAN {page_num + 1} ---\n"
                    text_content += page.get_text("text") + "\n\n"
                    
            return text_content
        except Exception as e:
            logger.error(f"Gagal mengekstrak teks dengan keyword: {e}")
            return ""
