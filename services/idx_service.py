import requests
import logging

logger = logging.getLogger(__name__)

class IDXService:
    def __init__(self):
        self.base_url = "https://www.idx.co.id/primary/backend/api"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.idx.co.id/"
        }

    def get_all_emiten(self) -> list[dict]:
        """
        Mengambil semua data emiten (perusahaan tercatat) dari API IDX.
        Mengembalikan list of dictionaries containing ticker dan name.
        """
        url = f"{self.base_url}/company/profiles"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            
            # API biasanya mengembalikan json yang di dalamnya ada key 'data'
            items = data.get('data', [])
            
            emiten_list = []
            for item in items:
                ticker = item.get('IssuerCode', item.get('Symbol', item.get('Ticker'))) 
                # Menangani berbagai kemungkinan key dari IDX API
                name = item.get('IssuerName', item.get('Name', item.get('CompanyName')))
                
                if ticker and name:
                    emiten_list.append({
                        "ticker": ticker,
                        "name": name
                    })
            
            # Jika API company/profiles kosong, ada API Emiten lain
            if not emiten_list:
                # Alternative URL
                url_alt = "https://www.idx.co.id/primary/backend/api/Emiten/GetEmiten"
                resp_alt = requests.get(url_alt, headers=self.headers)
                if resp_alt.status_code == 200:
                    data_alt = resp_alt.json()
                    for item in data_alt.get('data', []):
                        ticker = item.get('KodeEmiten', item.get('IssuerCode'))
                        name = item.get('NamaEmiten', item.get('IssuerName'))
                        if ticker and name:
                            emiten_list.append({"ticker": ticker, "name": name})
                            
            logger.info(f"Berhasil mengambil {len(emiten_list)} emiten dari IDX.")
            return emiten_list
            
        except Exception as e:
            logger.error(f"Gagal mengambil data emiten dari IDX: {e}")
            return []
