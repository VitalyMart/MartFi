import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.exc import IntegrityError
from ..config import settings
from ..database.models import User
from .security import get_password_hash
from ..core.logger import logger


class UserServiceError(Exception):
    pass


class EmailAlreadyExistsError(UserServiceError):
    pass


class UserCreationError(UserServiceError):
    pass


def create_access_token(user_id: int, session_id: Optional[str] = None) -> str:
    if not session_id:
        session_id = secrets.token_urlsafe(32)
    
    jwt_id = secrets.token_urlsafe(16)
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": jwt_id,
        "type": "access",
        "iss": "martfi-auth",
        "aud": "martfi-app",
        "session_id": session_id
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            issuer="martfi-auth",
            audience="martfi-app"
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decoding error: {e}")
        return None