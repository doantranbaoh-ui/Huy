# --- shared/models.py ---
"""
Shared data models for all services
SentinelCore compliant — unified data structures
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict
import json

@dataclass
class Proxy:
    ip: str
    port: int
    protocol: str = "http"
    country: Optional[str] = None
    speed: float = 0.0
    is_alive: bool = True
    last_checked: Optional[str] = None
    fail_count: int = 0
    anonymity: str = "unknown"
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "speed": self.speed,
            "is_alive": self.is_alive,
            "last_checked": self.last_checked,
            "fail_count": self.fail_count,
            "anonymity": self.anonymity
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Proxy':
        return cls(
            ip=data.get("ip"),
            port=data.get("port"),
            protocol=data.get("protocol", "http"),
            country=data.get("country"),
            speed=data.get("speed", 0.0),
            is_alive=data.get("is_alive", True),
            last_checked=data.get("last_checked"),
            fail_count=data.get("fail_count", 0),
            anonymity=data.get("anonymity", "unknown")
        )
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"

@dataclass
class ProxyStats:
    total: int = 0
    alive: int = 0
    dead: int = 0
    last_update: Optional[str] = None
    uptime_seconds: int = 0
    
    def to_dict(self) -> dict:
        return {
            "total": self.total,
            "alive": self.alive,
            "dead": self.dead,
            "last_update": self.last_update,
            "uptime_seconds": self.uptime_seconds
        }

# --- shared/redis_client.py ---
"""
Redis client for cross-service communication
"""

import os
import json
import redis.asyncio as redis
from typing import Optional, List, Dict, Any
from datetime import datetime
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
        await self.client.expire(key, 3600)  # 1 hour TTL
        
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
        # Remove from alive set
        all_alive = await self.client.smembers(alive_key)
        for item in all_alive:
            data = json.loads(item)
            if data.get("ip") == proxy_id:
                await self.client.srem(alive_key, item)
