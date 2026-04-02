"""
Entry point for the FinScan FastAPI application.
"""
from fastapi import FastAPI
from api.endpoints import router as api_router
from core.database import engine, Base
from models import company, report  # ensure models are loaded

app = FastAPI(
    title="FinScan API",
    description="API for extracting financial report data from PDF to calculate PBV and PE ratios",
    version="1.0.0",
)

app.include_router(api_router, prefix="/api")

# Create tables in the database
Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
