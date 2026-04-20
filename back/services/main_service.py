from typing import Optional, List, Dict, Any
from ..database.models import User
from ..contracts.security import ISecurityService
from ..dto.market import MainPageData
from ..services.market_service import MarketService


class MainService:
    def __init__(self, security_service: ISecurityService, market_service: MarketService):
        self.security_service = security_service
        self.market_service = market_service

    async def get_main_page_data(self, request, current_user: Optional[User]) -> Optional[MainPageData]:
        if not current_user:
            return None

        csrf_token = ""
        if request:
            csrf_token = await self.security_service.get_csrf_token(request)
        
        all_data = await self.market_service.get_all_cached_data()
        
        gainers = []
        losers = []
        
        stocks_data = all_data.get('stock', [])
        
        for asset in stocks_data:
            price = asset.get('price', 0)
            change_percent = asset.get('change_percent', 0)
            
            if change_percent is None:
                change_percent = 0
            
            if price <= 0:
                continue
            
            if change_percent <= -99.9:
                continue
            
            asset_info = {
                'ticker': asset.get('ticker', ''),
                'name': asset.get('name', ''),
                'change_percent': change_percent,
                'price': price,
                'asset_type': 'stock'
            }
            
            if change_percent > 0:
                gainers.append(asset_info)
            elif change_percent < 0:
                losers.append(asset_info)
        
        gainers.sort(key=lambda x: x['change_percent'], reverse=True)
        losers.sort(key=lambda x: x['change_percent'])
        
        top_gainers = gainers[:5]
        top_losers = losers[:5]

        return MainPageData(
            user=current_user,
            csrf_token=csrf_token,
            top_gainers=top_gainers,
            top_losers=top_losers
        )