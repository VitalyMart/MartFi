from fastapi import Depends, Request
from sqlalchemy.orm import Session

from .services import verify_token
from ..database import get_db
from ..database.models import User
from ..core.logger import logger


def get_current_user(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = verify_token(token)
    if not payload:
        return None

    if payload.get("type") != "access":
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    try:
        user = db.query(User).filter(User.id == int(user_id)).first()
        return user
    except (ValueError, TypeError) as e:
        logger.error(f"User ID conversion error: {e}")
        return None
