from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from ..contracts.security import ISecurityService
from ..services.profile_service import ProfileService
from ..services.market_service import MarketService
from ..database.repositories.user_repository import UserRepository
from ..database.repositories.portfolio_repository import PortfolioRepository
from .common import get_security_service
from .market_dependencies import get_market_service
from ..database import get_db

def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)

def get_portfolio_repository(db: AsyncSession = Depends(get_db)) -> PortfolioRepository:
    return PortfolioRepository(db)

def get_profile_service(
    security_service: ISecurityService = Depends(get_security_service),
    user_repo: UserRepository = Depends(get_user_repository),
    portfolio_repo: PortfolioRepository = Depends(get_portfolio_repository),
    market_service: MarketService = Depends(get_market_service),
) -> ProfileService:
    return ProfileService(
        security_service=security_service,
        user_repo=user_repo,
        portfolio_repo=portfolio_repo,
        market_service=market_service
    )