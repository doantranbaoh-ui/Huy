# --- keep_alive/keepalive.py ---
"""
Keep-alive service for Render
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime
import aiohttp
import redis.asyncio as redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WEBHOOK_URL = os.getenv("SOC_WEBHOOK_URL", "")
HEARTBEAT_INTERVAL = 30

class KeepAliveService:
    def __init__(self):
        self.redis = None
        self.start_time = datetime.now()
        self.heartbeat_count = 0
        self.is_running = False
        
    async def connect_redis(self):
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
            
    async def start(self):
        if not await self.connect_redis():
            return
            
        self.is_running = True
        logger.info("💓 Keep-alive service started")
        
        while self.is_running:
            try:
                await self._heartbeat()
                await asyncio.sleep(HEARTBEAT_INTERVAL)
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
                
    async def _heartbeat(self):
        self.heartbeat_count += 1
        
        status = {
            "service": "nexus-keepalive",
            "status": "running",
            "heartbeats": self.heartbeat_count,
            "uptime_seconds": int((datetime.now() - self.start_time).total_seconds()),
            "last_heartbeat": datetime.now().isoformat(),
            "pid": os.getpid()
        }
        
        await self.redis.set("nexus:keepalive:status", json.dumps(status))
        await self.redis.expire("nexus:keepalive:status", 60)
        
        logger.debug(f"💓 Heartbeat #{self.heartbeat_count}")
        
        if self.heartbeat_count % 5 == 0 and WEBHOOK_URL:
            await self._send_soc_event(status)
            
    async def _send_soc_event(self, data: dict):
        if not WEBHOOK_URL:
            return
            
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    "source": "keepalive",
                    "timestamp": datetime.now().isoformat(),
                    "data": data,
                    "audit_trail": "SentinelCore_v2"
                }
                async with session.post(WEBHOOK_URL, json=payload, timeout=5.0) as resp:
                    if resp.status == 200:
                        logger.debug("✅ SOC event sent")
        except Exception as e:
            logger.error(f"SOC event error: {e}")
            
    async def stop(self):
        self.is_running = False
        if self.redis:
            await self.redis.close()
        logger.info("Keep-alive service stopped")

async def main():
    service = KeepAliveService()
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())
