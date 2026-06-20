# --- health/health.py ---
"""
Health check
"""

import os
import sys
import json
from fastapi import FastAPI
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.redis_client import RedisManager

app = FastAPI()
redis_manager = RedisManager()

@app.on_event("startup")
async def startup():
    await redis_manager.connect()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "time": datetime.now().isoformat()
    }

@app.get("/stats")
async def stats():
    stats = await redis_manager.get_stats()
    return stats

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
