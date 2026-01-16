from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from ..base import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    portfolio_items = relationship("PortfolioItem", back_populates="user", cascade="all, delete-orphan")