import os
import json
from urllib.parse import quote
from playwright.sync_api import sync_playwright

def download_tw1_reports():
    url = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport?indexFrom=1&pageSize=12&year=2025&reportType=rdf&EmitenType=s&periode=tw1&kodeEmiten=&SortColumn=KodeEmiten&SortOrder=asc"
    
    save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pdf")
    os.makedirs(save_dir, exist_ok=True)
    
    print(f"Fetching JSON metadata from: {url}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page.set_extra_http_headers({"Accept": "application/json"})
        
        try:
            # We use 'commit' to not wait for all resources. Cloudflare challenges 
            # or long background scripts can cause domcontentloaded or networkidle to timeout.
            page.goto(url, wait_until="commit", timeout=15000)
            page.wait_for_timeout(5000) # give cloudflare a moment to resolve
        except Exception as e:
            # It's completely normal for it to timeout, the content might still be there!
            pass
        page.wait_for_timeout(2000) # give cloudflare a moment
        
        body_text = page.locator("body").inner_text()
        try:
            data = json.loads(body_text)
        except json.JSONDecodeError as e:
            print(f"Failed to parse JSON. Might be blocked. Content: {body_text[:200]}")
            browser.close()
            return

        results = data.get("Results", [])
        print(f"Found {len(results)} companies matching.")
        
        for result in results:
            ticker = result.get("KodeEmiten")
            for att in result.get("Attachments", []):
                file_path = att.get("File_Path")
                if not file_path:
                    continue
                    
                download_url = f"https://www.idx.co.id{quote(file_path, safe='/:@')}"
                file_name = os.path.basename(file_path)
                local_path = os.path.join(save_dir, file_name)
                
                print(f"Downloading {ticker}: {file_name} ...")
                try:
                    with page.expect_download(timeout=60000) as download_info:
                        # Ignore the goto exception since triggering a download often interrupts normal navigation
                        try:
                            page.goto(download_url)
                        except Exception:
                            pass
                    download = download_info.value
                    download.save_as(local_path)
                    print(f" [OK] Saved to {local_path}")
                except Exception as e:
                    print(f" [ERR] Failed: {e}")
                    
        browser.close()

if __name__ == "__main__":
    download_tw1_reports()
