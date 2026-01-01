from dataclasses import dataclass
from typing import Optional


@dataclass
class RegistrationResult:
    success: bool
    user_id: Optional[int] = None
    error_message: Optional[str] = None
    redirect_path: Optional[str] = None


@dataclass
class LoginResult:
    success: bool
    user_id: Optional[int] = None
    access_token: Optional[str] = None
    error_message: Optional[str] = None


@dataclass
class LogoutResult:
    success: bool
    session_cleared: bool = False
    user_id: Optional[int] = None


@dataclass
class PageContextResult:
    template_name: str
    template_data: dict
    redirect_path: Optional[str] = None