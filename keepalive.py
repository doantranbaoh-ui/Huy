# --- keepalive/keepalive.py ---
"""
Keep-alive service
"""

import asyncio
import os
import sys
import json
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.redis_client import RedisManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KeepAlive:
    def __init__(self):
        self.redis = RedisManager()
        self.running = False
        
    async def start(self):
        await self.redis.connect()
        self.running = True
        logger.info("💓 Keep-alive started")
        
        while self.running:
            await self.redis.client.set(
                "nexus:keepalive",
                json.dumps({
                    "time": datetime.now().isoformat(),
                    "status": "alive"
                })
            )
            await asyncio.sleep(30)

async def main():
    service = KeepAlive()
    try:
        await service.start()
    except KeyboardInterrupt:
        service.running = False

if __name__ == "__main__":
    asyncio.run(main())
