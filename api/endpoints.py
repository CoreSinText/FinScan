from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from models.company import Company
from models.report import FinancialReport
from models.requests import PBVRequest
from models.responses import PBVResponse
from services.idx_service import IDXService
from services.llm_service import LLMService
from services.pdf_service import PDFService
from services.stock_price_service import StockPriceService
from core.calculator import calculate_bvps, calculate_pbv_ratio, get_pbv_status
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Directory where downloaded PDFs are stored
PDF_DOWNLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "pdf")


@router.post("/extract-ratios")
async def extract_financial_ratios():
    # TODO: Implement endpoint logic coordinating pdf parsing, LLM extraction, and calculation
    pass


@router.post("/emiten/scrape")
def scrape_emiten(db: Session = Depends(get_db)):
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


@router.get("/calculate/pbv/{ticker}", response_model=PBVResponse)
def calculate_pbv_auto(ticker: str, db: Session = Depends(get_db)):
    """
    Fully automated PBV calculation.

    User only provides the stock ticker (e.g., 'BBCA').
    Everything else is fetched automatically:
    - Stock price → from Yahoo Finance (realtime)
    - Listed shares → from Yahoo Finance or IDX as fallback
    - Total equity → extracted from the latest financial report PDF via LLM
    """
    ticker = ticker.upper()

    # Step 1: Fetch current stock price from Yahoo Finance
    stock_price_service = StockPriceService()
    yahoo_data = stock_price_service.get_current_price(ticker)

    if not yahoo_data:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker}' not found on Yahoo Finance. Make sure it's a valid IDX ticker."
        )

    stock_price = yahoo_data["stock_price"]
    company_name = yahoo_data["name"]

    if stock_price <= 0:
        raise HTTPException(status_code=400, detail="Stock price is 0 or unavailable.")

    # Get listed shares: prefer Yahoo Finance, fallback to IDX
    listed_shares = yahoo_data.get("shares_outstanding") or 0

    if listed_shares <= 0:
        # Fallback: try IDX trading summary for listed shares
        idx_service = IDXService()
        idx_data = idx_service.get_stock_data(ticker)
        if idx_data:
            listed_shares = idx_data.get("listed_shares", 0)

    if listed_shares <= 0:
        raise HTTPException(status_code=400, detail="Listed shares data is 0 or unavailable from both Yahoo Finance and IDX.")

    # Step 2: Find the company and its latest financial report in DB
    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        # Auto-create company record
        company = Company(ticker=ticker, name=company_name)
        db.add(company)
        db.flush()

    # Get the latest financial report (prefer 'rdf' = Laporan Keuangan, latest year, audit period)
    latest_report = (
        db.query(FinancialReport)
        .filter(
            FinancialReport.company_id == company.id,
            FinancialReport.report_type == "rdf",
            FinancialReport.file_name.like("%.pdf"),
        )
        .order_by(FinancialReport.year.desc(), FinancialReport.period.desc())
        .first()
    )

    if not latest_report:
        # Auto-scrape: fetch report metadata from IDX for this specific ticker
        idx_service = IDXService()
        ticker_reports = idx_service.get_financial_reports_for_ticker(ticker)

        if not ticker_reports:
            raise HTTPException(
                status_code=404,
                detail=f"No financial report found for '{ticker}' on IDX."
            )

        # Save them to DB and pick the best PDF
        for report in ticker_reports:
            file_id = report.get("file_id", "")
            if not file_id:
                continue
            existing = db.query(FinancialReport).filter(FinancialReport.file_id == file_id).first()
            if existing:
                continue
            new_report = FinancialReport(
                company_id=company.id,
                year=report["year"],
                period=report["period"],
                report_type=report["report_type"],
                file_id=file_id,
                file_name=report["file_name"],
                file_path=report["file_path"],
                file_type=report.get("file_type", ""),
                file_size=report.get("file_size", 0),
                is_downloaded=False,
            )
            db.add(new_report)

        db.commit()

        # Now query again for the best PDF report
        latest_report = (
            db.query(FinancialReport)
            .filter(
                FinancialReport.company_id == company.id,
                FinancialReport.report_type == "rdf",
                FinancialReport.file_name.like("%.pdf"),
            )
            .order_by(FinancialReport.year.desc(), FinancialReport.period.desc())
            .first()
        )

    if not latest_report:
        raise HTTPException(
            status_code=404,
            detail=f"No PDF financial report found for '{ticker}' after scraping IDX."
        )

    # Step 3: Download the PDF if not already downloaded
    if not latest_report.is_downloaded:
        idx_dl_service = IDXService()
        downloaded_path = idx_dl_service.download_file(latest_report.file_path, PDF_DOWNLOAD_DIR)
        if not downloaded_path:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to download financial report for '{ticker}'."
            )
        latest_report.is_downloaded = True
        db.commit()
        local_pdf_path = downloaded_path
    else:
        local_pdf_path = os.path.join(PDF_DOWNLOAD_DIR, os.path.basename(latest_report.file_path))

    if not os.path.exists(local_pdf_path):
        raise HTTPException(
            status_code=500,
            detail=f"Financial report PDF file not found at '{local_pdf_path}'."
        )

    # Step 4: Extract total equity from PDF using LLM
    pdf_service = PDFService(local_pdf_path)
    # Search for pages containing equity-related keywords
    extracted_text = pdf_service.extract_text_by_keywords([
        "total ekuitas", "total equity", "jumlah ekuitas",
        "laporan posisi keuangan", "balance sheet"
    ])

    if not extracted_text:
        # Fallback: try extracting from first 10 pages
        extracted_text = pdf_service.extract_text(start_page=0, end_page=10)

    if not extracted_text:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract text from financial report PDF for '{ticker}'."
        )

    llm_service = LLMService()
    total_equity = llm_service.extract_total_equity(extracted_text)

    if total_equity is None or total_equity <= 0:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to extract total equity from financial report for '{ticker}'. LLM could not find the value."
        )

    # Step 5: Calculate PBV
    try:
        bvps = calculate_bvps(total_equity, listed_shares)
        pbv = calculate_pbv_ratio(stock_price, bvps)
        status = get_pbv_status(pbv)

        return PBVResponse(
            ticker=ticker,
            name=company_name,
            stock_price=stock_price,
            listed_shares=listed_shares,
            total_equity=total_equity,
            bvps=round(bvps, 2),
            pbv=round(pbv, 2),
            status=status,
            report_source=f"{latest_report.report_type} / {latest_report.year} / {latest_report.period}"
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/calculate/pbv", response_model=PBVResponse)
def calculate_pbv_manual(request: PBVRequest):
    """
    Manual PBV calculation (fallback).

    User provides:
    - ticker: Stock ticker code (e.g., 'BBCA')
    - total_equity: Total equity from the financial report

    Stock price and listed shares are fetched automatically from Yahoo Finance.
    """
    ticker = request.ticker.upper()

    # Fetch current stock price from Yahoo Finance
    stock_price_service = StockPriceService()
    yahoo_data = stock_price_service.get_current_price(ticker)

    if not yahoo_data:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker}' not found on Yahoo Finance."
        )

    stock_price = yahoo_data["stock_price"]
    company_name = yahoo_data["name"]

    if stock_price <= 0:
        raise HTTPException(status_code=400, detail="Stock price is 0 or unavailable.")

    # Get listed shares: prefer Yahoo Finance, fallback to IDX
    listed_shares = yahoo_data.get("shares_outstanding") or 0

    if listed_shares <= 0:
        idx_service = IDXService()
        idx_data = idx_service.get_stock_data(ticker)
        if idx_data:
            listed_shares = idx_data.get("listed_shares", 0)

    if listed_shares <= 0:
        raise HTTPException(status_code=400, detail="Listed shares data is 0 or unavailable.")

    try:
        bvps = calculate_bvps(request.total_equity, listed_shares)
        pbv = calculate_pbv_ratio(stock_price, bvps)
        status = get_pbv_status(pbv)

        return PBVResponse(
            ticker=ticker,
            name=company_name,
            stock_price=stock_price,
            listed_shares=listed_shares,
            total_equity=request.total_equity,
            bvps=round(bvps, 2),
            pbv=round(pbv, 2),
            status=status
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/reports/scrape")
def scrape_financial_reports(db: Session = Depends(get_db)):
    """
    Scrape ALL financial report metadata from IDX across years 2022-2026,
    all periods (tw1, tw2, tw3, audit), and report types (rdf, rda).

    Stores file metadata in the `financial_report` table.
    Uses `file_id` (UUID from IDX) to prevent duplicate entries.
    Does NOT download the actual files — only indexes them.
    """
    idx_service = IDXService()
    all_reports = idx_service.get_all_financial_reports()
    

    if not all_reports:
        raise HTTPException(status_code=500, detail="Failed to fetch financial reports from IDX.")

    inserted = 0
    skipped = 0

    for report in all_reports:
        file_id = report.get("file_id", "")
        if not file_id:
            skipped += 1
            continue

        # Deduplication: check if this file_id already exists in the DB
        existing = db.query(FinancialReport).filter(FinancialReport.file_id == file_id).first()
        if existing:
            skipped += 1
            continue

        # Find the company in DB
        company = db.query(Company).filter(Company.ticker == report["ticker"]).first()
        if not company:
            # Auto-create company if not scraped yet
            company = Company(ticker=report["ticker"], name=report.get("name", ""))
            db.add(company)
            db.flush()  # Get the ID

        new_report = FinancialReport(
            company_id=company.id,
            year=report["year"],
            period=report["period"],
            report_type=report["report_type"],
            file_id=file_id,
            file_name=report["file_name"],
            file_path=report["file_path"],
            file_type=report.get("file_type", ""),
            file_size=report.get("file_size", 0),
            is_downloaded=False,
        )
        db.add(new_report)
        inserted += 1

    db.commit()

    return {
        "message": "Financial report scraping completed",
        "total_reports_found": len(all_reports),
        "inserted": inserted,
        "skipped_duplicates": skipped,
    }
