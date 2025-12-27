from typing import Callable
from fastapi import Depends, Request

from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from ..services.security_service import SecurityService
from ..auth.dependencies import get_current_user
from ..database.models import User

async def get_security_service() -> ISecurityService:
    return SecurityService()

async def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MarketService:
    return MarketService(security_service=security_service)

async def get_market_page_context_service(
    market_service: MarketService = Depends(get_market_service),
    current_user: User = Depends(get_current_user),
) -> Callable:
    async def get_context(request: Request):
        return await market_service.get_market_page_context(request, current_user)
    
    return get_context