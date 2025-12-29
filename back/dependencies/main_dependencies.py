from typing import Callable
from fastapi import Depends, Request
from ..contracts.security import ISecurityService
from ..services.main_service import MainService
from ..auth.dependencies import get_current_user
from ..database.models import User
from .common import get_security_service 

async def get_main_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MainService:
    return MainService(security_service=security_service)

async def get_main_page_context_service(
    main_service: MainService = Depends(get_main_service),
    current_user: User = Depends(get_current_user),
) -> Callable:
    async def get_context(request: Request):
        return await main_service.get_main_page_context(request, current_user)
    return get_context