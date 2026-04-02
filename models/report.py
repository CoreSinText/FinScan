from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from core.database import Base

class FinancialReport(Base):
    __tablename__ = "financial_report"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("company.id"), nullable=False)
    year = Column(Integer, nullable=False)
    period = Column(String, nullable=False)
    file_name = Column(String, unique=True, index=True, nullable=False)
    url = Column(String, nullable=True)

    company = relationship("Company", back_populates="reports")
