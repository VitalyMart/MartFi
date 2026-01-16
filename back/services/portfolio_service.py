from typing import List, Dict, Any, Optional
from ..database.repositories.portfolio_repository import PortfolioRepository
from ..services.market_service import MarketService
from ..contracts.security import ISecurityService
from ..dto.portfolio import PortfolioPageData, PortfolioStats
from ..core.logger import logger

class PortfolioService:
    def __init__(
        self,
        security_service: ISecurityService,
        portfolio_repo: PortfolioRepository,
        market_service: MarketService
    ):
        self.security_service = security_service
        self.portfolio_repo = portfolio_repo
        self.market_service = market_service
    
    async def get_portfolio_page_data(self, request, current_user) -> Optional[PortfolioPageData]:
        if not current_user:
            return None
        
        csrf_token = await self.security_service.get_csrf_token(request)
        
        
        portfolio_items = self.portfolio_repo.get_user_portfolio(current_user.id)
        
        
        enriched_items = await self._enrich_portfolio_items(portfolio_items)
        
        
        portfolio_summary = await self._calculate_portfolio_summary(enriched_items)
        
        return PortfolioPageData(
            user=current_user,
            csrf_token=csrf_token,
            portfolio_items=enriched_items,
            portfolio_summary=portfolio_summary
        )
    
    async def _enrich_portfolio_items(self, portfolio_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        enriched_items = []
        
        for item in portfolio_items:
            try:
                
                market_data = await self.market_service.get_cached_data(item['asset_type'])
                
                
                current_data = next(
                    (stock for stock in market_data if stock['ticker'] == item['ticker']),
                    None
                )
                
                if current_data:
                    current_price = current_data.get('price', 0)
                    current_change = current_data.get('change', 0)
                    current_change_percent = current_data.get('change_percent', 0)
                    
                    
                    purchase_value = item['quantity'] * item['average_price']
                    current_value = item['quantity'] * current_price
                    total_change = current_value - purchase_value
                    total_change_percent = (total_change / purchase_value * 100) if purchase_value > 0 else 0
                    
                    enriched_item = {
                        **item,
                        'current_price': current_price,
                        'current_change': current_change,
                        'current_change_percent': current_change_percent,
                        'purchase_value': purchase_value,
                        'current_value': current_value,
                        'total_change': total_change,
                        'total_change_percent': total_change_percent,
                        'name': current_data.get('name', item['ticker']),
                        'asset_type_display': self._get_asset_type_display(item['asset_type'])
                    }
                    enriched_items.append(enriched_item)
                    
            except Exception as e:
                logger.error(f"Error enriching portfolio item {item['ticker']}: {e}")
                
                enriched_items.append({
                    **item,
                    'current_price': 0,
                    'current_value': 0,
                    'total_change': 0,
                    'total_change_percent': 0,
                    'name': item['ticker'],
                    'asset_type_display': self._get_asset_type_display(item['asset_type'])
                })
        
        return enriched_items
    
    async def _calculate_portfolio_summary(self, portfolio_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        total_purchase_value = sum(item.get('purchase_value', 0) for item in portfolio_items)
        total_current_value = sum(item.get('current_value', 0) for item in portfolio_items)
        total_change = total_current_value - total_purchase_value
        total_change_percent = (total_change / total_purchase_value * 100) if total_purchase_value > 0 else 0
        
        
        asset_distribution = {}
        for item in portfolio_items:
            asset_type = item['asset_type']
            current_value = item.get('current_value', 0)
            if current_value > 0:
                asset_distribution[asset_type] = asset_distribution.get(asset_type, 0) + current_value
        
        return {
            'total_purchase_value': total_purchase_value,
            'total_current_value': total_current_value,
            'total_change': total_change,
            'total_change_percent': total_change_percent,
            'asset_distribution': asset_distribution,
            'item_count': len(portfolio_items)
        }
    
    def _get_asset_type_display(self, asset_type: str) -> str:
        display_map = {
            'stock': 'Акция',
            'bond': 'Облигация',
            'fund': 'Фонд',
            'currency': 'Валюта',
        }
        return display_map.get(asset_type, asset_type)
    
    def add_to_portfolio(self, user_id: int, ticker: str, asset_type: str, quantity: float, average_price: float = 0.0, notes: str = "") -> Optional[Dict[str, Any]]:
        if asset_type == 'index':
            return None
    
        return self.portfolio_repo.add_to_portfolio(user_id, ticker, asset_type, quantity, average_price, notes)
    
    def remove_from_portfolio(self, user_id: int, portfolio_item_id: int) -> bool:
        return self.portfolio_repo.remove_from_portfolio(user_id, portfolio_item_id)
    
    def update_portfolio_item(self, user_id: int, portfolio_item_id: int, 
                             quantity: Optional[float] = None, 
                             average_price: Optional[float] = None,
                             notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        return self.portfolio_repo.update_portfolio_item(user_id, portfolio_item_id, quantity, average_price, notes)
    
    async def quick_add_to_portfolio(self, user_id: int, ticker: str, asset_type: str, 
                                    quantity: float, price: float = None) -> Optional[Dict[str, Any]]:
        """
        Быстрое добавление актива в портфель.
        Если цена не указана, используется текущая рыночная цена.
        """
        if asset_type == 'index':
            return None
        
        
        if price is None or price == 0:
            try:
                market_data = await self.market_service.get_cached_data(asset_type)
                asset_data = next(
                    (item for item in market_data if item['ticker'] == ticker),
                    None
                )
                if asset_data and asset_data.get('price', 0) > 0:
                    price = asset_data['price']
                else:
                    price = 0
            except Exception as e:
                logger.error(f"Error getting market price for {ticker}: {e}")
                price = 0
        
        return self.portfolio_repo.add_to_portfolio(
            user_id=user_id,
            ticker=ticker,
            asset_type=asset_type,
            quantity=quantity,
            average_price=price,
            notes=f"Добавлено со страницы рынка"
        )