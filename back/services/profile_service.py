from typing import Optional, Dict, Any, List
from ..database.repositories.user_repository import UserRepository
from ..database.repositories.portfolio_repository import PortfolioRepository
from ..services.market_service import MarketService
from ..contracts.security import ISecurityService
from ..dto.profile import ProfilePageData
from ..auth.security import verify_password, get_password_hash
from ..auth.entities.user import User as DomainUser
from ..core.logger import logger

class ProfileService:
    def __init__(
        self,
        security_service: ISecurityService,
        user_repo: UserRepository,
        portfolio_repo: PortfolioRepository,
        market_service: MarketService
    ):
        self.security_service = security_service
        self.user_repo = user_repo
        self.portfolio_repo = portfolio_repo
        self.market_service = market_service

    async def get_profile_page_data(self, request, current_user: DomainUser) -> Optional[ProfilePageData]:
        if not current_user:
            return None

        csrf_token = await self.security_service.get_csrf_token(request)
        
        raw_portfolio_items = await self.portfolio_repo.get_user_portfolio(current_user.id)
        
        enriched_items = await self._enrich_portfolio_items(raw_portfolio_items)
        
        stats = await self._calculate_profile_stats(enriched_items, current_user)

        return ProfilePageData(
            user=current_user,
            csrf_token=csrf_token,
            stats=stats
        )

    async def _enrich_portfolio_items(self, portfolio_items: list) -> list:
        if not portfolio_items:
            return []
        
        asset_types = set(item['asset_type'] for item in portfolio_items)
        all_market_data = await self.market_service.get_all_cached_data()
        
        enriched_items = []
        for item in portfolio_items:
            try:
                market_data = all_market_data.get(item['asset_type'], [])
                current_data = next(
                    (asset for asset in market_data if asset['ticker'] == item['ticker']),
                    None
                )
                
                if current_data:
                    if item['asset_type'] == 'bond':
                        current_price = current_data.get('price_rub', 0)
                    else:
                        current_price = current_data.get('price', 0)
                    
                    purchase_value = item['quantity'] * item['average_price']
                    current_value = item['quantity'] * current_price
                    
                    enriched_item = {
                        **item,
                        'current_price': current_price,
                        'purchase_value': purchase_value,
                        'current_value': current_value
                    }
                    
                    enriched_items.append(enriched_item)
                else:
                    purchase_value = item['quantity'] * item['average_price']
                    enriched_item = {
                        **item,
                        'current_price': item['average_price'],
                        'purchase_value': purchase_value,
                        'current_value': purchase_value
                    }
                    enriched_items.append(enriched_item)
                    
            except Exception as e:
                logger.error(f"Error enriching portfolio item {item['ticker']}: {e}")
                purchase_value = item['quantity'] * item['average_price']
                enriched_items.append({
                    **item,
                    'current_price': item['average_price'],
                    'purchase_value': purchase_value,
                    'current_value': purchase_value
                })
        
        return enriched_items

    async def _calculate_profile_stats(self, enriched_items: list, user: DomainUser) -> Dict[str, Any]:
        total_value = 0
        total_purchase = 0
        
        for item in enriched_items:
            total_value += item.get('current_value', 0)
            total_purchase += item.get('purchase_value', 0)
        
        total_change = total_value - total_purchase
        total_change_percent = (total_change / total_purchase * 100) if total_purchase > 0 else 0

        return {
            'total_portfolio_value': round(total_value, 2),
            'total_portfolio_change': round(total_change, 2),
            'total_portfolio_change_percent': round(total_change_percent, 2),
            'assets_count': len(enriched_items),
            'member_since': 'Недавно'
        }

    async def update_profile(
        self,
        user_id: int,
        full_name: str,
        email: str
    ) -> Dict[str, Any]:
        try:
            user = await self.user_repo.get_by_id(user_id)
            if not user:
                return {"success": False, "message": "Пользователь не найден"}

            if email != user.email:
                existing_user = await self.user_repo.get_by_email(email)
                if existing_user:
                    return {"success": False, "message": "Этот email уже используется"}

            updated_user = await self.user_repo.update_user(
                user_id=user_id,
                email=email,
                full_name=full_name
            )

            if updated_user:
                return {
                    "success": True,
                    "message": "Профиль успешно обновлен",
                    "user": {
                        "id": updated_user.id,
                        "email": updated_user.email,
                        "full_name": updated_user.full_name
                    }
                }
            else:
                return {"success": False, "message": "Ошибка при обновлении профиля"}

        except Exception as e:
            logger.error(f"Error updating profile for user {user_id}: {e}")
            return {"success": False, "message": "Внутренняя ошибка сервера"}

    async def change_password(
        self,
        user_id: int,
        current_password: str,
        new_password: str
    ) -> Dict[str, Any]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "Пользователь не найден"}

        if not verify_password(current_password, user.hashed_password):
            return {"success": False, "message": "Неверный текущий пароль"}

        if len(new_password) < 8:
            return {"success": False, "message": "Новый пароль должен содержать минимум 8 символов"}

        new_hashed_password = get_password_hash(new_password)
        updated_user = await self.user_repo.update_user(
            user_id=user_id,
            hashed_password=new_hashed_password
        )

        if updated_user:
            return {"success": True, "message": "Пароль успешно изменен"}
        else:
            return {"success": False, "message": "Ошибка при смене пароля"}

    async def delete_account(self, user_id: int, password: str) -> Dict[str, Any]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"success": False, "message": "Пользователь не найден"}

        if not verify_password(password, user.hashed_password):
            return {"success": False, "message": "Неверный пароль"}

        success = await self.user_repo.delete_user(user_id)
        if success:
            return {"success": True, "message": "Аккаунт успешно удален"}
        else:
            return {"success": False, "message": "Ошибка при удалении аккаунта"}