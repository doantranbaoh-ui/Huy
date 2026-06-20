# --- proxy_manager/manager.py ---
"""
Proxy Manager Core — handles proxy loading, validation, storage
NO EXTERNAL DEPENDENCIES — all local
"""

import asyncio
import aiohttp
import logging
import re
import random
import json
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
import sys
import os

# Import local modules only
from redis_client import RedisManager

logger = logging.getLogger(__name__)

# --- Local Models (no external package needed) ---
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
            ip=data.get("ip", ""),
            port=data.get("port", 0),
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

class ProxyManager:
    """Main proxy management engine"""
    
    def __init__(self, max_proxies: int = 5000):
        self.max_proxies = max_proxies
        self.redis = RedisManager()
        self.stats = ProxyStats()
        self._initialized = False
        
    async def initialize(self):
        """Initialize manager with Redis connection"""
        if self._initialized:
            return
            
        await self.redis.connect()
        self._initialized = True
        logger.info("ProxyManager initialized")
        
    async def load_from_file(self, content: str) -> int:
        """Load proxies from file content"""
        lines = content.strip().split('\n')
        count = 0
        
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
                
            proxy = self._parse_proxy(line.strip())
            if proxy:
                await self.redis.set_proxy(
                    f"{proxy.ip}:{proxy.port}",
                    proxy.to_dict()
                )
                count += 1
                
        await self._update_stats()
        logger.info(f"Loaded {count} proxies")
        return count
        
    async def load_from_url(self, url: str) -> int:
        """Load proxies from URL"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        return 0
                    content = await resp.text()
                    return await self.load_from_file(content)
        except Exception as e:
            logger.error(f"Failed to load from URL: {e}")
            return 0
            
    def _parse_proxy(self, line: str) -> Optional[Proxy]:
        """Parse proxy line"""
        line = line.strip()
        
        patterns = [
            r'^(https?|socks[45])://([^:]+):(\d+)$',
            r'^([^:]+):(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 3:
                    protocol, ip, port = match.groups()
                else:
                    ip, port = match.groups()
                    protocol = "http"
                    
                try:
                    port = int(port)
                    if 1 <= port <= 65535:
                        return Proxy(ip=ip, port=port, protocol=protocol)
                except ValueError:
                    continue
        return None
        
    async def validate_proxy(self, proxy_data: dict) -> bool:
        """Validate a single proxy"""
        proxy = Proxy.from_dict(proxy_data)
        
        try:
            url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
            start = datetime.now()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=url,
                    timeout=5,
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        proxy.is_alive = True
                        proxy.speed = (datetime.now() - start).total_seconds() * 1000
                        proxy.last_checked = datetime.now().isoformat()
                        proxy.fail_count = 0
                        
                        await self.redis.set_proxy(
                            f"{proxy.ip}:{proxy.port}",
                            proxy.to_dict()
                        )
                        await self.redis.add_alive_proxy(proxy.to_dict())
                        return True
                        
        except Exception:
            proxy.is_alive = False
            proxy.fail_count += 1
            await self.redis.set_proxy(
                f"{proxy.ip}:{proxy.port}",
                proxy.to_dict()
            )
            return False
            
    async def validate_all(self, max_concurrent: int = 50) -> Dict:
        """Validate all proxies"""
        proxies = await self.redis.get_all_proxies()
        if not proxies:
            return {"total": 0, "validated": 0}
            
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_one(proxy_data):
            async with semaphore:
                return await self.validate_proxy(proxy_data)
                
        tasks = [validate_one(p) for p in proxies]
        results = await asyncio.gather(*tasks)
        
        await self._update_stats()
        
        return {
            "total": len(proxies),
            "validated": sum(1 for r in results if r)
        }
        
    async def _update_stats(self):
        """Update statistics in Redis"""
        proxies = await self.redis.get_all_proxies()
        alive = await self.redis.get_alive_proxies()
        
        stats = ProxyStats(
            total=len(proxies),
            alive=len(alive),
            dead=len(proxies) - len(alive),
            last_update=datetime.now().isoformat()
        )
        
        await self.redis.set_stats(stats.to_dict())
        self.stats = stats
        
    async def get_proxy_for_scan(self) -> Optional[dict]:
        """Get best proxy for scanning"""
        alive = await self.redis.get_alive_proxies()
        if not alive:
            return None
            
        alive.sort(key=lambda x: x.get("speed", float('inf')))
        return alive[0] if alive else None
        
    async def get_stats(self) -> dict:
        """Get current statistics"""
        await self._update_stats()
        return await self.redis.get_stats()
        
    async def cleanup(self):
        """Clean up resources"""
        await self.redis.disconnect()
