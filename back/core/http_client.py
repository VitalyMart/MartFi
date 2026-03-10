import aiohttp
from contextlib import asynccontextmanager
from ..core.logger import logger

_http_session = None

async def init_http_session():
    global _http_session
    if _http_session is None:
        _http_session = aiohttp.ClientSession()
        logger.info("HTTP session created")
    return _http_session

async def close_http_session():
    global _http_session
    if _http_session:
        await _http_session.close()
        logger.info("HTTP session closed")
        _http_session = None

def get_http_session() -> aiohttp.ClientSession:
    if _http_session is None:
        raise RuntimeError("HTTP session not initialized. Call init_http_session() first.")
    return _http_session

@asynccontextmanager
async def http_session_lifespan():
    await init_http_session()
    yield
    await close_http_session()