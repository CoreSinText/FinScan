"""
Pydantic schemas for API response formatting.
"""
from pydantic import BaseModel
from typing import Optional


class PBVResponse(BaseModel):
    """Response body for PBV calculation."""
    ticker: str
    name: str
    stock_price: float
    listed_shares: float
    total_equity: float
    bvps: float   # Book Value Per Share
    pbv: float    # Price to Book Value ratio
    status: str   # e.g., "undervalued", "overvalued", "fair"
    report_source: Optional[str] = None  # e.g., "rdf / 2024 / audit"


class FinancialRatiosResponse(BaseModel):
    # TODO: Define response schema representing the extracted data and the calculated PE, PBV ratios
    pass
