from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from typing import Annotated, Tuple
from sqlalchemy.orm import Session

from ..auth.security import csrf_protect
from ..services.auth_service import AuthService
from ..database import get_db
from ..templates import templates
from ..dependencies.auth_dependencies import get_auth_context_service, get_auth_processor_service

router = APIRouter()
DatabaseSession = Annotated[Session, Depends(get_db)]
AuthProcessor = Annotated[Tuple[AuthService, Session], Depends(get_auth_processor_service)]


@router.get("/login")
async def login_page(
    request: Request,
    get_context=Depends(get_auth_context_service),
):
    page_data = await get_context(request, page_type="login")
    
    if page_data.get("redirect"):
        return RedirectResponse(page_data["redirect"])
    
    return templates.TemplateResponse(
        "login.html",
        page_data["template_data"]
    )


@router.get("/register")
async def register_page(
    request: Request,
    get_context=Depends(get_auth_context_service),
):
    page_data = await get_context(request, page_type="register")
    
    if page_data.get("redirect"):
        return RedirectResponse(page_data["redirect"])
    
    return templates.TemplateResponse(
        "register.html",
        page_data["template_data"]
    )


@router.post("/register")
async def register(
    request: Request,
    auth_processor: AuthProcessor,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    auth_service, db = auth_processor
    client_ip = request.client.host
    
    return await auth_service.register_user(
        db=db,
        request=request,
        email=email,
        password=password,
        full_name=full_name,
        client_ip=client_ip
    )


@router.post("/login")
async def login(
    request: Request,
    auth_processor: AuthProcessor,
    email: str = Form(...),
    password: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    auth_service, db = auth_processor
    
    return await auth_service.login_user(
        db=db,
        request=request,
        email=email,
        password=password
    )


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_processor_service),
    csrf_verified: bool = Depends(csrf_protect),
):
    auth_service, _ = auth_service if isinstance(auth_service, tuple) else (auth_service, None)
    
    return await auth_service.logout_user(request)