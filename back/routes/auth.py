from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse

from ..auth.security import csrf_protect
from ..services.auth_service import AuthService
from ..auth.dto import RegistrationResult, LoginResult, LogoutResult
from ..auth.exceptions import (
    RateLimitException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    ValidationException
)
from ..templates import templates
from ..utils import render_form_error
from ..dependencies.auth_dependencies import get_auth_service
from ..auth.dependencies import get_current_user
from ..database.models import User
from ..core.logger import logger
from ..config import settings

router = APIRouter()


@router.get("/login")
async def login_page(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
):
    context_result = await auth_service.get_login_page_context(request, current_user)

    if context_result.redirect_path:
        return RedirectResponse(context_result.redirect_path)

    return templates.TemplateResponse(
        context_result.template_name,
        context_result.template_data
    )


@router.get("/register")
async def register_page(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    current_user: User = Depends(get_current_user),
):
    context_result = await auth_service.get_register_page_context(request, current_user)

    if context_result.redirect_path:
        return RedirectResponse(context_result.redirect_path)

    return templates.TemplateResponse(
        context_result.template_name,
        context_result.template_data
    )


@router.post("/register")
async def register(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    client_ip = request.client.host

    try:
        result: RegistrationResult = await auth_service.register_user(
            email=email,
            password=password,
            full_name=full_name,
            client_ip=client_ip
        )
    except RateLimitException as e:
        return render_form_error(request, "register.html", str(e))
    except ValidationException as e:
        return render_form_error(request, "register.html", str(e))
    except UserAlreadyExistsException as e:
        return render_form_error(request, "register.html", str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        return render_form_error(
            request,
            "register.html",
            "Registration error. Try again later"
        )

    return RedirectResponse(
        result.redirect_path or "/login?registered=true",
        status_code=303
    )


@router.post("/login")
async def login(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    email: str = Form(...),
    password: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),
):
    client_ip = request.client.host

    try:
        result: LoginResult = await auth_service.login_user(
            email=email,
            password=password,
            client_ip=client_ip
        )
    except RateLimitException as e:
        return render_form_error(request, "login.html", str(e))
    except InvalidCredentialsException as e:
        return render_form_error(request, "login.html", str(e))
    except Exception as e:
        logger.error(f"Login error: {e}")
        return render_form_error(
            request,
            "login.html",
            "Login error. Try again later"
        )

    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=result.access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )

    return response


@router.post("/logout")
async def logout(
    request: Request,
    auth_service: AuthService = Depends(get_auth_service),
    csrf_verified: bool = Depends(csrf_protect),
):
    access_token = request.cookies.get("access_token")

    try:
        result: LogoutResult = await auth_service.logout_user(access_token)
    except Exception as e:
        logger.error(f"Logout error: {e}")

    request.session.clear()

    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax",
        path="/"
    )

    return response