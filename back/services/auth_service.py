from typing import Optional
from sqlalchemy.orm import Session

from ..auth.dto import RegistrationResult, LoginResult, LogoutResult, PageContextResult
from ..auth.exceptions import (
    RateLimitException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    ValidationException,
)
from ..database.models import User
from ..database.repositories.user_repository import UserRepository
from ..contracts.security import ISecurityService
from ..auth.services import create_access_token, verify_token
from ..auth.validators import validate_full_name, normalize_and_validated_email
from ..auth.security import validate_password
from ..core import (
    redis_client,
    is_rate_limited,
    increment_rate_limit,
    clear_rate_limit,
    is_registration_rate_limited,
    increment_registration_attempts,
    get_login_rate_key,
)
from ..core.logger import logger
from ..config import settings


class AuthService:
    def __init__(self, security_service: ISecurityService, db_session: Session):
        self.security_service = security_service
        self.db_session = db_session
        self.user_repository = UserRepository(db_session)

    async def get_login_page_context(self, request, current_user: Optional[User]) -> PageContextResult:
        if current_user:
            return PageContextResult(template_name="", template_data={}, redirect_path="/")

        csrf_token = await self.security_service.get_csrf_token(request)

        return PageContextResult(
            template_name="login.html",
            template_data={
                "request": request,
                "csrf_token": csrf_token,
            },
        )

    async def get_register_page_context(self, request, current_user: Optional[User]) -> PageContextResult:
        if current_user:
            return PageContextResult(template_name="", template_data={}, redirect_path="/")

        csrf_token = await self.security_service.get_csrf_token(request)

        return PageContextResult(
            template_name="register.html",
            template_data={
                "request": request,
                "csrf_token": csrf_token,
            },
        )

    async def register_user(self, email: str, password: str, full_name: str, client_ip: str) -> RegistrationResult:
        if is_registration_rate_limited(client_ip):
            logger.warning(f"Registration rate limit exceeded for IP: {client_ip}")
            raise RateLimitException("Too many registration attempts. Try again later")

        normalized_email = normalize_and_validated_email(email)
        if not normalized_email:
            increment_registration_attempts(client_ip)
            raise ValidationException("Invalid email format")

        is_valid_pass, pass_error = validate_password(password)
        if not is_valid_pass:
            increment_registration_attempts(client_ip)
            raise ValidationException(pass_error)

        is_valid_name, name_error = validate_full_name(full_name)
        if not is_valid_name:
            increment_registration_attempts(client_ip)
            raise ValidationException(name_error)

        if self.user_repository.email_exists(normalized_email):
            increment_registration_attempts(client_ip)
            raise UserAlreadyExistsException("Email already registered")

        try:
            user = self.user_repository.create(normalized_email, password, full_name)
            logger.info(f"User registered successfully: {normalized_email}")

            return RegistrationResult(success=True, user_id=user.id, redirect_path="/login?registered=true")

        except Exception as e:
            logger.error(f"User creation error for {normalized_email}: {e}")
            increment_registration_attempts(client_ip)
            raise

    async def login_user(self, email: str, password: str, client_ip: str) -> LoginResult:
        normalized_email = normalize_and_validated_email(email)
        if not normalized_email:
            raise InvalidCredentialsException("Invalid email or password")

        login_key = get_login_rate_key(normalized_email)
        if is_rate_limited(login_key):
            logger.warning(f"Login rate limit exceeded for: {email}")
            raise RateLimitException("Too many login attempts")

        user = self.user_repository.verify_credentials(email, password)
        if not user:
            increment_rate_limit(login_key)
            logger.warning(f"Failed login attempt for: {email}")
            raise InvalidCredentialsException("Invalid email or password")

        clear_rate_limit(login_key)
        access_token = create_access_token(user.id)

        try:
            redis_client.setex(f"session:{user.id}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "active")
        except Exception as e:
            logger.error(f"Redis error storing session: {e}")

        logger.info(f"User logged in successfully: {email}")

        return LoginResult(success=True, user_id=user.id, access_token=access_token)

    async def logout_user(self, access_token: Optional[str]) -> LogoutResult:
        user_id = None

        if access_token:
            try:
                payload = verify_token(access_token)
                if payload and payload.get("sub"):
                    user_id = payload.get("sub")
                    try:
                        redis_client.delete(f"session:{user_id}")
                        redis_client.delete(f"token:{user_id}")
                    except Exception as e:
                        logger.error(f"Redis error during logout: {e}")
            except Exception as e:
                logger.error(f"Error during token cleanup: {e}")

        return LogoutResult(success=True, session_cleared=True, user_id=user_id)
