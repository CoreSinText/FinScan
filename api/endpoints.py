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


@router.get("/calculate/pbv/{ticker}", response_model=PBVResponse)
async def calculate_pbv_auto(ticker: str, db: Session = Depends(get_db)):
    """
    Fully automated PBV calculation.

    User only provides the stock ticker (e.g., 'BBCA').
    Everything else is fetched automatically:
    - Stock price & listed shares → from IDX realtime trading data
    - Total equity → extracted from the latest financial report PDF via LLM
    """
    ticker = ticker.upper()

    # Step 1: Fetch realtime stock data from IDX
    idx_service = IDXService()
    stock_data = idx_service.get_stock_data(ticker)

    if not stock_data:
        raise HTTPException(
            status_code=404,
            detail=f"Ticker '{ticker}' not found in IDX trading data."
        )

    stock_price = stock_data["stock_price"]
    listed_shares = stock_data["listed_shares"]

    if stock_price <= 0:
        raise HTTPException(status_code=400, detail="Stock price is 0 or unavailable.")
    if listed_shares <= 0:
        raise HTTPException(status_code=400, detail="Listed shares data is 0 or unavailable.")

    # Step 2: Find the company and its latest financial report in DB
    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        raise HTTPException(
            status_code=404,
            detail=f"Company '{ticker}' not found in database. Run /emiten/scrape and /reports/scrape first."
        )

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
        raise HTTPException(
            status_code=404,
            detail=f"No financial report (PDF) found for '{ticker}'. Run /reports/scrape first."
        )

    # Step 3: Download the PDF if not already downloaded
    if not latest_report.is_downloaded:
        downloaded_path = idx_service.download_file(latest_report.file_path, PDF_DOWNLOAD_DIR)
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
            ticker=stock_data["ticker"],
            name=stock_data["name"],
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
async def calculate_pbv_manual(request: PBVRequest):
    """
    Manual PBV calculation (fallback).

    User provides:
    - ticker: Stock ticker code (e.g., 'BBCA')
    - total_equity: Total equity from the financial report

    Stock price and listed shares are fetched automatically from IDX realtime data.
    """
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


@router.post("/reports/scrape")
async def scrape_financial_reports(db: Session = Depends(get_db)):
    """
    Scrape ALL financial report metadata from IDX across years 2022-2026,
    all periods (tw1, tw2, tw3, audit), and report types (rdf, rda).

    Stores file metadata in the `financial_report` table.
    Uses `file_id` (UUID from IDX) to prevent duplicate entries.
    Does NOT download the actual files — only indexes them.
    """
    print("sadasd")
    return{
        "message": "Financial report scraping completed",
    }
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
