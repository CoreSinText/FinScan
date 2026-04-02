import requests
import logging

logger = logging.getLogger(__name__)

class IDXService:
    def __init__(self):
        self.base_url = "https://www.idx.co.id/primary/ListedCompany"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/",
            "X-Requested-With": "XMLHttpRequest"
        }

    def get_all_emiten(self) -> list[dict]:
        """
        Mengambil semua data emiten (perusahaan tercatat) dari API IDX.
        Mengembalikan list of dictionaries containing ticker dan name.
        """
        url = f"{self.base_url}/GetCompanyProfiles"
        params = {
            "length": 9999,
            "start": 0,
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get("data", [])

            emiten_list = []
            for item in items:
                ticker = item.get("KodeEmiten")
                name = item.get("NamaEmiten")

                if ticker and name:
                    emiten_list.append({
                        "ticker": ticker,
                        "name": name
                    })

            logger.info(f"Berhasil mengambil {len(emiten_list)} emiten dari IDX.")
            return emiten_list

        except Exception as e:
            logger.error(f"Gagal mengambil data emiten dari IDX: {e}")
            return []
