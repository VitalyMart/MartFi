import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from sqlalchemy.orm import Session
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

def is_email_registered(db: Session, email: str) -> bool:
    return db.query(User).filter(User.email == email).first() is not None

def create_user(db: Session, email: str, password: str, full_name: str) -> User:
    try:
        hashed_password = get_password_hash(password)
        user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=full_name.strip(),
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"User created successfully: {email}")
        return user
    except IntegrityError:
        db.rollback()
        logger.warning(f"Email already exists: {email}")
        raise EmailAlreadyExistsError("Email уже зарегистрирован")
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating user {email}: {e}")
        raise UserCreationError(f"Ошибка создания пользователя: {str(e)}")