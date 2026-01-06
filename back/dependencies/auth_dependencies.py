from typing import Callable, Optional, Tuple
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..contracts.security import ISecurityService
from ..contracts.repositories import IUserRepository
from ..services.auth_service import AuthService
from ..auth.entities.user import User as DomainUser
from ..database import get_db
from .common import get_security_service
from ..database.repositories.user_repository import UserRepository


def get_user_repository(db: Session = Depends(get_db)) -> IUserRepository:
    return UserRepository(db)


def get_auth_service(
    user_repo: IUserRepository = Depends(get_user_repository),
    security_service: ISecurityService = Depends(get_security_service),
) -> AuthService:
    return AuthService(security_service=security_service, user_repo=user_repo)


async def get_current_user(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
) -> Optional[DomainUser]:
    token = request.cookies.get("access_token")
    return await auth_service.get_current_user(token)


async def get_auth_context_service(
    auth_service: AuthService = Depends(get_auth_service),
    current_user: Optional[DomainUser] = Depends(get_current_user),
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
) -> Tuple[AuthService, Session]:
    return auth_service, db