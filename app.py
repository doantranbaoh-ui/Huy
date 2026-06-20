# --- proxy_manager/app.py ---
"""
FastAPI web service for Proxy Manager
Deploy on Render as Web Service
"""

import os
import sys
import asyncio
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uvicorn
import tempfile

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from proxy_manager.manager import ProxyManager
from shared.models import Proxy

# --- Initialize ---
app = FastAPI(
    title="Nexus Proxy Manager API",
    description="Proxy management for legitimate security testing",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Models ---
class LoadResponse(BaseModel):
    success: bool
    count: int
    message: str

class StatsResponse(BaseModel):
    total: int
    alive: int
    dead: int
    last_update: Optional[str]
    uptime_seconds: int

class ValidateResponse(BaseModel):
    total: int
    validated: int
    timestamp: str

# --- Manager Instance ---
manager = ProxyManager()

@app.on_event("startup")
async def startup_event():
    """Initialize manager on startup"""
    await manager.initialize()
    print("✅ Proxy Manager API started")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    await manager.cleanup()

# --- Endpoints ---
@app.get("/")
async def root():
    return {
        "service": "Nexus Proxy Manager",
        "status": "running",
        "version": "2.0.0",
        "timestamp": datetime.now().isoformat()
    }

@app.post("/load/file")
async def load_file(file: UploadFile = File(...)) -> LoadResponse:
    """Load proxies from uploaded file"""
    if not file.filename.endswith('.txt'):
        raise HTTPException(400, "Only .txt files supported")
        
    content = await file.read()
    text = content.decode('utf-8')
    
    count = await manager.load_from_file(text)
    
    return LoadResponse(
        success=count > 0,
        count=count,
        message=f"Loaded {count} proxies"
    )

@app.post("/load/url")
async def load_url(url: str) -> LoadResponse:
    """Load proxies from URL"""
    count = await manager.load_from_url(url)
    
    return LoadResponse(
        success=count > 0,
        count=count,
        message=f"Loaded {count} proxies from URL"
    )

@app.post("/validate")
async def validate_proxies() -> ValidateResponse:
    """Validate all proxies"""
    result = await manager.validate_all()
    
    return ValidateResponse(
        total=result["total"],
        validated=result["validated"],
        timestamp=datetime.now().isoformat()
    )

@app.get("/stats")
async def get_stats() -> StatsResponse:
    """Get proxy statistics"""
    stats = await manager.get_stats()
    
    return StatsResponse(
        total=stats.get("total", 0),
        alive=stats.get("alive", 0),
        dead=stats.get("dead", 0),
        last_update=stats.get("last_update"),
        uptime_seconds=int((datetime.now() - datetime.now()).seconds)  # Will be fixed
    )

@app.get("/proxies/alive")
async def get_alive_proxies(limit: int = 100) -> List[dict]:
    """Get alive proxies"""
    alive = await manager.redis.get_alive_proxies()
    return alive[:limit]

@app.get("/proxies/random")
async def get_random_proxy() -> Optional[dict]:
    """Get random alive proxy"""
    alive = await manager.redis.get_alive_proxies()
    if not alive:
        return None
    import random
    return random.choice(alive)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    stats = await manager.get_stats()
    return {
        "status": "healthy",
        "service": "proxy_manager",
        "stats": stats,
        "timestamp": datetime.now().isoformat()
    }

# --- Main ---
if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
