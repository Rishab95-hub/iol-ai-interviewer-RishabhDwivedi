"""
Redis client configuration
"""
from typing import Optional
from redis.asyncio import Redis
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    """Get Redis client instance"""
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True,
        )
    return redis_client


async def close_redis() -> None:
    """Close Redis connection"""
    global redis_client
    if redis_client:
        await redis_client.close()
        redis_client = None
