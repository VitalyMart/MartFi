import aiohttp
from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from .common import get_security_service
from ..services.market.providers import StocksDataProvider, BondsDataProvider, FundsDataProvider, IndicesDataProvider, CurrencyDataProvider
from ..core.http_client import get_http_session

def get_market_data_providers(
    session: aiohttp.ClientSession = Depends(get_http_session)
):
    base_url = "https://iss.moex.com/iss"
    return [
        StocksDataProvider(base_url, session),
        BondsDataProvider(base_url, session),
        FundsDataProvider(base_url, session),
        IndicesDataProvider(base_url, session),
        CurrencyDataProvider(base_url, session),
    ]

def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
    providers: list = Depends(get_market_data_providers),
) -> MarketService:
    return MarketService(security_service=security_service, data_providers=providers)