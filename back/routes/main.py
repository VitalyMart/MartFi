from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse, JSONResponse
from ..services.main_service import MainService
from ..templates import templates
from ..dependencies import get_main_service
from ..dependencies.auth_dependencies import get_current_user
from ..auth.entities.user import User as DomainUser

router = APIRouter()

@router.get("/")
async def root(
    request: Request,
    main_service: MainService = Depends(get_main_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login")
    data = await main_service.get_main_page_data(request, current_user)
    if not data:
        return RedirectResponse("/login")
    return templates.TemplateResponse(
        "index.html", {
            "request": request,
            "user": data.user,
            "csrf_token": data.csrf_token,
            "top_gainers": data.top_gainers,
            "top_losers": data.top_losers
        }
    )

@router.get("/api/main/leaders")
async def get_leaders_data(
    request: Request,
    main_service: MainService = Depends(get_main_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        return JSONResponse({"success": False, "error": "Not authenticated"}, status_code=401)
    
    data = await main_service.get_main_page_data(request, current_user)
    if not data:
        return JSONResponse({"success": False, "error": "No data"}, status_code=500)
    
    return JSONResponse({
        "success": True,
        "top_gainers": data.top_gainers,
        "top_losers": data.top_losers
    })