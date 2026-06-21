#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TELEGRAM BOT CÀY VIEW YOUTUBE - NHẬN MỌI FILE .TXT
- Tự động nhận bất kỳ file .txt nào, đọc proxy từ đó
- Merge proxy không xóa, lưu vào proxy.txt
- Hỗ trợ HTTP/SOCKS4/SOCKS5
"""

import asyncio
import sys
import os
import random
import time
import requests
import signal
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from aiohttp import web

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
else:
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    except Exception:
        pass

from pyrogram import Client, filters
from pyrogram.types import Message, Document, InlineKeyboardMarkup, InlineKeyboardButton

# ===== CẤU HÌNH =====
API_ID = 27657608
API_HASH = "3b6e52a3713b44ad5adaa2bcf579de66"
BOT_TOKEN = "6320148381:AAG8gj3AkesAySvvuJ-upX5Ov48azxUrYRA"
MAIN_PROXY_FILE = "proxy.txt"
DEAD_PROXY_FILE = "dead_proxy.txt"
LOG_FILE = "bot_log.txt"
PID_FILE = "bot.pid"
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

# ===== CẤU HÌNH VIEW =====
YOUTUBE_WATCH_URL = "https://www.youtube.com/watch?v={video_id}"
MAX_WORKERS = 30
VIEW_RETRY = 3
PROXY_CHECK_INTERVAL = 1800
PROXY_RELOAD_INTERVAL = 3600
MIN_WATCH_TIME = 120
MAX_WATCH_TIME = 180

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
]

PROXY_LIST = []
PROXY_MASTER = set()
DEAD_PROXIES = set()
proxy_lock = Lock()
bot_running = True
view_stats = {"total": 0, "success": 0, "failed": 0}
start_time = time.time()
app_bot = None

DEMO_VIDEOS = {
    "dQw4w9WgXcQ": "Rick Astley - Never Gonna Give You Up",
    "9bZkp7q19f0": "PSY - GANGNAM STYLE",
    "kJQP7kiw5Fk": "Luis Fonsi - Despacito",
}

def log_message(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {msg}"
    print(log_line)
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(log_line + "\n")
    except:
        pass

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

def parse_proxy(proxy_str):
    if proxy_str.startswith("http://"):
        return {"http": proxy_str, "https": proxy_str}
    elif proxy_str.startswith("socks5://"):
        return {"http": proxy_str, "https": proxy_str}
    elif proxy_str.startswith("socks4://"):
        return {"http": proxy_str, "https": proxy_str}
    else:
        return {"http": "http://" + proxy_str, "https": "http://" + proxy_str}

def load_proxies_from_file(filename):
    proxies = set()
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    proxies.add(line)
    return proxies

def merge_proxies_from_file(filename):
    """Merge proxy từ bất kỳ file .txt nào vào master"""
    global PROXY_MASTER, PROXY_LIST, DEAD_PROXIES
    new_proxies = load_proxies_from_file(filename)
    added = 0
    
    for p in new_proxies:
        if p not in PROXY_MASTER:
            PROXY_MASTER.add(p)
            added += 1
            # Lưu vào file chính
            with open(MAIN_PROXY_FILE, "a", encoding="utf-8") as f:
                f.write(p + "\n")
    
    with proxy_lock:
        PROXY_LIST = [p for p in PROXY_MASTER if p not in DEAD_PROXIES]
    
    log_message(f"Merge từ {filename}: thêm {added}, master={len(PROXY_MASTER)}, sống={len(PROXY_LIST)}")
    return added, len(PROXY_LIST)

def reload_proxies():
    added = merge_proxies_from_file(MAIN_PROXY_FILE)
    return len(PROXY_LIST), added

def save_dead_proxy(proxy):
    DEAD_PROXIES.add(proxy)
    with open(DEAD_PROXY_FILE, "a", encoding="utf-8") as f:
        f.write(f"{proxy}  # {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    with proxy_lock:
        if proxy in PROXY_LIST:
            PROXY_LIST.remove(proxy)

def get_proxy():
    with proxy_lock:
        if PROXY_LIST:
            return random.choice(PROXY_LIST)
    return None

def check_proxy_alive(proxy_str: str, timeout: int = 15) -> bool:
    test_url = "https://www.youtube.com"
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        proxies = parse_proxy(proxy_str)
        resp = requests.get(test_url, headers=headers, proxies=proxies, timeout=timeout)
        return resp.status_code == 200
    except:
        return False

def scan_dead_proxies():
    dead_found = []
    with proxy_lock:
        current_list = PROXY_LIST.copy()
    for proxy in current_list:
        if not check_proxy_alive(proxy):
            dead_found.append(proxy)
            save_dead_proxy(proxy)
    if dead_found:
        log_message(f"Đã loại {len(dead_found)} proxy chết, còn {len(PROXY_LIST)} sống")
    return len(dead_found)

def fetch_video_page(video_id: str, proxy_str: str = None, retry: int = VIEW_RETRY):
    url = YOUTUBE_WATCH_URL.format(video_id=video_id)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": "en-US,en;q=0.9",
        "Cache-Control": "no-cache",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    proxies = parse_proxy(proxy_str) if proxy_str else None
    
    for attempt in range(retry):
        try:
            session = requests.Session()
            resp = session.get(url, headers=headers, proxies=proxies, timeout=20)
            if resp.status_code != 200:
                session.close()
                time.sleep(random.uniform(1.0, 3.0) * (attempt + 1))
                continue
            
            watch_time = random.randint(MIN_WATCH_TIME, MAX_WATCH_TIME)
            segments = random.randint(4, 8)
            segment_time = watch_time // segments
            
            for seg in range(segments):
                time.sleep(segment_time + random.uniform(0.5, 2.0))
                if seg < segments - 1:
                    try:
                        session.get(
                            url + "&t=" + str(int(segment_time * seg)),
                            headers=headers,
                            proxies=proxies,
                            timeout=5
                        )
                    except:
                        pass
            
            session.get(
                url + "&t=" + str(random.randint(watch_time - 10, watch_time + 10)),
                headers=headers,
                proxies=proxies,
                timeout=5
            )
            
            time.sleep(random.uniform(1.0, 3.0))
            session.get(
                f"https://www.youtube.com/embed/{video_id}?autoplay=1",
                headers=headers,
                proxies=proxies,
                timeout=5
            )
            
            session.close()
            return True
            
        except Exception:
            if attempt == retry - 1:
                if proxy_str:
                    save_dead_proxy(proxy_str)
            else:
                time.sleep(random.uniform(1.0, 3.0) * (attempt + 1))
    
    return False

def run_view_task(video_id: str, count: int):
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
            if i % 5 == 0:
                time.sleep(0.1)
        
        for f in futures:
            if f.result():
                success += 1
            else:
                failed += 1
            time.sleep(random.uniform(0.05, 0.2))
    
    global view_stats
    view_stats["total"] += count
    view_stats["success"] += success
    view_stats["failed"] += failed
    
    with proxy_lock:
        alive_count = len(PROXY_LIST)
    
    return success, f"Success: {success}/{count} | Proxy alive: {alive_count}"

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

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text=f"YouTube View Bot - PID: {os.getpid()}"))
    app.router.add_get("/health", handle_health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, WEB_HOST, WEB_PORT)
    await site.start()
    log_message(f"Web server: http://{WEB_HOST}:{WEB_PORT}")

# ===== TELEGRAM BOT =====
app_bot = Client("view_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

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

# ===== COMMANDS =====
@app_bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    with proxy_lock:
        alive = len(PROXY_LIST)
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"🎬 **YouTube View Bot**\n\n"
        f"📌 **LỆNH:**\n"
        f"├ `/view VIDEO_ID SỐ_LƯỢNG` - Cày view\n"
        f"├ `/upload` - Upload file .txt (proxy)\n"
        f"├ `/proxy` - Xem proxy sống\n"
        f"├ `/dead` - Xem proxy chết\n"
        f"├ `/check` - Quét proxy chết\n"
        f"├ `/stats` - Thống kê\n"
        f"└ `/ping` - Kiểm tra bot\n\n"
        f"📂 **Proxy sống:** {alive}\n"
        f"📂 **Proxy master:** {master}\n"
        f"💀 **Proxy chết:** {dead}"
    )

@app_bot.on_message(filters.command("view"))
async def view_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("❌ **Cách dùng:** `/view VIDEO_ID SỐ_LƯỢNG` (1-500)")
        return
    video_id = parts[1].strip()
    try:
        count = int(parts[2])
        if count < 1 or count > 500:
            await message.reply_text("❌ Số lượng phải từ 1-500")
            return
    except ValueError:
        await message.reply_text("❌ Số lượng phải là số nguyên")
        return

    with proxy_lock:
        if not PROXY_LIST:
            await message.reply_text("❌ Không có proxy sống. Upload file .txt")
            return

    msg = await message.reply_text(f"⏳ Đang cày {count} view...")
    success, info = await asyncio.to_thread(run_view_task, video_id, count)
    await msg.edit_text(
        f"✅ **{info}**\n"
        f"🎯 https://youtu.be/{video_id}\n"
        f"📊 Tổng: {view_stats['total']} views"
    )

@app_bot.on_message(filters.command("upload"))
async def upload_cmd(client, message: Message):
    await message.reply_text(
        "📤 **Gửi file .txt** bất kỳ (đính kèm)\n"
        "Bot sẽ đọc proxy từ file và merge vào danh sách"
    )

@app_bot.on_message(filters.document)
async def handle_document(client, message: Message):
    doc = message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply_text("⚠️ Chỉ chấp nhận file .txt")
        return
    
    msg = await message.reply_text(f"⏳ Đang xử lý: {doc.file_name}...")
    file_path = await client.download_media(message)
    
    if not file_path:
        await msg.edit_text("❌ Không thể tải file")
        return
    
    try:
        # Đếm số proxy trước khi merge
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            total_in_file = len(lines)
        
        # Merge proxy vào master
        added, alive = await asyncio.to_thread(merge_proxies_from_file, file_path)
        
        await msg.edit_text(
            f"✅ **Đã xử lý: {doc.file_name}**\n"
            f"├ Tổng proxy trong file: {total_in_file}\n"
            f"├ Đã thêm mới: {added}\n"
            f"├ Proxy sống hiện tại: {alive}\n"
            f"├ Proxy master: {len(PROXY_MASTER)}\n"
            f"└ Proxy chết: {len(DEAD_PROXIES)}"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app_bot.on_message(filters.command("proxy"))
async def proxy_cmd(client, message: Message):
    with proxy_lock:
        if PROXY_LIST:
            sample = PROXY_LIST[:5]
            await message.reply_text(
                f"📋 **Proxy SỐNG:** {len(PROXY_LIST)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(PROXY_LIST)>5 else ''}"
            )
        else:
            await message.reply_text("❌ Không có proxy sống. Upload file .txt")

@app_bot.on_message(filters.command("dead"))
async def dead_cmd(client, message: Message):
    with proxy_lock:
        dead_list = list(DEAD_PROXIES)
        if dead_list:
            sample = dead_list[:5]
            await message.reply_text(
                f"💀 **Proxy CHẾT:** {len(dead_list)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(dead_list)>5 else ''}"
            )
        else:
            await message.reply_text("✅ Chưa có proxy chết nào")

@app_bot.on_message(filters.command("check"))
async def check_cmd(client, message: Message):
    msg = await message.reply_text("⏳ Đang quét proxy chết...")
    dead = await asyncio.to_thread(scan_dead_proxies)
    with proxy_lock:
        alive = len(PROXY_LIST)
    await msg.edit_text(
        f"✅ **Quét hoàn tất**\n"
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
        f"📊 **THỐNG KÊ**\n"
        f"├ Tổng view: {view_stats['total']}\n"
        f"├ Thành công: {view_stats['success']}\n"
        f"├ Thất bại: {view_stats['failed']}\n"
        f"├ Proxy sống: {alive}\n"
        f"├ Proxy master: {master}\n"
        f"├ Proxy chết: {dead}\n"
        f"├ PID: {os.getpid()}\n"
        f"└ Uptime: {uptime}s"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    await message.reply_text(f"🏓 **Pong!** PID: {os.getpid()}")

# ===== SIGNAL =====
def signal_handler(sig, frame):
    global bot_running
    log_message(f"Signal {sig}, shutting down...")
    bot_running = False
    remove_pid()
    sys.exit(0)

# ===== MAIN =====
async def main():
    global bot_running, start_time, app_bot
    
    if check_already_running():
        log_message("Bot đã chạy, thoát.")
        sys.exit(1)
    
    write_pid()
    log_message(f"Khởi động bot, PID: {os.getpid()}")
    
    # Load proxy từ file chính nếu có
    merge_proxies_from_file(MAIN_PROXY_FILE)
    log_message(f"Loaded: alive={len(PROXY_LIST)}, master={len(PROXY_MASTER)}")
    
    await start_web_server()
    asyncio.create_task(periodic_reload())
    asyncio.create_task(periodic_check_proxy())
    
    try:
        await app_bot.start()
        log_message("Bot Telegram đã kết nối")
        while bot_running:
            await asyncio.sleep(1)
    except Exception as e:
        log_message(f"Lỗi bot: {e}")
    finally:
        if app_bot:
            await app_bot.stop()
        remove_pid()
        log_message("Bot đã dừng")

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        loop = asyncio.get_event_loop()
        if loop.is_closed():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        log_message("Keyboard interrupt")
        remove_pid()
    except Exception as e:
        log_message(f"Lỗi fatal: {e}")
        remove_pid()
