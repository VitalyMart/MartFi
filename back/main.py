from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from passlib.context import CryptContext
from .config import settings
from jose import JWTError, jwt
from datetime import datetime, timezone, timedelta
import os
import redis
import secrets
import re

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "front")
pages_path = os.path.join(os.path.dirname(__file__), "..", "front/templates")
static_path = os.path.join(os.path.dirname(__file__), "..", "front/static")

templates = Jinja2Templates(directory=pages_path)
app.mount("/static", StaticFiles(directory=static_path), name="static")

redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)

def generate_csrf_token() -> str:
    """Генерирует CSRF токен"""
    return secrets.token_urlsafe(32)

def validate_csrf_token(token: str, request: Request) -> bool:
    """Проверяет CSRF токен"""
    stored_token = request.session.get("csrf_token")
    return stored_token and secrets.compare_digest(token, stored_token)

def get_csrf_token(request: Request) -> str:
    """Получает или создает CSRF токен для сессии"""
    if "csrf_token" not in request.session:
        request.session["csrf_token"] = generate_csrf_token()
    return request.session["csrf_token"]

async def csrf_protect(request: Request, csrf_token: str = Form(...)):
    """Зависимость для проверки CSRF токена"""
    if not validate_csrf_token(csrf_token, request):
        raise HTTPException(status_code=403, detail="Invalid CSRF token")
    return True

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def validate_email(email: str) -> bool:
    """Валидация email адреса"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password: str) -> tuple[bool, str]:
    """Валидация пароля"""
    if len(password) < 8:
        return False, "Пароль должен содержать минимум 8 символов"
    if not any(c.isupper() for c in password):
        return False, "Пароль должен содержать хотя бы одну заглавную букву"
    if not any(c.islower() for c in password):
        return False, "Пароль должен содержать хотя бы одну строчную букву"
    if not any(c.isdigit() for c in password):
        return False, "Пароль должен содержать хотя бы одну цифру"
    return True, ""

def create_access_token(user_id: int):
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
        "aud": "martfi-app"
    }
    
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def verify_token(token: str):
    try:
        payload = jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            issuer="martfi-auth",
            audience="martfi-app"
        )
        return payload
    except JWTError:
        return None

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
    except (ValueError, TypeError):
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def is_rate_limited(email: str) -> bool:
    key = f"login_attempts:{email}"
    attempts = redis_client.get(key)
    return attempts and int(attempts) >= 5

def increment_login_attempts(email: str):
    key = f"login_attempts:{email}"
    redis_client.incr(key)
    redis_client.expire(key, 3600)

def clear_login_attempts(email: str):
    key = f"login_attempts:{email}"
    redis_client.delete(key)

@app.get("/")
async def root(request: Request, current_user = Depends(get_current_user)):
    if not current_user:
        return RedirectResponse("/login")
    return templates.TemplateResponse("index.html", {"request": request, "user": current_user})

@app.get("/login")
async def login_page(request: Request, current_user = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/")
    
    csrf_token = get_csrf_token(request)
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "csrf_token": csrf_token
    })

@app.get("/register")
async def register_page(request: Request, current_user = Depends(get_current_user)):
    if current_user:
        return RedirectResponse("/")
    
    csrf_token = get_csrf_token(request)
    
    return templates.TemplateResponse("register.html", {
        "request": request,
        "csrf_token": csrf_token
    })

@app.post("/register")
async def register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    full_name: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),  
    db: Session = Depends(get_db)
):
    
    if not validate_email(email):
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "Некорректный формат email",
            "csrf_token": csrf_token
        })
    
    is_valid_password, password_error = validate_password(password)
    if not is_valid_password:
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": password_error,
            "csrf_token": csrf_token
        })
    
    if len(full_name.strip()) < 2:
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "ФИО должно содержать минимум 2 символа",
            "csrf_token": csrf_token
        })
    
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("register.html", {
            "request": request, 
            "error": "Email уже зарегистрирован",
            "csrf_token": csrf_token
        })
    
    hashed_password = get_password_hash(password)
    user = User(
        email=email.lower().strip(),  
        hashed_password=hashed_password, 
        full_name=full_name.strip()
    )
    db.add(user)
    db.commit()
    
    return RedirectResponse("/login?registered=true", status_code=303)

@app.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_verified: bool = Depends(csrf_protect),  
    db: Session = Depends(get_db)
):
    
    email = email.lower().strip()
    
    if not validate_email(email):
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный email или пароль",
            "csrf_token": csrf_token
        })
    
    if is_rate_limited(email):
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Слишком много попыток входа. Попробуйте через час",
            "csrf_token": csrf_token
        })
    
    user = db.query(User).filter(User.email == email).first()
    
    dummy_hash = pwd_context.hash(secrets.token_urlsafe(32))
    hash_to_check = user.hashed_password if user else dummy_hash
    
    is_valid = pwd_context.verify(password, hash_to_check)
    
    if not user or not is_valid:
        increment_login_attempts(email)
        csrf_token = get_csrf_token(request)
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный email или пароль",
            "csrf_token": csrf_token
        })
    
    clear_login_attempts(email)
    access_token = create_access_token(user.id)
    
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    return response

@app.post("/logout")
async def logout(request: Request, csrf_verified: bool = Depends(csrf_protect)): 
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(
        key="access_token",
        httponly=True,
        secure=not settings.DEBUG,
        samesite="lax"
    )
    return response
