from typing import Optional
from ..dto.auth import RegistrationResult, LoginResult, LogoutResult, PageContextResult, RegistrationForm, LoginForm
from ..auth.exceptions import (
    RateLimitException,
    InvalidCredentialsException,
    UserAlreadyExistsException,
    ValidationException,
)
from ..auth.entities.user import User as DomainUser
from ..contracts.repositories import IUserRepository
from ..contracts.security import ISecurityService
from ..auth.token_service import create_access_token, verify_token
from ..auth.security import get_password_hash, verify_password
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
from email_validator import validate_email, EmailNotValidError


class AuthService:
    def __init__(self, security_service: ISecurityService, user_repo: IUserRepository):
        self.security_service = security_service
        self.user_repo = user_repo

    async def get_current_user(self, token: str | None) -> Optional[DomainUser]:
        if not token:
            return None
        payload = verify_token(token)
        if not payload or payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if not user_id:
            return None
        try:
            return self.user_repo.get_by_id(int(user_id))
        except (ValueError, TypeError):
            return None

    async def get_login_page_context(self, request, current_user: Optional[DomainUser]) -> PageContextResult:
        if current_user:
            return PageContextResult(
                template_name="",
                template_data={},
                redirect_path="/"
            )
        csrf_token = await self.security_service.get_csrf_token(request)
        return PageContextResult(
            template_name="login.html",
            template_data={
                "request": request,
                "csrf_token": csrf_token,
            },
        )

    async def get_register_page_context(self, request, current_user: Optional[DomainUser]) -> PageContextResult:
        if current_user:
            return PageContextResult(
                template_name="",
                template_data={},
                redirect_path="/"
            )
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
        
        try:
            registration_form = RegistrationForm(
                email=email,
                password=password,
                full_name=full_name
            )
        except Exception as e:
            increment_registration_attempts(client_ip)
            raise ValidationException(str(e))
        
        try:
            validated_email = validate_email(registration_form.email).email
        except EmailNotValidError:
            increment_registration_attempts(client_ip)
            raise ValidationException("Invalid email format")
        
        if self.user_repo.email_exists(validated_email):
            increment_registration_attempts(client_ip)
            raise UserAlreadyExistsException("Email already registered")
        
        try:
            user = self.user_repo.create(validated_email, registration_form.password, registration_form.full_name)
            logger.info(f"User registered successfully: {validated_email}")
            return RegistrationResult(
                success=True, 
                user_id=user.id, 
                redirect_path="/login?registered=true"
            )
        except Exception as e:
            logger.error(f"User creation error for {validated_email}: {e}")
            increment_registration_attempts(client_ip)
            raise

    async def login_user(self, email: str, password: str, client_ip: str) -> LoginResult:
        try:
            login_form = LoginForm(email=email, password=password)
            validated_email = validate_email(login_form.email).email
        except Exception as e:
            raise InvalidCredentialsException("Invalid email or password")
            
        login_key = get_login_rate_key(validated_email)
        if is_rate_limited(login_key):
            logger.warning(f"Login rate limit exceeded for: {email}")
            raise RateLimitException("Too many login attempts")
        
        user = self.user_repo.verify_credentials(validated_email, login_form.password)
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
        return LoginResult(
            success=True, 
            user_id=user.id, 
            access_token=access_token
        )

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
        return LogoutResult(
            success=True, 
            session_cleared=True, 
            user_id=user_id
        )