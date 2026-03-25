"""
API endpoints for FinScan.
"""
from fastapi import APIRouter

router = APIRouter()

@router.post("/extract-ratios")
async def extract_financial_ratios():
    # TODO: Implement endpoint logic coordinating pdf parsing, LLM extraction, and calculation
    pass
