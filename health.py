# --- health_check/health.py ---
"""
Health check endpoint for Render
Deploy as Web Service on port 8080
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
    """Health check endpoint"""
    redis_status = "unknown"
    
    try:
        r = redis.from_url(REDIS_URL, decode_responses=True)
        r.ping()
        redis_status = "healthy"
    except:
        redis_status = "unhealthy"
        
    # Check proxy manager
    proxy_manager_status = "unknown"
    try:
        import httpx
        with httpx.Client() as client:
            resp = client.get("http://localhost:8000/health", timeout=3.0)
            if resp.status_code == 200:
                proxy_manager_status = "healthy"
            else:
                proxy_manager_status = "unhealthy"
    except:
        proxy_manager_status = "unreachable"
        
    return {
        "status": "healthy" if redis_status == "healthy" else "degraded",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "redis": redis_status,
            "proxy_manager": proxy_manager_status
        },
        "service": "nexus-healthcheck",
        "version": "2.0.0"
    }

@app.get("/stats")
async def get_stats():
    """Get overall statistics"""
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
