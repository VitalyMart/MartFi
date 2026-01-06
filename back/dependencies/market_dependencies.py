from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from .common import get_security_service
from ..services.market.providers import StocksDataProvider


def get_market_data_providers():
    base_url = "https://iss.moex.com/iss"
    return [StocksDataProvider(base_url)]


def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MarketService:
    providers = get_market_data_providers()
    return MarketService(security_service=security_service, data_providers=providers)