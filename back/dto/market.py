from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from ..auth.entities.user import User as DomainUser

@dataclass
class MainPageData:
    user: DomainUser
    csrf_token: str

@dataclass
class MarketPageData:
    user: DomainUser
    csrf_token: str
    stocks: List[Dict[str, Any]]
    search_query: str
    sort_by: str
    sort_order: str
    page: int
    total_pages: int
    total_count: int

@dataclass
class MarketStocksData:
    stocks: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    filters: Dict[str, Any]