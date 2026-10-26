# keepalive.py - HTTP server giữ Render không ngủ, hỗ trợ /health /ping /token /status
# Yêu cầu: pip install aiohttp

import os
import time
import logging
from aiohttp import web

log = logging.getLogger("keepalive")
PORT = int(os.environ.get("PORT", "8080"))

BOT_TOKEN = "6367532329:AAF4F5XEYrdn121tbxmnxdHLDu7WzuePKkA"

status = {
    "running": False,
    "bot_ready": False,
    "last_ping": None,
    "started_at": None,
}


async def handle_root(request):
    # Endpoint gốc trả text đơn giản để monitor đọc
    return web.Response(text="alive", content_type="text/plain")


async def handle_ping(request):
    # Cập nhật thời điểm ping gần nhất
    status["last_ping"] = time.time()
    return web.json_response({
        "status": "ok",
        "running": status["running"],
        "bot_ready": status["bot_ready"],
        "last_ping": status["last_ping"],
        "started_at": status["started_at"],
    })


async def handle_health(request):
    # Health check cho Render: luôn 200 nếu server sống
    return web.json_response({
        "status": "ok",
        "running": status["running"],
        "bot_ready": status["bot_ready"],
    })


async def handle_token(request):
    # Xác nhận token đã nạp (không trả token thật)
    return web.json_response({"bot_token_set": bool(BOT_TOKEN)})


async def handle_status(request):
    # Trả trạng thái tổng hợp, phục vụ debug từ trình duyệt
    uptime = None
    if status["started_at"]:
        uptime = int(time.time() - status["started_at"])
    return web.json_response({
        "status": "ok",
        "running": status["running"],
        "bot_ready": status["bot_ready"],
        "uptime": uptime,
        "last_ping": status["last_ping"],
        "started_at": status["started_at"],
    })


def create_app():
    # Đăng ký toàn bộ route
    app = web.Application()
    app.router.add_get("/", handle_root)
    app.router.add_get("/ping", handle_ping)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/token", handle_token)
    app.router.add_get("/status", handle_status)
    return app


async def start_keepalive():
    # Mở cổng HTTP ngay lập tức, trước khi bot đăng nhập
    status["started_at"] = time.time()
    app = create_app()
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    status["running"] = True
    log.info(f"Keepalive mở cổng {PORT}")
    return runner


def mark_bot_ready():
    # Đánh dấu bot Telegram đã đăng nhập xong
    status["bot_ready"] = True
    log.info("Bot Telegram đã đăng nhập xong")
