from typing import Optional, Dict, Any
from pydantic import BaseModel
from ..auth.entities.user import User as DomainUser

class ProfileUpdateForm(BaseModel):
    full_name: str
    email: str
    current_password: Optional[str] = None
    new_password: Optional[str] = None
    confirm_password: Optional[str] = None

class ProfilePageData(BaseModel):
    user: DomainUser
    csrf_token: str
    stats: Dict[str, Any]

class ProfileStats(BaseModel):
    total_portfolio_value: float
    total_portfolio_change: float
    total_portfolio_change_percent: float
    assets_count: int
    member_since: str