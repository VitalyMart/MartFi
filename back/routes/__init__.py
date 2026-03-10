# back/routes/__init__.py
from .auth import router as auth_router
from .main import router as main_router
from .market import router as market_router
from .portfolio import router as portfolio_router
from .profile import router as profile_router
from .chat import router as chat_router
from .assistant import router as assistant_router

__all__ = [
    "auth_router", 
    "main_router", 
    "market_router", 
    "portfolio_router", 
    "profile_router", 
    "chat_router",
    "assistant_router"
]