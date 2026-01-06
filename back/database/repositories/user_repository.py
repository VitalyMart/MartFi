from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from ..models.user import User as ORMUser
from ...contracts.repositories import IUserRepository
from ...auth.entities.user import User as DomainUser
from ...auth.security import get_password_hash, verify_password
from ...core.logger import logger

class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    def _to_domain(self, orm_user: ORMUser) -> DomainUser:
        return DomainUser(
            id=orm_user.id,
            email=orm_user.email,
            full_name=orm_user.full_name,
            hashed_password=orm_user.hashed_password,
        )

    def get_by_id(self, user_id: int) -> Optional[DomainUser]:
        orm_user = self.db.query(ORMUser).filter(ORMUser.id == user_id).first()
        return self._to_domain(orm_user) if orm_user else None

    def get_by_email(self, email: str) -> Optional[DomainUser]:
        orm_user = self.db.query(ORMUser).filter(ORMUser.email == email).first()
        return self._to_domain(orm_user) if orm_user else None

    def email_exists(self, email: str) -> bool:
        return self.db.query(ORMUser.id).filter(ORMUser.email == email).first() is not None

    def create(self, email: str, password: str, full_name: str) -> DomainUser:
        try:
            hashed_password = get_password_hash(password)
            orm_user = ORMUser(
                email=email,
                hashed_password=hashed_password,
                full_name=full_name.strip(),
            )
            self.db.add(orm_user)
            self.db.commit()
            self.db.refresh(orm_user)
            logger.info(f"User created successfully: {email}")
            return self._to_domain(orm_user)
        except IntegrityError:
            self.db.rollback()
            logger.warning(f"Email already exists: {email}")
            raise ValueError(f"Email already registered: {email}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user {email}: {e}")
            raise RuntimeError(f"Failed to create user: {str(e)}")

    def verify_credentials(self, email: str, password: str) -> Optional[DomainUser]:
        user = self.get_by_email(email)
        if not user:
            return None
        if verify_password(password, user.hashed_password):
            return user
        return None