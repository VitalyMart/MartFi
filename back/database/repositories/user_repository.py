from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models.user import User
from ...auth.security import get_password_hash, verify_password
from ...core.logger import logger


class UserRepository:
    def __init__(self, db: Session):
        self.db = db
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        return self.db.query(User).filter(User.id == user_id).first()
    
    def get_by_email(self, email: str) -> Optional[User]:
        return self.db.query(User).filter(User.email == email).first()
    
    def email_exists(self, email: str) -> bool:
        return self.get_by_email(email) is not None
    
    def create(self, email: str, password: str, full_name: str) -> User:
        try:
            hashed_password = get_password_hash(password)
            user = User(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name.strip(),
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)
            logger.info(f"User created successfully: {email}")
            return user
        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Email already exists: {email}")
            raise ValueError(f"Email already registered: {email}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user {email}: {e}")
            raise RuntimeError(f"Failed to create user: {str(e)}")
    
    def verify_credentials(self, email: str, password: str) -> Optional[User]:
        user = self.get_by_email(email)
        if not user:
            return None
        if verify_password(password, user.hashed_password):
            return user
        return None