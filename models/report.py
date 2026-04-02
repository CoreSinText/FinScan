from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from core.database import Base

class FinancialReport(Base):
    __tablename__ = "financial_report"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    year = Column(Integer, nullable=False, index=True)
    period = Column(String, nullable=False, index=True)        # tw1, tw2, tw3, audit
    report_type = Column(String, nullable=False, index=True)   # rdf (Laporan Keuangan), rda (Laporan Tahunan)
    file_id = Column(String, unique=True, index=True, nullable=False)  # IDX File_ID (UUID) for deduplication
    file_name = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    file_type = Column(String, nullable=True)                  # .pdf, .xlsx, .zip
    file_size = Column(Integer, nullable=True)
    is_downloaded = Column(Boolean, default=False)             # track download status

    company = relationship("Company", back_populates="reports")
