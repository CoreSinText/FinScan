"""
Pydantic schemas for API request validation.
"""
from pydantic import BaseModel, Field
from typing import Optional


class PBVRequest(BaseModel):
    """Request body for PBV calculation. Only ticker and total_equity needed."""
    ticker: str = Field(..., description="Stock ticker code (e.g., 'BBCA')")
    total_equity: float = Field(..., description="Total equity from the financial report")


class RatioExtractionRequest(BaseModel):
    # TODO: Define request schema (e.g., file upload metadata or PDF URL)
    pass
