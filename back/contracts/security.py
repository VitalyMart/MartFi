from typing import Protocol
from fastapi import Request

class ISecurityService(Protocol):
    async def get_csrf_token(self, request: Request) -> str: ...