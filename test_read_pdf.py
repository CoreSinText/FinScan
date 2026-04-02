from services.pdf_service import PDFService
from services.llm_service import LLMService

def main():
    # Lokasi file PDF Anda
    pdf_path = "data/pdf/FinancialStatement-2025-III-ASLC.pdf"
    
    print(f"Tahap 1: Membaca isi file {pdf_path}...")
    # Inisialisasi PDF Service
    pdf_service = PDFService(pdf_path)
    
    # Alih-alih membaca puluhan/ratusan halaman, kita gunakan filter pencarian kata kunci.
    # Misalnya kita cari halaman yang mengandung "aset pajak tangguhan"
    keywords = ["aset pajak tangguhan"]
    text_content = pdf_service.extract_text_by_keywords(keywords=keywords)
    
    if not text_content:
        print(f"Gagal menemukan teks dengan kata kunci {keywords} atau file PDF kosong.")
        return
        
    print(f"Berhasil mengumpulkan teks hasil pencarian sebanyak {len(text_content)} karakter.")
    print("--------------------------------------------------")
    print("Tahap 2: Menyiapkan ekstraksi data ke Model LLM (Ollama)...\n")
    
    llm = LLMService(model_name="llama3") # Ubah sesuai format nama model Ollama Anda
    
    # Catatan: Jika text_content sangat panjang, bisa jadi butuh waktu yang lama 
    # untuk Ollama merespon, atau bahkan melebihi context limit dari model yg berjalan lokal.
    result = llm.extract_financial_data(text_content)
    
    if result:
        print("\n=== HASIL EKSTRAKSI ===")
        print(result)
        # Tahap selanjutnya (Opsional): Anda bisa meneruskannya ke core.calculator untuk dihitung rasionya.
    else:
        print("\nGagal mengekstrak data JSON dari LLM.")

if __name__ == "__main__":
    main()
