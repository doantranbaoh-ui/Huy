# --- app/redis_client.py ---
"""
Redis client for cross-service communication
"""

import os
import json
import redis.asyncio as redis
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class RedisManager:
    """Redis client for proxy data sharing between services"""
    
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.client: Optional[redis.Redis] = None
        self.prefix = os.getenv("REDIS_PREFIX", "nexus:")
        
    async def connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
            
    async def disconnect(self):
        """Disconnect from Redis"""
        if self.client:
            await self.client.close()
            logger.info("Disconnected from Redis")
            
    async def set_proxy(self, proxy_id: str, proxy_data: dict):
        """Store proxy in Redis"""
        key = f"{self.prefix}proxy:{proxy_id}"
        await self.client.hset(key, mapping=proxy_data)
        await self.client.expire(key, 3600)
        
    async def get_proxy(self, proxy_id: str) -> Optional[dict]:
        """Get proxy from Redis"""
        key = f"{self.prefix}proxy:{proxy_id}"
        data = await self.client.hgetall(key)
        return data if data else None
        
    async def get_all_proxies(self) -> List[dict]:
        """Get all proxies from Redis"""
        pattern = f"{self.prefix}proxy:*"
        keys = await self.client.keys(pattern)
        proxies = []
        for key in keys:
            data = await self.client.hgetall(key)
            if data:
                proxies.append(data)
        return proxies
        
    async def set_stats(self, stats: dict):
        """Store statistics"""
        key = f"{self.prefix}stats"
        await self.client.set(key, json.dumps(stats))
        await self.client.expire(key, 3600)
        
    async def get_stats(self) -> dict:
        """Get statistics"""
        key = f"{self.prefix}stats"
        data = await self.client.get(key)
        return json.loads(data) if data else {}
        
    async def add_alive_proxy(self, proxy: dict):
        """Add to alive proxy set"""
        key = f"{self.prefix}alive"
        await self.client.sadd(key, json.dumps(proxy))
        
    async def get_alive_proxies(self) -> List[dict]:
        """Get all alive proxies"""
        key = f"{self.prefix}alive"
        members = await self.client.smembers(key)
        return [json.loads(m) for m in members]
        
    async def remove_proxy(self, proxy_id: str):
        """Remove proxy from all sets"""
        key = f"{self.prefix}proxy:{proxy_id}"
        await self.client.delete(key)
        alive_key = f"{self.prefix}alive"
        all_alive = await self.client.smembers(alive_key)
        for item in all_alive:
            data = json.loads(item)
            if data.get("ip") == proxy_id:
                await self.client.srem(alive_key, item)
