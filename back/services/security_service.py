from fastapi import Request
from ..contracts.security import ISecurityService

class SecurityService(ISecurityService):
    async def get_csrf_token(self, request: Request) -> str:
        from ..auth.security import get_csrf_token
        return get_csrf_token(request)