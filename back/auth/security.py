import secrets
import time
from fastapi import Request, Form, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import Tuple
import hmac

from ..database.models import User
from ..core.logger import logger

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

def generate_fake_hash() -> str:
    return pwd_context.hash(secrets.token_urlsafe(32))

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, request: Request) -> bool:
    stored_token = request.session.get("csrf_token")
    referer = request.headers.get("referer")
    
    if referer and not referer.startswith(str(request.base_url)):
        logger.warning(f"Invalid Referer header: {referer}")
        return False
    
    return bool(stored_token and hmac.compare_digest(token, stored_token))

def get_csrf_token(request: Request) -> str:
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = generate_csrf_token()
    return request.session["csrf_token"]

async def csrf_protect(request: Request, csrf_token: str = Form(...)):
    if not validate_csrf_token(csrf_token, request):
        logger.warning("CSRF token validation failed")
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    request.session.pop("csrf_token", None)
    return True

def validate_password(password: str) -> Tuple[bool, str]:
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"
    if len(password) > 64:
        return False, "Пароль слишком длинный"
    if not any(c.isupper() for c in password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not any(c.islower() for c in password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    if not any(c.isdigit() for c in password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, ""

def verify_user_password(db: Session, email: str, password: str):
    start_time = time.time()
    
    user = db.query(User).filter(User.email == email).first()
    
    fake_hash = generate_fake_hash()
    provided_hash = user.hashed_password if user else fake_hash
    
    is_valid = pwd_context.verify(password, provided_hash)
    
    execution_time = time.time() - start_time
    fixed_delay = 0.05
    
    if execution_time < fixed_delay:
        time.sleep(fixed_delay - execution_time)
    
    return user if (user and is_valid) else None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    start_time = time.time()
    is_valid = pwd_context.verify(plain_password, hashed_password)
    
    execution_time = time.time() - start_time
    fixed_delay = 0.5
    
    if execution_time < fixed_delay:
        time.sleep(fixed_delay - execution_time)
    
    return is_valid

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)