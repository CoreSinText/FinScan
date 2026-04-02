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
