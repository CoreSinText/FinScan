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
