from typing import Optional
from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from ..database.models import User
from ..contracts.security import ISecurityService
from ..templates import templates

class MainService:
    def __init__(self, security_service: ISecurityService):
        self.security_service = security_service
    
    async def get_main_page_context(
        self,
        request: Request,
        current_user: Optional[User]
    ) -> Response:
        
        
        if not current_user:
            return RedirectResponse("/login")
        
        csrf_token = await self.security_service.get_csrf_token(request)
        
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "user": current_user,
                "csrf_token": csrf_token
            }
        )