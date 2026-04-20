import aiohttp
from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.market_service import MarketService
from .common import get_security_service
from ..services.market.providers import StocksDataProvider, BondsDataProvider, FundsDataProvider, IndicesDataProvider, CurrencyDataProvider
from ..core.http_client import get_http_session

_market_service = None

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

async def get_market_service(
    security_service: ISecurityService = Depends(get_security_service),
    providers: list = Depends(get_market_data_providers),
) -> MarketService:
    global _market_service
    if _market_service is None:
        _market_service = MarketService(security_service=security_service, data_providers=providers)
        await _market_service.start_background_updater()
    return _market_service