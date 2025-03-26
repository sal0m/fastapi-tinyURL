import redis.asyncio as redis
import json
import os

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:5370")
redis = redis.from_url(REDIS_URL, decode_responses=True)

async def set_cache(key: str, value: dict, expire: int = 3600):
    await redis.set(key, json.dumps(value), ex=expire)

async def get_cache(key: str):
    data = await redis.get(key)
    return json.loads(data) if data else None

async def delete_cache(key: str):
    await redis.delete(key)
