from .auth import router as auth_router
from .main import router as main_router
from .market import router as market_router

__all__ = ["auth_router", "main_router", "market_router"]