from ..services.security_service import SecurityService
from ..contracts.security import ISecurityService

async def get_security_service() -> ISecurityService:
    return SecurityService()