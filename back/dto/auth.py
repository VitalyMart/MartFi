from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, field_validator


class RegistrationResult(BaseModel):
    success: bool
    user_id: Optional[int] = None
    error_message: Optional[str] = None
    redirect_path: Optional[str] = None


class LoginResult(BaseModel):
    success: bool
    user_id: Optional[int] = None
    access_token: Optional[str] = None
    error_message: Optional[str] = None


class LogoutResult(BaseModel):
    success: bool
    session_cleared: bool = False
    user_id: Optional[int] = None


class PageContextResult(BaseModel):
    template_name: str
    template_data: Dict[str, Any]
    redirect_path: Optional[str] = None


class RegistrationForm(BaseModel):
    email: EmailStr
    password: str
    full_name: str
    
    @field_validator('password')
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        if len(v) > 64:
            raise ValueError('Пароль слишком длинный')
        if not any(c.isupper() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну заглавную букву')
        if not any(c.islower() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну строчную букву')
        if not any(c.isdigit() for c in v):
            raise ValueError('Пароль должен содержать хотя бы одну цифру')
        return v
    
    @field_validator('full_name')
    def validate_full_name(cls, v):
        v = v.strip()
        if len(v) < 4:
            raise ValueError('ФИО должно содержать минимум 4 символа')
        if len(v) > 100:
            raise ValueError('ФИО не может быть длиннее 100 символов')
        return v


class LoginForm(BaseModel):
    email: EmailStr
    password: str