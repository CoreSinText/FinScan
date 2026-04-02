"""
API endpoints for FinScan.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.company import Company
from models.requests import PBVRequest
from models.responses import PBVResponse
from services.idx_service import IDXService
from core.calculator import calculate_bvps, calculate_pbv_ratio, get_pbv_status

router = APIRouter()


@router.post("/extract-ratios")
async def extract_financial_ratios():
    # TODO: Implement endpoint logic coordinating pdf parsing, LLM extraction, and calculation
    pass

@router.post("/emiten/scrape")
async def scrape_emiten(db: Session = Depends(get_db)):
    """
    Scrape all listed company (emiten) data from IDX and save/update to the database.
    """
    idx_service = IDXService()
    emiten_data = idx_service.get_all_emiten()
    
    if not emiten_data:
        raise HTTPException(status_code=500, detail="Failed to scrape emiten data from IDX.")
        
    inserted = 0
    updated = 0
    
    for item in emiten_data:
        ticker = item['ticker']
        name = item['name']
        
        # Check if emiten already exists
        company = db.query(Company).filter(Company.ticker == ticker).first()
        if company:
            # Update if name has changed
            if company.name != name:
                company.name = name
                updated += 1
        else:
            # Insert new record
            new_company = Company(ticker=ticker, name=name)
            db.add(new_company)
            inserted += 1
            
    db.commit()
    
    return {
        "message": "Scraping completed",
        "total_emiten_found": len(emiten_data),
        "inserted": inserted,
        "updated": updated
    }


@router.post("/calculate/pbv", response_model=PBVResponse)
async def calculate_pbv(request: PBVRequest):
    """
    Calculate Price to Book Value (PBV) ratio.
    
    User only provides:
    - ticker: Stock ticker code (e.g., 'BBCA')
    - total_equity: Total equity from the financial report
    
    Stock price and listed shares are fetched automatically from IDX realtime data.
    """
    # Fetch realtime stock data from IDX
    idx_service = IDXService()
    stock_data = idx_service.get_stock_data(request.ticker)
    
    if not stock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{request.ticker}' not found in IDX trading data."
        )
    
    stock_price = stock_data["stock_price"]
    listed_shares = stock_data["listed_shares"]
    
    if stock_price <= 0:
        raise HTTPException(status_code=400, detail="Stock price is 0 or unavailable.")
    if listed_shares <= 0:
        raise HTTPException(status_code=400, detail="Listed shares data is 0 or unavailable.")
    
    try:
        bvps = calculate_bvps(request.total_equity, listed_shares)
        pbv = calculate_pbv_ratio(stock_price, bvps)
        status = get_pbv_status(pbv)
        
        return PBVResponse(
            ticker=stock_data["ticker"],
            name=stock_data["name"],
            stock_price=stock_price,
            listed_shares=listed_shares,
            total_equity=request.total_equity,
            bvps=round(bvps, 2),
            pbv=round(pbv, 2),
            status=status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

