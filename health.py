# --- health_check/health.py ---
"""
Health check endpoint
"""

from fastapi import FastAPI
from datetime import datetime
import os
import redis
import json

app = FastAPI(title="Health Check Service")

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

@app.get("/")
@app.get("/health")
async def health_check():
    redis_status = "unknown"
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"
        
    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": redis_status
        },
        "service": "nexus-healthcheck",
        "version": "2.0.0"
    }

@app.get("/stats")
async def get_stats():
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        stats_data = r.get("nexus:stats")
        stats = json.loads(stats_data) if stats_data else {}
        return {
            "stats": stats,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
