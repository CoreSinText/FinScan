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
        Fetch all listed company (emiten) data from the IDX API.
        Returns a list of dictionaries containing ticker and name.
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

            logger.info(f"Successfully fetched {len(emiten_list)} emiten from IDX.")
            return emiten_list

        except Exception as e:
            logger.error(f"Failed to fetch emiten data from IDX: {e}")
            return []

    def get_stock_data(self, ticker: str) -> dict | None:
        """
        Fetch realtime stock trading data for a specific ticker.
        Returns stock_price (Close), listed_shares, and other trading info.
        """
        url = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary"
        params = {
            "length": 9999,
            "start": 0,
        }

        try:
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            items = data.get("data", [])

            for item in items:
                if item.get("StockCode") == ticker.upper():
                    return {
                        "ticker": item["StockCode"],
                        "name": item.get("StockName", ""),
                        "stock_price": item.get("Close", 0),
                        "listed_shares": item.get("ListedShares", 0),
                        "previous": item.get("Previous", 0),
                        "open_price": item.get("OpenPrice", 0),
                        "high": item.get("High", 0),
                        "low": item.get("Low", 0),
                        "volume": item.get("Volume", 0),
                        "date": item.get("Date", ""),
                    }

            logger.warning(f"Ticker '{ticker}' not found in IDX trading data.")
            return None

        except Exception as e:
            logger.error(f"Failed to fetch stock data for '{ticker}': {e}")
            return None
