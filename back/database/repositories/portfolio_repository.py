from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from ..models.portfolio import PortfolioItem as ORMPortfolioItem
from ...core.logger import logger

class PortfolioRepository:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_user_portfolio(self, user_id: int) -> List[Dict[str, Any]]:
        stmt = select(ORMPortfolioItem).where(
            ORMPortfolioItem.user_id == user_id
        )
        result = await self.db.execute(stmt)
        items = result.scalars().all()
        
        return [
            {
                'id': item.id,
                'ticker': item.ticker,
                'asset_type': item.asset_type,
                'quantity': item.quantity,
                'average_price': item.average_price,
                'notes': item.notes,
                'created_at': item.created_at.isoformat() if item.created_at else None,
            }
            for item in items
        ]
    
    async def add_to_portfolio(self, user_id: int, ticker: str, asset_type: str, 
                              quantity: float, average_price: float = 0.0, notes: str = "") -> Optional[Dict[str, Any]]:
        try:
            stmt = select(ORMPortfolioItem).where(
                ORMPortfolioItem.user_id == user_id,
                ORMPortfolioItem.ticker == ticker,
                ORMPortfolioItem.asset_type == asset_type
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.quantity += quantity
                if average_price > 0:
                    total_investment = (existing.quantity * existing.average_price) + (quantity * average_price)
                    existing.average_price = total_investment / existing.quantity
                if notes:
                    existing.notes = notes
            else:
                existing = ORMPortfolioItem(
                    user_id=user_id,
                    ticker=ticker,
                    asset_type=asset_type,
                    quantity=quantity,
                    average_price=average_price,
                    notes=notes
                )
                self.db.add(existing)
            
            await self.db.commit()
            await self.db.refresh(existing)
            
            return {
                'id': existing.id,
                'ticker': existing.ticker,
                'asset_type': existing.asset_type,
                'quantity': existing.quantity,
                'average_price': existing.average_price,
                'notes': existing.notes,
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error adding to portfolio: {e}")
            return None
    
    async def remove_from_portfolio(self, user_id: int, portfolio_item_id: int) -> bool:
        try:
            stmt = delete(ORMPortfolioItem).where(
                ORMPortfolioItem.id == portfolio_item_id,
                ORMPortfolioItem.user_id == user_id
            )
            result = await self.db.execute(stmt)
            await self.db.commit()
            
            return result.rowcount > 0
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error removing from portfolio: {e}")
            return False
    
    async def update_portfolio_item(self, user_id: int, portfolio_item_id: int, 
                                   quantity: Optional[float] = None, 
                                   average_price: Optional[float] = None,
                                   notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            stmt = select(ORMPortfolioItem).where(
                ORMPortfolioItem.id == portfolio_item_id,
                ORMPortfolioItem.user_id == user_id
            )
            result = await self.db.execute(stmt)
            item = result.scalar_one_or_none()
            
            if not item:
                return None
            
            if quantity is not None:
                item.quantity = quantity
            if average_price is not None:
                item.average_price = average_price
            if notes is not None:
                item.notes = notes
            
            await self.db.commit()
            await self.db.refresh(item)
            
            return {
                'id': item.id,
                'ticker': item.ticker,
                'asset_type': item.asset_type,
                'quantity': item.quantity,
                'average_price': item.average_price,
                'notes': item.notes,
            }
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error updating portfolio item: {e}")
            return None