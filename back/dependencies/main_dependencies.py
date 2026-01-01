from fastapi import Depends
from ..contracts.security import ISecurityService
from ..services.main_service import MainService
from .common import get_security_service


async def get_main_service(
    security_service: ISecurityService = Depends(get_security_service),
) -> MainService:
    return MainService(security_service=security_service)
