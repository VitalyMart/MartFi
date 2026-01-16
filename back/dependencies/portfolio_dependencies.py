from fastapi import Depends
from sqlalchemy.orm import Session
from ..contracts.security import ISecurityService
from ..services.portfolio_service import PortfolioService
from ..services.market_service import MarketService
from ..database.repositories.portfolio_repository import PortfolioRepository
from .common import get_security_service
from .market_dependencies import get_market_service
from ..database import get_db

def get_portfolio_repository(db: Session = Depends(get_db)) -> PortfolioRepository:
    return PortfolioRepository(db)

def get_portfolio_service(
    security_service: ISecurityService = Depends(get_security_service),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    market_service: MarketService = Depends(get_market_service),
) -> PortfolioService:
    return PortfolioService(
        security_service=security_service,
        portfolio_repo=portfolio_repo,
        market_service=market_service
    )