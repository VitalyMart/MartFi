import logging
from .redis_client import redis_client

logger = logging.getLogger(__name__)


def is_rate_limited(key: str) -> bool:
    try:
        attempts = redis_client.get(key)
        return attempts and int(attempts) >= 5
    except Exception as e:
        logger.error(f"Redis error in is_rate_limited: {e}")
        return False


def increment_rate_limit(key: str):
    try:
        redis_client.incr(key)
        redis_client.expire(key, 3600)
    except Exception as e:
        logger.error(f"Redis error in increment_rate_limit: {e}")


def clear_rate_limit(key: str):
    try:
        redis_client.delete(key)
    except Exception as e:
        logger.error(f"Redis error in clear_rate_limit: {e}")


def is_registration_rate_limited(ip: str) -> bool:
    return is_rate_limited(f"reg_attempts:{ip}")


def increment_registration_attempts(ip: str):
    increment_rate_limit(f"reg_attempts:{ip}")


def get_login_rate_key(email: str) -> str:
    return f"login_attempts:{email}"
