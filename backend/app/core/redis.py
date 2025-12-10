import redis
from redis.asyncio import Redis, from_url

from app.core.config import settings

_redis_client: Redis = None
_redis_client_sync: redis.Redis = None


def get_redis_client() -> Redis:
    """
    Get async Redis client for FastAPI endpoints.
    
    Returns:
        Async Redis client instance
    """
    global _redis_client
    if _redis_client is None:
        _redis_client = from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS
        )
    return _redis_client


def get_redis_client_sync() -> redis.Redis:
    """
    Get synchronous Redis client for Celery workers.
    
    Returns:
        Synchronous Redis client instance
    """
    global _redis_client_sync
    if _redis_client_sync is None:
        _redis_client_sync = redis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=settings.REDIS_MAX_CONNECTIONS
        )
    return _redis_client_sync


async def close_redis_client():
    """Close async Redis client connection."""
    global _redis_client
    if _redis_client:
        await _redis_client.close()
        _redis_client = None


def close_redis_client_sync():
    """Close synchronous Redis client connection."""
    global _redis_client_sync
    if _redis_client_sync:
        _redis_client_sync.close()
        _redis_client_sync = None
