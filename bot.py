#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Bot tự động cày view YouTube qua proxy xoay vòng, chạy 24/7.
- Tự động kiểm tra proxy sống/chết, loại bỏ proxy chết khỏi danh sách dùng nhưng GIỮ NGUYÊN file proxy.txt (không xóa)
- Khi upload file proxy mới, bot tự động merge (không ghi đè), chỉ thêm proxy mới
- Lưu proxy chết vào file dead_proxy.txt để tham khảo
- Web server giữ tiến trình tại 0.0.0.0:8080
Yêu cầu: python3, requests, pyrogram, asyncio, aiohttp
Cài đặt: pip install requests pyrogram asyncio aiohttp
"""

import asyncio
import random
import time
import requests
import os
import sys
import signal
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from aiohttp import web

# === THƯ VIỆN PYROGRAM ===
from pyrogram import Client, filters
from pyrogram.types import Message

# ===== CẤU HÌNH =====
API_ID = 123456  # Thay bằng API ID
API_HASH = "your_api_hash"  # Thay bằng API Hash
BOT_TOKEN = "your_bot_token"  # Thay bằng token
PROXY_FILE = "proxy.txt"
DEAD_PROXY_FILE = "dead_proxy.txt"
LOG_FILE = "bot_log.txt"
PID_FILE = "bot.pid"
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

# ===== CẤU HÌNH CÀY VIEW =====
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
MAX_WORKERS = 15
VIEW_RETRY = 2
PROXY_CHECK_INTERVAL = 1800  # 30 phút kiểm tra proxy
PROXY_RELOAD_INTERVAL = 3600  # 1 giờ reload proxy
HEARTBEAT_INTERVAL = 300  # 5 phút

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0",
]

# Biến toàn cục
PROXY_LIST = []           # Danh sách proxy ĐANG DÙNG (chỉ proxy sống)
PROXY_MASTER = set()      # Tất cả proxy từ file (bao gồm cả chết)
DEAD_PROXIES = set()      # Proxy đã bị loại
proxy_lock = Lock()
last_proxy_reload = 0
bot_running = True
view_stats = {"total": 0, "success": 0, "failed": 0}
start_time = time.time()

# ===== GHI LOG =====
def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except:
        pass

# ===== QUẢN LÝ TIẾN TRÌNH =====
def write_pid():
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

def remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

def check_already_running():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                pid = int(f.read().strip())
            try:
                os.kill(pid, 0)
                return True
            except OSError:
                os.remove(PID_FILE)
                return False
        except:
            return False
    return False

# ===== ĐỌC PROXY - MERGE KHÔNG XÓA =====
def load_proxies_from_file():
    """Đọc tất cả proxy từ file, KHÔNG xóa proxy cũ, chỉ thêm mới."""
    proxies = set()
    if os.path.exists(PROXY_FILE):
        with open(PROXY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.add(line)
    return proxies

def merge_new_proxies():
    """Merge proxy từ file vào master, không xóa proxy hiện có."""
    global PROXY_MASTER, PROXY_LIST, DEAD_PROXIES
    new_proxies = load_proxies_from_file()
    
    # Thêm proxy mới vào master
    added = 0
    for p in new_proxies:
        if p not in PROXY_MASTER:
            PROXY_MASTER.add(p)
            added += 1
    
    # Cập nhật PROXY_LIST: chỉ lấy proxy sống (loại bỏ dead)
    with proxy_lock:
        PROXY_LIST = [p for p in PROXY_MASTER if p not in DEAD_PROXIES]
    
    log_message(f"Merge proxy: thêm {added} mới, tổng master={len(PROXY_MASTER)}, sống={len(PROXY_LIST)}, chết={len(DEAD_PROXIES)}")
    return added

def reload_proxies():
    """Tải lại proxy từ file (merge không xóa)."""
    global last_proxy_reload
    added = merge_new_proxies()
    last_proxy_reload = time.time()
    return len(PROXY_LIST), added

def save_dead_proxy(proxy):
    """Lưu proxy chết vào file dead_proxy.txt."""
    DEAD_PROXIES.add(proxy)
    with open(DEAD_PROXY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{proxy}  # {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    # Xóa khỏi danh sách dùng
    with proxy_lock:
        if proxy in PROXY_LIST:
            PROXY_LIST.remove(proxy)

# ===== KIỂM TRA PROXY SỐNG =====
def check_proxy_alive(proxy: str, timeout: int = 10) -> bool:
    """Kiểm tra proxy có hoạt động không bằng cách gọi YouTube."""
    test_url = "https://www.youtube.com"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    proxies = {"http": proxy, "https": proxy}
    try:
        resp = requests.get(test_url, headers=headers, proxies=proxies, timeout=timeout)
        return resp.status_code == 200
    except:
        return False

def scan_dead_proxies():
    """Quét và loại bỏ proxy chết khỏi danh sách dùng."""
    global PROXY_LIST
    dead_found = []
    with proxy_lock:
        current_list = PROXY_LIST.copy()
    
    for proxy in current_list:
        if not check_proxy_alive(proxy):
            dead_found.append(proxy)
            save_dead_proxy(proxy)
            log_message(f"Proxy chết: {proxy}")
    
    if dead_found:
        log_message(f"Đã loại {len(dead_found)} proxy chết, còn {len(PROXY_LIST)} sống")
    return len(dead_found)

# ===== HÀM CÀY VIEW =====
def get_proxy():
    """Trả về proxy ngẫu nhiên từ danh sách sống."""
    with proxy_lock:
        if PROXY_LIST:
            return random.choice(PROXY_LIST)
    return None

def fetch_video_page(video_id: str, proxy: str = None, retry: int = VIEW_RETRY):
    """Tải trang video YouTube với retry, nếu proxy chết thì loại bỏ."""
    url = YOUTUBE_WATCH_URL.format(video_id=video_id)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
    }
    proxies = {"http": proxy, "https": proxy} if proxy else None
    
    for attempt in range(retry):
        try:
            resp = requests.get(url, headers=headers, proxies=proxies, timeout=15)
            if resp.status_code == 200:
                for _ in range(random.randint(2, 5)):
                    requests.get(url + "&t=" + str(random.randint(10, 600)),
                                 headers=headers, proxies=proxies, timeout=5)
                    time.sleep(random.uniform(0.5, 1.5))
                time.sleep(random.uniform(1.0, 3.0))
                return True
            else:
                time.sleep(random.uniform(1.0, 2.0) * (attempt + 1))
        except Exception:
            if attempt == retry - 1:
                # Proxy chết, loại bỏ
                if proxy:
                    save_dead_proxy(proxy)
                    log_message(f"Proxy chết khi cày view: {proxy}")
            else:
                time.sleep(random.uniform(1.0, 3.0) * (attempt + 1))
    return False

def run_view_task(video_id: str, count: int):
    """Chạy nhiều view với thread pool."""
    with proxy_lock:
        if not PROXY_LIST:
            return 0, "Không có proxy sống"
    
    success = 0
    failed = 0
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = []
        for i in range(count):
            proxy = get_proxy()
            futures.append(executor.submit(fetch_video_page, video_id, proxy))
            if i % 10 == 0:
                time.sleep(0.05)
        
        for f in futures:
            if f.result():
                success += 1
            else:
                failed += 1
            time.sleep(random.uniform(0.1, 0.5))
    
    global view_stats
    view_stats["total"] += count
    view_stats["success"] += success
    view_stats["failed"] += failed
    
    with proxy_lock:
        alive_count = len(PROXY_LIST)
    return success, f"Thành công: {success}/{count}, Proxy sống: {alive_count}"

# ===== WEB SERVER =====
async def handle_health(request):
    stats = {
        "status": "running",
        "pid": os.getpid(),
        "proxy_alive": len(PROXY_LIST),
        "proxy_master": len(PROXY_MASTER),
        "proxy_dead": len(DEAD_PROXIES),
        "uptime": int(time.time() - start_time),
        "view_stats": view_stats,
        "timestamp": datetime.now().isoformat()
    }
    return web.json_response(stats)

async def handle_index(request):
    html = f"""
    <html>
    <head><title>YouTube View Bot 24/7</title></head>
    <body>
    <h1>🤖 YouTube View Bot</h1>
    <p>PID: {os.getpid()}</p>
    <p>Proxy sống: {len(PROXY_LIST)}</p>
    <p>Proxy master: {len(PROXY_MASTER)}</p>
    <p>Proxy chết: {len(DEAD_PROXIES)}</p>
    <p>Total Views: {view_stats['total']}</p>
    <p>Success: {view_stats['success']}</p>
    <p>Failed: {view_stats['failed']}</p>
    <p>Uptime: {int(time.time() - start_time)}s</p>
    <p><a href="/health">Health Check</a></p>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_index)
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    log_message(f"Web server: http://{WEB_HOST}:{WEB_PORT}")

# ===== BOT TELEGRAM =====
app_bot = Client("view_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===== TASK NỀN =====
async def periodic_reload():
    global bot_running
    while bot_running:
        await asyncio.sleep(PROXY_RELOAD_INTERVAL)
        if bot_running:
            alive, added = await asyncio.to_thread(reload_proxies)
            log_message(f"Auto reload: {alive} alive, {added} added")

async def periodic_check_proxy():
    global bot_running
    while bot_running:
        await asyncio.sleep(PROXY_CHECK_INTERVAL)
        if bot_running:
            dead = await asyncio.to_thread(scan_dead_proxies)
            log_message(f"Proxy check: {dead} dead removed")

async def heartbeat():
    global bot_running
    while bot_running:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        if bot_running:
            with proxy_lock:
                alive = len(PROXY_LIST)
                master = len(PROXY_MASTER)
                dead = len(DEAD_PROXIES)
            log_message(f"Heartbeat: alive={alive}, master={master}, dead={dead}, views={view_stats['total']}")

# ===== LỆNH TELEGRAM =====
@app_bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    with proxy_lock:
        alive = len(PROXY_LIST)
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"🤖 Bot cày view YouTube 24/7\n"
        f"📌 Lệnh:\n"
        f"/view <video_id> <số_lượng> - Cày view (1-500)\n"
        f"/reload - Tải lại proxy từ file (merge)\n"
        f"/proxy - Xem proxy sống\n"
        f"/dead - Xem proxy chết\n"
        f"/addproxy <proxy> - Thêm proxy\n"
        f"/stats - Thống kê\n"
        f"/check - Kiểm tra proxy chết\n"
        f"📂 Proxy sống: {alive}\n"
        f"📂 Proxy master: {master}\n"
        f"💀 Proxy chết: {dead}\n"
        f"🌐 Web: http://{WEB_HOST}:{WEB_PORT}"
    )

@app_bot.on_message(filters.command("view"))
async def view_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("❌ Dùng: /view VIDEO_ID SỐ_LƯỢNG (1-500)")
        return
    video_id = parts[1].strip()
    try:
        count = int(parts[2])
        if count < 1 or count > 500:
            await message.reply_text("❌ Số lượng 1-500")
            return
    except ValueError:
        await message.reply_text("❌ Số lượng phải là số nguyên")
        return

    with proxy_lock:
        if not PROXY_LIST:
            await message.reply_text("❌ Không có proxy sống. Dùng /check để quét hoặc thêm proxy mới")
            return

    msg = await message.reply_text(f"⏳ Đang cày {count} view...")
    success, info = await asyncio.to_thread(run_view_task, video_id, count)
    await msg.edit_text(
        f"✅ {info}\n"
        f"🎯 https://youtu.be/{video_id}\n"
        f"📊 Tổng: {view_stats['total']} views"
    )

@app_bot.on_message(filters.command("reload"))
async def reload_cmd(client, message: Message):
    alive, added = await asyncio.to_thread(reload_proxies)
    with proxy_lock:
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"🔄 Đã merge proxy từ file\n"
        f"├ Thêm mới: {added}\n"
        f"├ Proxy sống: {alive}\n"
        f"├ Proxy master: {master}\n"
        f"└ Proxy chết: {dead}"
    )

@app_bot.on_message(filters.command("proxy"))
async def proxy_cmd(client, message: Message):
    with proxy_lock:
        if PROXY_LIST:
            sample = PROXY_LIST[:5]
            await message.reply_text(
                f"📋 Proxy SỐNG: {len(PROXY_LIST)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(PROXY_LIST)>5 else ''}\n"
                f"📄 File: {PROXY_FILE} (merge, không xóa)"
            )
        else:
            await message.reply_text(f"❌ Không có proxy sống. Dùng /check để quét")

@app_bot.on_message(filters.command("dead"))
async def dead_cmd(client, message: Message):
    with proxy_lock:
        dead_list = list(DEAD_PROXIES)
        if dead_list:
            sample = dead_list[:5]
            await message.reply_text(
                f"💀 Proxy CHẾT: {len(dead_list)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(dead_list)>5 else ''}\n"
                f"📄 File lưu: {DEAD_PROXY_FILE}"
            )
        else:
            await message.reply_text("✅ Chưa có proxy chết nào")

@app_bot.on_message(filters.command("addproxy"))
async def addproxy_cmd(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("❌ Dùng: /addproxy http://user:pass@ip:port")
        return
    new_proxy = parts[1].strip()
    if not (new_proxy.startswith("http://") or new_proxy.startswith("socks5://")):
        await message.reply_text("❌ Proxy phải bắt đầu http:// hoặc socks5://")
        return
    
    # Kiểm tra xem đã tồn tại chưa
    if new_proxy in PROXY_MASTER:
        await message.reply_text(f"⚠️ Proxy đã tồn tại trong master")
        return
    
    # Thêm vào file
    with open(PROXY_FILE, "a", encoding="utf-8") as f:
        f.write(new_proxy + "\n")
    
    # Merge vào master
    PROXY_MASTER.add(new_proxy)
    with proxy_lock:
        PROXY_LIST.append(new_proxy)
    
    await message.reply_text(
        f"✅ Đã thêm proxy: {new_proxy}\n"
        f"📊 Proxy sống: {len(PROXY_LIST)}\n"
        f"📊 Proxy master: {len(PROXY_MASTER)}"
    )

@app_bot.on_message(filters.command("check"))
async def check_cmd(client, message: Message):
    msg = await message.reply_text("⏳ Đang quét proxy chết...")
    dead = await asyncio.to_thread(scan_dead_proxies)
    with proxy_lock:
        alive = len(PROXY_LIST)
    await msg.edit_text(
        f"✅ Quét hoàn tất\n"
        f"├ Proxy chết đã loại: {dead}\n"
        f"├ Proxy sống còn: {alive}\n"
        f"└ Tổng proxy đã chết: {len(DEAD_PROXIES)}"
    )

@app_bot.on_message(filters.command("stats"))
async def stats_cmd(client, message: Message):
    uptime = int(time.time() - start_time)
    with proxy_lock:
        alive = len(PROXY_LIST)
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"📊 THỐNG KÊ\n"
        f"├ Tổng view: {view_stats['total']}\n"
        f"├ Thành công: {view_stats['success']}\n"
        f"├ Thất bại: {view_stats['failed']}\n"
        f"├ Proxy sống: {alive}\n"
        f"├ Proxy master: {master}\n"
        f"├ Proxy chết: {dead}\n"
        f"├ PID: {os.getpid()}\n"
        f"├ Uptime: {uptime}s\n"
        f"└ Web: http://{WEB_HOST}:{WEB_PORT}"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    await message.reply_text(f"🏓 Pong! PID: {os.getpid()}")

@app_bot.on_message(filters.command("stop"))
async def stop_cmd(client, message: Message):
    global bot_running
    await message.reply_text("🛑 Đang dừng bot...")
    bot_running = False
    asyncio.get_event_loop().call_later(1, lambda: asyncio.get_event_loop().stop())

# ===== XỬ LÝ TÍN HIỆU =====
def signal_handler(sig, frame):
    global bot_running
    log_message(f"Signal {sig}, shutting down...")
    bot_running = False
    remove_pid()
    sys.exit(0)

# ===== KHỞI ĐỘNG =====
async def main():
    global bot_running, start_time
    
    if check_already_running():
        log_message("Bot đã chạy, thoát.")
        sys.exit(1)
    
    write_pid()
    log_message(f"Khởi động bot, PID: {os.getpid()}")
    
    # Load proxy lần đầu
    merge_new_proxies()
    log_message(f"Loaded: alive={len(PROXY_LIST)}, master={len(PROXY_MASTER)}")
    
    # Khởi động web server
    await start_web_server()
    
    # Task nền
    asyncio.create_task(periodic_reload())
    asyncio.create_task(periodic_check_proxy())
    asyncio.create_task(heartbeat())
    
    # Chạy bot
    try:
        await app_bot.start()
        log_message("Bot Telegram đã kết nối")
        await app_bot.idle()
    except Exception as e:
        log_message(f"Lỗi bot: {e}")
    finally:
        await app_bot.stop()
        remove_pid()
        log_message("Bot đã dừng")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log_message("Keyboard interrupt")
        remove_pid()
    except Exception as e:
        log_message(f"Lỗi fatal: {e}")
        remove_pid()
