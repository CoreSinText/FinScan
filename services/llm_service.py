import json
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class LLMService:
    def __init__(self, model_name: str = "llama3"):
        self.model_name = model_name
        self.api_url = "http://localhost:11434/api/generate"

    def extract_financial_data(self, text_content: str) -> Optional[Dict[str, Any]]:
        prompt = f"""
        Extract financial data from the following text to calculate PBV (Price to Book Value) and PE (Price to Earnings) ratios.
        Please return the result strictly in JSON format with the following keys:
        - "stock_price"
        - "book_value_per_share"
        - "earnings_per_share"
        - "aset_pajak_tangguhan"
        - "calculated_bvps"
        "
        If a value is not found, set it to null. Do not include any other text except the JSON.

        Text:
        {text_content}
        """

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            result_json = response.json()
            response_text = result_json.get("response", "{}")
            return json.loads(response_text)
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error occurred: {http_err}")
            logger.error(f"Response from Ollama: {http_err.response.text}")
            return None
        except Exception as e:
            logger.error(f"Error communicating with Ollama: {e}")
            return None

    def extract_total_equity(self, text_content: str) -> Optional[float]:
        """
        Extract total equity value from financial report text using LLM.
        Returns the total equity as a float, or None if extraction fails.
        """
        prompt = f"""
        From the following financial report text, extract the "Total Ekuitas" or "Total Equity" value.
        This is typically found in the Balance Sheet (Laporan Posisi Keuangan) section.
        Look for the line that says "Total ekuitas" or "Total equity" and extract the numeric value.

        IMPORTANT:
        - Return ONLY a JSON object with the key "total_equity" and the numeric value.
        - The value should be in the original unit (e.g., if stated in millions, return the full number).
        - If stated in "jutaan" (millions), multiply by 1,000,000.
        - If stated in "miliaran" (billions), multiply by 1,000,000,000.
        - If total equity is not found, return {{"total_equity": null}}.
        - Do NOT include any explanation, only the JSON.

        Example response: {{"total_equity": 250000000000}}

        Text:
        {text_content}
        """

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "format": "json"
        }

        try:
            response = requests.post(self.api_url, json=payload, timeout=120)
            response.raise_for_status()
            result_json = response.json()
            response_text = result_json.get("response", "{}")
            parsed = json.loads(response_text)
            total_equity = parsed.get("total_equity")
            if total_equity is not None:
                return float(total_equity)
            return None
        except requests.exceptions.HTTPError as http_err:
            logger.error(f"HTTP error extracting total equity: {http_err}")
            return None
        except Exception as e:
            logger.error(f"Error extracting total equity via LLM: {e}")
            return None
