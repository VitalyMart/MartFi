from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from ..auth.entities.user import User as DomainUser


class MainPageData(BaseModel):
    user: DomainUser
    csrf_token: str


class MarketPageData(BaseModel):
    user: DomainUser
    csrf_token: str
    stocks: List[Dict[str, Any]]
    search_query: str
    sort_by: str
    sort_order: str
    page: int
    total_pages: int
    total_count: int


class MarketStocksData(BaseModel):
    stocks: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    filters: Dict[str, Any]