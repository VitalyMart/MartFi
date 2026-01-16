from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from ..auth.entities.user import User as DomainUser

@dataclass
class PortfolioItemDTO:
    ticker: str
    asset_type: str
    quantity: float
    average_price: float
    notes: Optional[str] = None

@dataclass
class PortfolioPageData:
    user: DomainUser
    csrf_token: str
    portfolio_items: List[Dict[str, Any]]
    portfolio_summary: Dict[str, Any]

@dataclass
class PortfolioStats:
    total_value: float
    total_change: float
    total_change_percent: float
    asset_distribution: Dict[str, float]