"""
Synchronous Redis client for Celery workers.
Workers are sync — can't use aioredis.
"""
import redis as sync_redis
from app.core.config import settings

redis_client = sync_redis.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)
