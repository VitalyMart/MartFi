import logging
from .redis_client import redis_client

logger = logging.getLogger(__name__)


async def is_rate_limited(key: str) -> bool:
    try:
        attempts = await redis_client.get(key)  
        return attempts and int(attempts) >= 5
    except Exception as e:
        logger.error(f"Redis error in is_rate_limited: {e}")
        return False


async def increment_rate_limit(key: str):
    try:
        await redis_client.incr(key)  
        await redis_client.expire(key, 3600)  
    except Exception as e:
        logger.error(f"Redis error in increment_rate_limit: {e}")


async def clear_rate_limit(key: str):
    try:
        await redis_client.delete(key)  
    except Exception as e:
        logger.error(f"Redis error in clear_rate_limit: {e}")


async def is_registration_rate_limited(ip: str) -> bool:
    return await is_rate_limited(f"reg_attempts:{ip}")  


async def increment_registration_attempts(ip: str):
    await increment_rate_limit(f"reg_attempts:{ip}")  


def get_login_rate_key(email: str) -> str:
    return f"login_attempts:{email}"