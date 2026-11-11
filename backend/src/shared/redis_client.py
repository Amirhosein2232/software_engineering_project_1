from redis.asyncio import Redis

from src.shared.config import settings

redis_client: Redis = Redis.from_url(
    settings.redis_url,
    decode_responses=True,   # returns str instead of bytes
)