from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from ..auth.entities.user import User as DomainUser


class PortfolioItemDTO(BaseModel):
    ticker: str
    asset_type: str
    quantity: float
    average_price: float
    notes: Optional[str] = None


class PortfolioPageData(BaseModel):
    user: DomainUser
    csrf_token: str
    portfolio_items: List[Dict[str, Any]]
    portfolio_summary: Dict[str, Any]


class PortfolioStats(BaseModel):
    total_value: float
    total_change: float
    total_change_percent: float
    asset_distribution: Dict[str, float]