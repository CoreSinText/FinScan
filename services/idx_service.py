import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging
import os
import time
from urllib.parse import quote

logger = logging.getLogger(__name__)

# Constants
REPORT_TYPES = ["rdf", "rda"]       # rdf = Laporan Keuangan, rda = Laporan Tahunan
PERIODS = ["tw1", "tw2", "tw3", "audit"]
YEARS = list(range(2022, 2027))      # 2022 - 2026
EMITEN_TYPE = "s"                    # s = Saham
PAGE_SIZE = 100


class IDXService:
    def __init__(self):
        self.base_url = "https://www.idx.co.id/primary/ListedCompany"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/laporan-keuangan-dan-tahunan/",
            "X-Requested-With": "XMLHttpRequest"
        }
        # Session with retry logic
        self.session = requests.Session()
        retries = Retry(total=3, backoff_factor=2, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retries))
        self.session.headers.update(self.headers)

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

    def get_financial_reports(
        self,
        report_type: str = "rdf",
        year: int = 2024,
        period: str = "audit",
    ) -> list[dict]:
        """
        Fetch financial report metadata from IDX for a given report_type, year, and period.
        Handles pagination automatically.
        Returns a flat list of attachment dicts with emiten info.
        """
        url = f"{self.base_url}/GetFinancialReport"
        all_attachments = []
        index_from = 1

        try:
            while True:
                params = {
                    "reportType": report_type,
                    "year": str(year),
                    "periode": period,
                    "EmitenType": EMITEN_TYPE,
                    "indexFrom": index_from,
                    "pageSize": PAGE_SIZE,
                }

                response = self.session.get(url, params=params, timeout=60)
                response.raise_for_status()
                data = response.json()

                total = data.get("ResultCount", 0)
                results = data.get("Results", [])

                if not results:
                    break

                for emiten_result in results:
                    ticker = emiten_result.get("KodeEmiten", "")
                    name = emiten_result.get("NamaEmiten", "")

                    for att in emiten_result.get("Attachments", []):
                        all_attachments.append({
                            "ticker": ticker,
                            "name": name,
                            "file_id": att.get("File_ID", ""),
                            "file_name": att.get("File_Name", ""),
                            "file_path": att.get("File_Path", ""),
                            "file_type": att.get("File_Type", ""),
                            "file_size": att.get("File_Size", 0),
                            "report_type": report_type,
                            "year": year,
                            "period": period,
                        })

                index_from += PAGE_SIZE
                if index_from > total:
                    break

                # Rate limiting
                time.sleep(0.3)

            logger.info(
                f"Fetched {len(all_attachments)} attachments for "
                f"reportType={report_type}, year={year}, period={period}"
            )
            return all_attachments

        except Exception as e:
            logger.error(
                f"Failed to fetch financial reports "
                f"(reportType={report_type}, year={year}, period={period}): {e}"
            )
            return []

    def get_all_financial_reports(self) -> list[dict]:
        """
        Fetch ALL financial report metadata across all years, periods, and report types.
        Iterates: years (2022-2026) x periods (tw1,tw2,tw3,audit) x report_types (rdf,rda).
        """
        all_reports = []

        for report_type in REPORT_TYPES:
            for year in YEARS:
                for period in PERIODS:
                    logger.info(f"Fetching reports: type={report_type}, year={year}, period={period}")
                    reports = self.get_financial_reports(
                        report_type=report_type,
                        year=year,
                        period=period,
                    )
                    all_reports.extend(reports)
                    time.sleep(0.5)  # Rate limiting between combinations

        logger.info(f"Total report attachments fetched: {len(all_reports)}")
        return all_reports

    def download_file(self, file_path: str, save_dir: str) -> str | None:
        """
        Download a single file from IDX given its file_path.
        Returns the local file path if successful, None otherwise.
        """
        download_url = f"https://www.idx.co.id{quote(file_path, safe='/:@')}"

        try:
            response = requests.get(download_url, headers=self.headers, stream=True, timeout=60)
            response.raise_for_status()

            # Extract filename from file_path
            file_name = os.path.basename(file_path)
            local_path = os.path.join(save_dir, file_name)

            os.makedirs(save_dir, exist_ok=True)

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded: {file_name}")
            return local_path

        except Exception as e:
            logger.error(f"Failed to download file from '{file_path}': {e}")
            return None
