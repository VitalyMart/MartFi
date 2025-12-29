from typing import Callable
from fastapi import Depends, Request
from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from ..auth.dependencies import get_current_user
from ..database.models import User
from .common import get_security_service 

async def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MarketService:
    return MarketService(security_service=security_service)

async def get_market_page_context_service(
    market_service: MarketService = Depends(get_market_service),
    current_user: User = Depends(get_current_user),
) -> Callable:
    async def get_context(
        request: Request,
        search: str = "",
        sort_by: str = "name",
        sort_order: str = "asc",
        page: int = 1,
        page_size: int = 50
    ):
        return await market_service.get_market_page_context(
            request=request,
            current_user=current_user,
            search=search,
            sort_by=sort_by,
            sort_order=sort_order,
            page=page,
            page_size=page_size
        )
    return get_context