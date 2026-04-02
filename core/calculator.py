"""
Core business logic for financial calculations (PBV, PE ratios).
"""


def calculate_bvps(total_equity: float, total_shares_outstanding: float) -> float:
    """
    Calculate Book Value Per Share (BVPS).
    BVPS = Total Equity / Total Shares Outstanding
    """
    if total_shares_outstanding <= 0:
        raise ValueError("Total shares outstanding must be greater than 0.")
    return total_equity / total_shares_outstanding


def calculate_pbv_ratio(stock_price: float, bvps: float) -> float:
    """
    Calculate Price to Book Value (PBV) ratio.
    PBV = Stock Price / BVPS
    """
    if bvps <= 0:
        raise ValueError("BVPS must be greater than 0.")
    return stock_price / bvps


def get_pbv_status(pbv: float) -> str:
    """
    Determine valuation status based on PBV ratio.
    - PBV < 1: potentially undervalued
    - PBV == 1: fair value
    - PBV > 1: potentially overvalued
    """
    if pbv < 1:
        return "undervalued"
    elif pbv == 1:
        return "fair"
    else:
        return "overvalued"


def calculate_pe_ratio(stock_price: float, earnings_per_share: float) -> float:
    """
    Calculate Price to Earnings (PE) ratio.
    PE = Stock Price / Earnings Per Share (EPS)
    """
    if earnings_per_share <= 0:
        raise ValueError("EPS must be greater than 0.")
    return stock_price / earnings_per_share
