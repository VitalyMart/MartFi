import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

class Settings:
    SECRET_KEY = os.getenv("SECRET_KEY")
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY must be set in environment variables")
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL must be set in environment variables")
    
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
    ALGORITHM = os.getenv("ALGORITHM", "HS256")
    
    CSRF_TOKEN_EXPIRE_MINUTES = int(os.getenv("CSRF_TOKEN_EXPIRE_MINUTES", "30"))
    
    try:
        ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    except (TypeError, ValueError):
        ACCESS_TOKEN_EXPIRE_MINUTES = 30
        
    try:
        REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    except (TypeError, ValueError):
        REFRESH_TOKEN_EXPIRE_DAYS = 7
    
settings = Settings()