from typing import Callable
from fastapi import Depends, Request
from sqlalchemy.orm import Session
from ..contracts.security import ISecurityService
from ..services.auth_service import AuthService
from ..auth.dependencies import get_current_user
from ..database.models import User
from ..database import get_db
from .common import get_security_service  

def get_auth_service(
    db: Session = Depends(get_db),
    security_service: ISecurityService = Depends(get_security_service),
) -> AuthService:
    return AuthService(
        security_service=security_service,
        db_session=db
    )
    
async def get_auth_context_service(
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
) -> Callable:
    async def get_context(request: Request, page_type: str = "login"):
        if page_type == "login":
            return await auth_service.get_login_page_context(request, current_user)
        elif page_type == "register":
            return await auth_service.get_register_page_context(request, current_user)
        else:
            raise ValueError(f"Unknown page type: {page_type}")
    return get_context

async def get_auth_processor_service(
    auth_service: AuthService = Depends(get_auth_service),
    db: Session = Depends(get_db),
) -> tuple:
    return auth_service, db

