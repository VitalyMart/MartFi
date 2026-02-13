from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from ..auth.security import csrf_protect
from ..services.profile_service import ProfileService
from ..services.render_service import RenderService
from ..dependencies.profile_dependencies import get_profile_service
from ..dependencies.auth_dependencies import get_current_user
from ..dependencies.render_dependencies import get_render_service
from ..auth.entities.user import User as DomainUser
from ..core.logger import logger

router = APIRouter()

@router.get("/profile")
async def profile_page(
    request: Request,
    profile_service: ProfileService = Depends(get_profile_service),
    render_service: RenderService = Depends(get_render_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        return RedirectResponse("/login")

    data = await profile_service.get_profile_page_data(request, current_user)
    if not data:
        return RedirectResponse("/login")

    return render_service.render_with_csrf(
        request=request,
        template_name="profile.html",
        context={
            "user": data.user,
            "stats": data.stats
        }
    )

@router.post("/profile/update")
async def update_profile(
    request: Request,
    profile_service: ProfileService = Depends(get_profile_service),
    current_user: DomainUser | None = Depends(get_current_user),
    full_name: str = Form(...),
    email: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await profile_service.update_profile(
        user_id=current_user.id,
        full_name=full_name,
        email=email
    )

    if result["success"]:
        return JSONResponse(result)
    else:
        return JSONResponse(result, status_code=400)

@router.post("/profile/change-password")
async def change_password(
    request: Request,
    profile_service: ProfileService = Depends(get_profile_service),
    current_user: DomainUser | None = Depends(get_current_user),
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    if new_password != confirm_password:
        return JSONResponse({
            "success": False,
            "message": "Новые пароли не совпадают"
        }, status_code=400)

    result = await profile_service.change_password(
        user_id=current_user.id,
        current_password=current_password,
        new_password=new_password
    )

    if result["success"]:
        return JSONResponse(result)
    else:
        return JSONResponse(result, status_code=400)

@router.post("/profile/delete")
async def delete_account(
    request: Request,
    profile_service: ProfileService = Depends(get_profile_service),
    current_user: DomainUser | None = Depends(get_current_user),
    password: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    result = await profile_service.delete_account(
        user_id=current_user.id,
        password=password
    )

    if result["success"]:
        response = JSONResponse(result)
        response.delete_cookie(key="access_token")
        return response
    else:
        return JSONResponse(result, status_code=400)

@router.get("/api/profile/stats")
async def get_profile_stats(
    request: Request,
    profile_service: ProfileService = Depends(get_profile_service),
    current_user: DomainUser | None = Depends(get_current_user),
):
    if not current_user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        data = await profile_service.get_profile_page_data(request, current_user)
        return JSONResponse({
            "success": True,
            "data": data.stats if data else {}
        })
    except Exception as e:
        logger.error(f"Error getting profile stats: {e}")
        return JSONResponse({
            "success": False,
            "message": "Ошибка при получении статистики"
        }, status_code=500)