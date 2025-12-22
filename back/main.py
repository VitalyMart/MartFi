import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .config import settings
from .database import create_tables
from .core.logger import logger
from .routes.auth import router as auth_router
from .routes.main import router as main_router
from .routes.market import router as market_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    logger.info("Application started successfully")
    yield
    logger.info("Application shutting down")

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    SessionMiddleware,
    secret_key=settings.SECRET_KEY,
    session_cookie="sessionid",
    max_age=3600,
    same_site="lax",
    https_only=not settings.DEBUG,
)

frontend_path = os.path.join(os.path.dirname(__file__), "..", "front")
static_path = os.path.join(frontend_path, "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

app.include_router(auth_router)
app.include_router(main_router)
app.include_router(market_router)