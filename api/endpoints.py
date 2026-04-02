"""
API endpoints for FinScan.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.company import Company
from services.idx_service import IDXService

router = APIRouter()


@router.post("/extract-ratios")
async def extract_financial_ratios():
    # TODO: Implement endpoint logic coordinating pdf parsing, LLM extraction, and calculation
    pass

@router.post("/emiten/scrape")
async def scrape_emiten(db: Session = Depends(get_db)):
    """
    Scarape all data from idx
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
        
        # Cek apakah emiten sudah ada
        company = db.query(Company).filter(Company.ticker == ticker).first()
        if company:
            # Update jika nama berubah
            if company.name != name:
                company.name = name
                updated += 1
        else:
            # Insert baru
            new_company = Company(ticker=ticker, name=name)
            db.add(new_company)
            inserted += 1
            
    db.commit()
    
    return {
        "message": "Scrapping done",
        "total_emiten_ditemukan": len(emiten_data),
        "inserted": inserted,
        "updated": updated
    }
