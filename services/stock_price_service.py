"""
Service for fetching real-time stock prices from Yahoo Finance.
Indonesian stocks use the .JK suffix (Jakarta Stock Exchange).
"""
import yfinance as yf
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class StockPriceService:
    """Fetch current stock price data from Yahoo Finance."""

    @staticmethod
    def _to_yahoo_ticker(ticker: str) -> str:
        """
        Convert IDX ticker to Yahoo Finance format.
        e.g., 'BBCA' -> 'BBCA.JK'
        """
        ticker = ticker.upper().strip()
        if not ticker.endswith(".JK"):
            ticker = f"{ticker}.JK"
        return ticker

    def get_current_price(self, ticker: str) -> Optional[dict]:
        """
        Fetch the current stock price and key info from Yahoo Finance.

        Args:
            ticker: IDX stock ticker (e.g., 'BBCA')

        Returns:
            dict with stock_price, name, previous_close, etc. or None if not found.
        """
        yahoo_ticker = self._to_yahoo_ticker(ticker)

        try:
            stock = yf.Ticker(yahoo_ticker)
            info = stock.info

            # Yahoo Finance may return empty info for invalid tickers
            if not info or info.get("trailingPegRatio") is None and info.get("currentPrice") is None:
                # Fallback: try getting price from recent history
                hist = stock.history(period="5d")
                if hist.empty:
                    logger.warning(f"Ticker '{yahoo_ticker}' not found on Yahoo Finance.")
                    return None

                # Use the latest closing price from history
                latest = hist.iloc[-1]
                return {
                    "ticker": ticker.upper().replace(".JK", ""),
                    "name": info.get("shortName") or info.get("longName") or ticker.upper(),
                    "stock_price": float(latest["Close"]),
                    "previous_close": float(hist.iloc[-2]["Close"]) if len(hist) > 1 else 0,
                    "open_price": float(latest["Open"]),
                    "high": float(latest["High"]),
                    "low": float(latest["Low"]),
                    "volume": int(latest["Volume"]),
                    "source": "yahoo_finance",
                }

            current_price = (
                info.get("currentPrice")
                or info.get("regularMarketPrice")
                or info.get("previousClose")
                or 0
            )

            return {
                "ticker": ticker.upper().replace(".JK", ""),
                "name": info.get("shortName") or info.get("longName") or ticker.upper(),
                "stock_price": float(current_price),
                "previous_close": float(info.get("previousClose", 0)),
                "open_price": float(info.get("open") or info.get("regularMarketOpen", 0)),
                "high": float(info.get("dayHigh") or info.get("regularMarketDayHigh", 0)),
                "low": float(info.get("dayLow") or info.get("regularMarketDayLow", 0)),
                "volume": int(info.get("volume") or info.get("regularMarketVolume", 0)),
                "market_cap": info.get("marketCap"),
                "shares_outstanding": info.get("sharesOutstanding"),
                "source": "yahoo_finance",
            }

        except Exception as e:
            logger.error(f"Failed to fetch stock price for '{yahoo_ticker}' from Yahoo Finance: {e}")
            return None
