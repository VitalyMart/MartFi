from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from ..models.portfolio import PortfolioItem as ORMPortfolioItem
from ...core.logger import logger

class PortfolioRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_user_portfolio(self, user_id: int) -> List[Dict[str, Any]]:
        items = self.db.query(ORMPortfolioItem).filter(
            ORMPortfolioItem.user_id == user_id
        ).all()
        
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
    
    def add_to_portfolio(self, user_id: int, ticker: str, asset_type: str, 
                         quantity: float, average_price: float = 0.0, notes: str = "") -> Optional[Dict[str, Any]]:
        try:
            existing = self.db.query(ORMPortfolioItem).filter(
                ORMPortfolioItem.user_id == user_id,
                ORMPortfolioItem.ticker == ticker,
                ORMPortfolioItem.asset_type == asset_type
            ).first()
            
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
            
            self.db.commit()
            self.db.refresh(existing)
            
            return {
                'id': existing.id,
                'ticker': existing.ticker,
                'asset_type': existing.asset_type,
                'quantity': existing.quantity,
                'average_price': existing.average_price,
                'notes': existing.notes,
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error adding to portfolio: {e}")
            return None
    
    def remove_from_portfolio(self, user_id: int, portfolio_item_id: int) -> bool:
        try:
            item = self.db.query(ORMPortfolioItem).filter(
                ORMPortfolioItem.id == portfolio_item_id,
                ORMPortfolioItem.user_id == user_id
            ).first()
            
            if not item:
                return False
            
            self.db.delete(item)
            self.db.commit()
            return True
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error removing from portfolio: {e}")
            return False
    
    def update_portfolio_item(self, user_id: int, portfolio_item_id: int, 
                             quantity: Optional[float] = None, 
                             average_price: Optional[float] = None,
                             notes: Optional[str] = None) -> Optional[Dict[str, Any]]:
        try:
            item = self.db.query(ORMPortfolioItem).filter(
                ORMPortfolioItem.id == portfolio_item_id,
                ORMPortfolioItem.user_id == user_id
            ).first()
            
            if not item:
                return None
            
            if quantity is not None:
                item.quantity = quantity
            if average_price is not None:
                item.average_price = average_price
            if notes is not None:
                item.notes = notes
            
            self.db.commit()
            self.db.refresh(item)
            
            return {
                'id': item.id,
                'ticker': item.ticker,
                'asset_type': item.asset_type,
                'quantity': item.quantity,
                'average_price': item.average_price,
                'notes': item.notes,
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating portfolio item: {e}")
            return None