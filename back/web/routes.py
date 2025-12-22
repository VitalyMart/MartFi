from fastapi import Depends, Form, Request, Response
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from typing import Annotated
from datetime import datetime

from ..auth.security import (
    get_csrf_token,
    csrf_protect,
    validate_password,
    verify_user_password
)
from ..auth.validators import (
    validate_full_name,
    normalize_and_validated_email
)
from ..auth.services import (
    create_access_token,
    is_email_registered,
    create_user,
    verify_token
)
from ..auth.services import (
    EmailAlreadyExistsError,
    UserCreationError
)
from ..market.services import fetch_moex_data, fetch_stocks
from ..core import (
    redis_client,
    is_rate_limited,
    increment_rate_limit,
    clear_rate_limit,
    is_registration_rate_limited,
    increment_registration_attempts,
    get_login_rate_key
)
from ..core.logger import logger
from ..database import get_db
from ..database.models import User
from ..config import settings

DatabaseSession = Annotated[Session, Depends(get_db)]


def setup_routes(app, templates: Jinja2Templates, get_current_user):
    
    def render_form_error(
        request: Request,
        template_name: str,
        error: str
    ) -> Response:
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse(
            template_name,
            {
                "request": request,
                "error": error,
                "csrf_token": csrf_token
            },
        )

    @app.get("/")
    async def root(
        request: Request,
        current_user: User = Depends(get_current_user)
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

    @app.get("/login")
    async def login_page(
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        if current_user:
            return RedirectResponse("/")
        
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "csrf_token": csrf_token
            }
        )

    @app.get("/register")
    async def register_page(
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        if current_user:
            return RedirectResponse("/")
        
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse(
            "register.html",
            {
                "request": request,
                "csrf_token": csrf_token
            }
        )
        
    @app.get("/market")
    async def assets_page(
        request: Request,
        current_user: User = Depends(get_current_user)
    ):
        if not current_user:
            return RedirectResponse("/login")
        
        csrf_token = get_csrf_token(request)
        stocks = await fetch_stocks()
        
        return templates.TemplateResponse(
            "market.html",
            {
                "request": request,
                "user": current_user,
                "csrf_token": csrf_token,
                "stocks": stocks
            }
        )


        
    @app.post("/register")
    async def register(
        request: Request,
        db: DatabaseSession,
        email: str = Form(...),
        password: str = Form(...),
        full_name: str = Form(...),
        csrf_verified: bool = Depends(csrf_protect),
    ):
        client_ip = request.client.host
        if is_registration_rate_limited(client_ip):
            logger.warning(
                f"Registration rate limit exceeded for IP: {client_ip}"
            )
            return render_form_error(
                request,
                "register.html",
                "Too many registration attempts. Try again later"
            )

        normalized_email = normalize_and_validated_email(email)
        if not normalized_email:
            increment_registration_attempts(client_ip)
            return render_form_error(
                request,
                "register.html",
                "Invalid email format"
            )

        is_valid_pass, pass_error = validate_password(password)
        if not is_valid_pass:
            increment_registration_attempts(client_ip)
            return render_form_error(request, "register.html", pass_error)

        is_valid_name, name_error = validate_full_name(full_name)
        if not is_valid_name:
            increment_registration_attempts(client_ip)
            return render_form_error(request, "register.html", name_error)

        if is_email_registered(db, normalized_email):
            increment_registration_attempts(client_ip)
            return render_form_error(
                request,
                "register.html",
                "Email already registered"
            )

        try:
            user = create_user(db, normalized_email, password, full_name)
            logger.info(f"User registered successfully: {normalized_email}")
            return RedirectResponse(
                "/login?registered=true",
                status_code=303
            )
        
        except EmailAlreadyExistsError:
            increment_registration_attempts(client_ip)
            return render_form_error(
                request,
                "register.html",
                "Email already registered"
            )
        
        except UserCreationError as e:
            logger.error(f"User creation error for {normalized_email}: {e}")
            increment_registration_attempts(client_ip)
            return render_form_error(
                request,
                "register.html",
                "Registration error. Try again later"
            )
        
        except Exception as e:
            logger.error(
                f"Unexpected registration error for {normalized_email}: {e}"
            )
            increment_registration_attempts(client_ip)
            return render_form_error(
                request,
                "register.html",
                "Unexpected error. Try again later"
            )

    @app.post("/login")
    async def login(
        request: Request,
        db: DatabaseSession,
        email: str = Form(...),
        password: str = Form(...),
        csrf_verified: bool = Depends(csrf_protect),
    ):
        normalized_email = normalize_and_validated_email(email)
        if not normalized_email:
            return render_form_error(
                request,
                "login.html",
                "Invalid email or password"
            )
        
        login_key = get_login_rate_key(normalized_email)
        
        if is_rate_limited(login_key):
            logger.warning(f"Login rate limit exceeded for: {email}")
            return render_form_error(
                request,
                "login.html",
                "Too many login attempts"
            )
        
        user = verify_user_password(db, email, password)
        
        if not user:
            increment_rate_limit(login_key)
            logger.warning(f"Failed login attempt for: {email}")
            return render_form_error(
                request,
                "login.html",
                "Invalid email or password"
            )
        
        clear_rate_limit(login_key)
        access_token = create_access_token(user.id)
        
        try:
            redis_client.setex(
                f"session:{user.id}",
                settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
                "active"
            )
        except Exception as e:
            logger.error(f"Redis error storing session: {e}")
        
        logger.info(f"User logged in successfully: {email}")
        response = RedirectResponse("/", status_code=303)
        response.set_cookie(
            key="access_token",
            value=access_token,
            httponly=True,
            max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            secure=not settings.DEBUG,
            samesite="lax",
            path="/"
        )
        return response

    @app.post("/logout")
    async def logout(
        request: Request,
        csrf_verified: bool = Depends(csrf_protect)
    ):
        token = request.cookies.get("access_token")
        if token:
            try:
                payload = verify_token(token)
                if payload and payload.get("sub"):
                    user_id = payload.get("sub")
                    try:
                        redis_client.delete(f"session:{user_id}")
                        redis_client.delete(f"token:{user_id}")
                    except Exception as e:
                        logger.error(f"Redis error during logout: {e}")
            except Exception as e:
                logger.error(f"Error during token cleanup: {e}")
        
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
    
    @app.get("/api/moex-test")
    async def moex_test(request: Request):
        stocks = await fetch_moex_data()
    
        return {
            "message": "MOEX data fetched successfully",
            "stocks_count": len(stocks),
            "stocks": stocks
        }