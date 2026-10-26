# keepalive.py - HTTP server giữ Render không ngủ
# Yêu cầu: pip install aiohttp

import os
import time
import logging
from aiohttp import web

log = logging.getLogger("keepalive")
PORT = int(os.environ.get("PORT", "8080"))

status = {"running": False, "last_ping": None, "started_at": None}


async def handle_ping(request):
    status["last_ping"] = time.time()
    return web.json_response({
        "status": "ok",
        "running": status["running"],
        "last_ping": status["last_ping"],
        "started_at": status["started_at"],
    })


async def handle_root(request):
    return web.Response(text="alive", content_type="text/plain")


def create_app():
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ping", handle_ping)
    app.router.add_get("/health", handle_ping)
    return app


async def start_keepalive():
    status["started_at"] = time.time()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    log.info(f"Keepalive chạy tại cổng {PORT}")
    return runner


def mark_running():
    status["running"] = True
