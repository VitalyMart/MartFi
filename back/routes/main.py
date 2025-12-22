from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..auth.security import get_csrf_token
from ..database.models import User
from ..auth.dependencies import get_current_user
from ..templates import templates  # Просто импортируем глобальный экземпляр

router = APIRouter()


@router.get("/")
async def root(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login")
    csrf_token = get_csrf_token(request)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "user": current_user,
            "csrf_token": csrf_token
        }
    )