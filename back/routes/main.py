from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse

from ..services.main_service import MainService
from ..templates import templates
from ..dependencies import get_main_service
from ..auth.dependencies import get_current_user
from ..database.models import User

router = APIRouter()


@router.get("/")
async def root(
    request: Request,
    main_service: MainService = Depends(get_main_service),
    current_user: User = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login")

    data = await main_service.get_main_page_data(request, current_user)

    if not data:
        return RedirectResponse("/login")

    return templates.TemplateResponse(
        "index.html", {"request": request, "user": data.user, "csrf_token": data.csrf_token}
    )
