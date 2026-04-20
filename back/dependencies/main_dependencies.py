from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.main_service import MainService
from ..services.market_service import MarketService
from .common import get_security_service
from .market_dependencies import get_market_service


async def get_main_service(
    security_service: ISecurityService = Depends(get_security_service),
    market_service: MarketService = Depends(get_market_service),
) -> MainService:
    return MainService(security_service=security_service, market_service=market_service)