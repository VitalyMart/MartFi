from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from ..database.models import User


@dataclass
class MainPageData:
    user: User
    csrf_token: str


@dataclass
class MarketPageData:
    user: User
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