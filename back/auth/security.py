# back/auth/security.py
import secrets
import asyncio
import hmac
from fastapi import Request, Form, HTTPException
from passlib.context import CryptContext
from typing import Optional
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

async def verify_password(plain_password: str, hashed_password: str) -> bool:
    start = asyncio.get_event_loop().time()
    loop = asyncio.get_event_loop()
    is_valid = await loop.run_in_executor(None, pwd_context.verify, plain_password, hashed_password)
    elapsed = asyncio.get_event_loop().time() - start
    fixed_delay = 0.5
    if elapsed < fixed_delay:
        await asyncio.sleep(fixed_delay - elapsed)
    return is_valid

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)