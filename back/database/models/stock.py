from sqlalchemy import Column, Integer, String, Float, DateTime
from sqlalchemy.sql import func
from ..base import Base


class Stock(Base):
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(20), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    full_name = Column(String(500), nullable=True)
    price = Column(Float, default=0.0)
    change = Column(Float, default=0.0)
    sector = Column(String(100), nullable=True)
    market_cap = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
