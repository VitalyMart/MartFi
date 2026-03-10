# back/routes/assistant.py
from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from ..templates import templates
from ..dependencies.auth_dependencies import get_current_user
from ..auth.entities.user import User as DomainUser

router = APIRouter()

@router.get("/assistant")
async def assistant_page(
    request: Request,
    current_user: DomainUser | None = Depends(get_current_user)
):
    if not current_user:
        return RedirectResponse("/login")
    
    return templates.TemplateResponse(
        "assistant.html",
        {
            "request": request,
            "user": current_user,
            "csrf_token": request.session.get("csrf_token", "")
        }
    )