import urllib.parse
from playwright.sync_api import sync_playwright
import logging
import os
import time
import json
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
        self.user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

    def _fetch_json(self, url: str) -> dict:
        """Helper method to fetch JSON using Playwright to bypass Cloudflare."""
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page(user_agent=self.user_agent)
                page.set_extra_http_headers({"Accept": "application/json"})
                try:
                    page.goto(url, wait_until='commit', timeout=20000)
                    page.wait_for_timeout(5000) # Give cloudflare a moment to resolve properly
                except Exception:
                    pass
                
                body_text = page.locator("body").inner_text()
                data = json.loads(body_text)
                browser.close()
                return data
        except Exception as e:
            logger.error(f"Failed to fetch JSON from {url} via Playwright: {e}")
            return {}

    def get_all_emiten(self) -> list[dict]:
        """Fetch all listed company (emiten) data from the IDX API."""
        url = f"{self.base_url}/GetCompanyProfiles?length=9999&start=0"
        data = self._fetch_json(url)
        items = data.get("data", [])
        emiten_list = []
        for item in items:
            ticker = item.get("KodeEmiten")
            name = item.get("NamaEmiten")
            if ticker and name:
                emiten_list.append({"ticker": ticker, "name": name})
        logger.info(f"Successfully fetched {len(emiten_list)} emiten from IDX.")
        return emiten_list

    def get_stock_data(self, ticker: str) -> dict | None:
        """Fetch realtime stock trading data for a specific ticker."""
        url = "https://www.idx.co.id/primary/TradingSummary/GetStockSummary?length=9999&start=0"
        data = self._fetch_json(url)
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

    def get_financial_reports(
        self,
        report_type: str = "rdf",
        year: int = 2024,
        period: str = "audit",
    ) -> list[dict]:
        """Fetch financial report metadata automatically paginated."""
        all_attachments = []
        index_from = 1

        while True:
            url = f"{self.base_url}/GetFinancialReport?reportType={report_type}&year={year}&periode={period}&EmitenType={EMITEN_TYPE}&indexFrom={index_from}&pageSize={PAGE_SIZE}"
            data = self._fetch_json(url)
            
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
                
            time.sleep(1) # Add delay between pages

        logger.info(f"Fetched {len(all_attachments)} attachments for reportType={report_type}, year={year}, period={period}")
        return all_attachments

    def get_financial_reports_for_ticker(self, ticker: str) -> list[dict]:
        """Fetch financial report metadata for a specific ticker."""
        ticker = ticker.upper()
        ticker_reports = []

        # Optimization: use kodeEmiten param if possible, but IDX requires exact match filtering locally if the API doesn't support it perfectly
        # We can pass kodeEmiten directly to the endpoint to filter it on the server-side, which is much faster!
        
        # Search recent years first
        for year in [2025, 2024, 2023]:
            for period in ["audit", "tw3", "tw2", "tw1"]:
                url = f"{self.base_url}/GetFinancialReport?reportType=rdf&year={year}&periode={period}&EmitenType={EMITEN_TYPE}&kodeEmiten={ticker}&indexFrom=1&pageSize=5"
                data = self._fetch_json(url)
                
                results = data.get("Results", [])
                for emiten_result in results:
                    if emiten_result.get("KodeEmiten", "").upper() == ticker:
                        for att in emiten_result.get("Attachments", []):
                            ticker_reports.append({
                                "ticker": ticker,
                                "name": emiten_result.get("NamaEmiten", ""),
                                "file_id": att.get("File_ID", ""),
                                "file_name": att.get("File_Name", ""),
                                "file_path": att.get("File_Path", ""),
                                "file_type": att.get("File_Type", ""),
                                "file_size": att.get("File_Size", 0),
                                "report_type": "rdf",
                                "year": year,
                                "period": period,
                            })

                if ticker_reports:
                    logger.info(f"Found {len(ticker_reports)} reports for '{ticker}' in {year}/{period}")
                    return ticker_reports

                time.sleep(0.5)

        logger.warning(f"No financial reports found for ticker '{ticker}'")
        return ticker_reports

    def get_all_financial_reports(self) -> list[dict]:
        """Fetch ALL financial report metadata across all years, periods, and report types."""
        all_reports = []
        for report_type in REPORT_TYPES:
            for year in YEARS:
                for period in PERIODS:
                    reports = self.get_financial_reports(report_type, year, period)
                    all_reports.extend(reports)
        return all_reports

    def download_file(self, file_path: str, save_dir: str) -> str | None:
        """
        Download a single file from IDX. Uses Playwright to grab CloudFlare
        cookies seamlessly, and then streams the actual PDF using urllib.
        This avoids the Playwright 'download is starting' errors.
        """
        import urllib.request
        from urllib.parse import quote
        
        download_url = f"https://www.idx.co.id{quote(file_path, safe='/:@')}"
        file_name = os.path.basename(file_path)
        local_path = os.path.join(save_dir, file_name)
        
        os.makedirs(save_dir, exist_ok=True)
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()
                
                # Navigate to the base URL to bypass cloudflare and get cookies
                try:
                    page.goto("https://www.idx.co.id", wait_until='domcontentloaded', timeout=15000)
                    page.wait_for_timeout(3000)
                except Exception:
                    pass
                    
                cookies = context.cookies()
                browser.close()
                
            # Construct cookie header
            cookie_header = "; ".join([f"{c['name']}={c['value']}" for c in cookies])
            
            req = urllib.request.Request(download_url, headers={
                "User-Agent": self.user_agent,
                "Cookie": cookie_header,
                "Referer": "https://www.idx.co.id/"
            })
            
            with urllib.request.urlopen(req, timeout=30) as response, open(local_path, 'wb') as out_file:
                out_file.write(response.read())
                
            logger.info(f"Downloaded: {file_name}")
            return local_path
        except Exception as e:
            logger.error(f"Failed to download file from '{file_path}': {e}")
            return None
