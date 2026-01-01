from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from .common import get_security_service


async def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MarketService:
    return MarketService(security_service=security_service)
