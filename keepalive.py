# --- keep_alive/keepalive.py ---
"""
Keep-alive service for Render
Deploy as Worker or Cron Job
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta
import aiohttp
import redis.asyncio as redis

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Config ---
HEARTBEAT_INTERVAL = 30  # seconds
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
WEBHOOK_URL = os.getenv("SOC_WEBHOOK_URL", "")

class KeepAliveService:
    """Keep-alive and monitoring service"""
    
    def __init__(self):
        self.redis = None
        self.start_time = datetime.now()
        self.heartbeat_count = 0
        self.is_running = False
        
    async def connect_redis(self):
        """Connect to Redis"""
        try:
            self.redis = redis.from_url(REDIS_URL, decode_responses=True)
            await self.redis.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
            
    async def start(self):
        """Start keep-alive service"""
        if not await self.connect_redis():
            logger.error("Cannot start without Redis")
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
        """Send heartbeat"""
        self.heartbeat_count += 1
        
        # Update status in Redis
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
        
        # Check proxy manager health
        await self._check_services()
        
        logger.debug(f"💓 Heartbeat #{self.heartbeat_count}")
        
        # Send to SOC every 5 heartbeats
        if self.heartbeat_count % 5 == 0 and WEBHOOK_URL:
            await self._send_soc_event(status)
            
    async def _check_services(self):
        """Check if services are healthy"""
        try:
            async with aiohttp.ClientSession() as session:
                # Check proxy manager
                try:
                    async with session.get(
                        "http://localhost:8000/health",
                        timeout=5.0
                    ) as resp:
                        if resp.status == 200:
                            await self.redis.set("nexus:service:proxy_manager", "healthy")
                        else:
                            await self.redis.set("nexus:service:proxy_manager", "unhealthy")
                except:
                    await self.redis.set("nexus:service:proxy_manager", "unreachable")
                    
        except Exception as e:
            logger.error(f"Service check error: {e}")
            
    async def _send_soc_event(self, data: dict):
        """Send event to SOC webhook"""
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
                
                async with session.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=5.0
                ) as resp:
                    if resp.status == 200:
                        logger.debug("✅ SOC event sent")
                    else:
                        logger.warning(f"SOC event failed: {resp.status}")
        except Exception as e:
            logger.error(f"SOC event error: {e}")
            
    async def stop(self):
        """Stop keep-alive service"""
        self.is_running = False
        if self.redis:
            await self.redis.close()
        logger.info("Keep-alive service stopped")

# --- Main ---
async def main():
    """Run keep-alive service"""
    service = KeepAliveService()
    
    try:
        await service.start()
    except KeyboardInterrupt:
        await service.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        await service.stop()

if __name__ == "__main__":
    asyncio.run(main())
