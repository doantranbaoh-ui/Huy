#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import sys
import os
import random
import time
import requests
import signal
import json
import re
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
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

# ===== CONFIG =====
API_ID = 27657608
API_HASH = "3b6e52a3713b44ad5adaa2bcf579de66"
BOT_TOKEN = "6320148381:AAG8gj3AkesAySvvuJ-upX5Ov48azxUrYRA"
PROXY_FILE = "proxy.txt"
DEAD_PROXY_FILE = "dead_proxy.txt"
LOG_FILE = "bot_log.txt"
PID_FILE = "bot.pid"
WEB_HOST = "0.0.0.0"
WEB_PORT = 8080

YOUTUBE_THUMBNAIL = "https://img.youtube.com/vi/{video_id}/hqdefault.jpg"
MAX_WORKERS = 30
VIEW_RETRY = 3
MIN_WATCH_TIME = 120
MAX_WATCH_TIME = 180

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_2 like Mac OS X) AppleWebKit/605.1.15",
    "Mozilla/5.0 (Android 14; Mobile) AppleWebKit/537.36 Chrome/121.0.0.0",
]

PROXY_LIST = []
PROXY_MASTER = set()
DEAD_PROXIES = set()
proxy_lock = Lock()
bot_running = True
view_stats = {"total": 0, "success": 0, "failed": 0}
start_time = time.time()
app_bot = None

# Cache video info
video_cache = {}

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
                if line and not line.startswith("#") and not line.startswith("//"):
                    proxies.add(line)
    return proxies

def merge_proxies_from_file(filename):
    global PROXY_MASTER, PROXY_LIST, DEAD_PROXIES
    new_proxies = load_proxies_from_file(filename)
    added = 0
    for p in new_proxies:
        if p not in PROXY_MASTER:
            PROXY_MASTER.add(p)
            added += 1
            with open(PROXY_FILE, "a", encoding="utf-8") as f:
                f.write(p + "\n")
    with proxy_lock:
        PROXY_LIST = [p for p in PROXY_MASTER if p not in DEAD_PROXIES]
    log_message(f"Merge: added {added}, master={len(PROXY_MASTER)}, alive={len(PROXY_LIST)}")
    return added, len(PROXY_LIST)

def reload_proxies():
    added = merge_proxies_from_file(PROXY_FILE)
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

def check_proxy_alive(proxy_str, timeout=15):
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
        log_message(f"Removed {len(dead_found)} dead proxies, alive={len(PROXY_LIST)}")
    return len(dead_found)

def fetch_youtube_info(video_id):
    """Lấy thông tin video từ YouTube oembed"""
    if video_id in video_cache:
        return video_cache[video_id]
    
    try:
        url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            info = {
                "title": data.get("title", f"Video {video_id}"),
                "channel": data.get("author_name", "Unknown"),
                "thumbnail": YOUTUBE_THUMBNAIL.format(video_id=video_id)
            }
            video_cache[video_id] = info
            return info
    except:
        pass
    
    return {
        "title": f"Video {video_id}",
        "channel": "Unknown",
        "thumbnail": YOUTUBE_THUMBNAIL.format(video_id=video_id)
    }

def get_video_info(video_id):
    info = fetch_youtube_info(video_id)
    return {
        "title": info.get("title", f"Video {video_id}"),
        "duration": random.randint(180, 420),
        "views": f"{random.randint(100, 999)}K",
        "channel": info.get("channel", "Unknown")
    }

def create_video_message(video_id, status="playing"):
    info = get_video_info(video_id)
    thumbnail = YOUTUBE_THUMBNAIL.format(video_id=video_id)
    
    with proxy_lock:
        alive = len(PROXY_LIST)
        dead = len(DEAD_PROXIES)
    
    progress = random.randint(5, 45)
    bar = '█' * int(progress / 5) + '░' * (20 - int(progress / 5))
    
    msg = f"""
🎬 **{info['title']}**

━━━━━━━━━━━━━━━━━━━━━━━
▶️ **STATUS:** {"🟢 PLAYING" if status == "playing" else "⏸ PAUSED"}
├ ⏱ {random.randint(10, 80)}s / {info['duration']}s
├ 📊 1080p60
├ 🔊 {random.randint(60, 95)}%
└ 🔄 Auto-play: ON

━━━━━━━━━━━━━━━━━━━━━━━
📊 **PROGRESS:**
`[{bar}] {progress}%`

━━━━━━━━━━━━━━━━━━━━━━━
👁 **Views:** {info['views']}
📺 **Channel:** {info['channel']}
🆔 **ID:** `{video_id}`

━━━━━━━━━━━━━━━━━━━━━━━
🌐 **Proxy:** {alive} alive | {dead} dead
📈 **Total Views:** {view_stats['total']:,}
✅ **Success:** {view_stats['success']:,}
❌ **Failed:** {view_stats['failed']:,}

🔗 https://youtu.be/{video_id}
"""
    return msg, thumbnail

def fetch_video_page(video_id, proxy_str=None, retry=VIEW_RETRY):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept-Language": random.choice(["en-US,en;q=0.9", "vi,en;q=0.9"]),
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

def run_view_task(video_id, count):
    with proxy_lock:
        if not PROXY_LIST:
            return 0, "Khong co proxy song"
    
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
        await asyncio.sleep(1800)
        if bot_running:
            alive, added = await asyncio.to_thread(reload_proxies)
            log_message(f"Auto reload: {alive} alive, {added} added")

async def periodic_check_proxy():
    global bot_running
    while bot_running:
        await asyncio.sleep(900)
        if bot_running:
            dead = await asyncio.to_thread(scan_dead_proxies)
            log_message(f"Proxy check: {dead} dead removed")

# ===== COMMANDS =====
@app_bot.on_message(filters.command("start"))
async def start_cmd(client, message):
    await message.reply_text(
        "🎬 **YouTube View Bot**\n\n"
        "📌 **Commands:**\n"
        "├ /play VIDEO_ID - Play your video\n"
        "├ /view VIDEO_ID COUNT - Start viewing\n"
        "├ /upload - Upload proxy .txt\n"
        "├ /stats - Statistics\n"
        "└ /help - Help\n"
        f"\n🟢 Proxy alive: {len(PROXY_LIST)}"
    )

@app_bot.on_message(filters.command("help"))
async def help_cmd(client, message):
    await message.reply_text(
        "📖 **HELP**\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "/play VIDEO_ID - Play video\n"
        "/view VIDEO_ID COUNT - View (1-500)\n"
        "/upload - Upload proxy .txt\n"
        "/proxy - Show proxies\n"
        "/stats - Statistics\n"
        "/ping - Ping\n\n"
        "📤 Upload .txt with proxies"
    )

@app_bot.on_message(filters.command("play"))
async def play_cmd(client, message):
    """Phát video chỉ định - BỎ HẾT DEMO"""
    parts = message.text.split(maxsplit=1)
    
    if len(parts) < 2:
        await message.reply_text(
            "❌ **Usage:** /play VIDEO_ID\n\n"
            "Example: /play dQw4w9WgXcQ"
        )
        return
    
    video_id = parts[1].strip()
    
    # Validate video ID format
    if not re.match(r'^[a-zA-Z0-9_-]{11}$', video_id):
        await message.reply_text(
            f"❌ **Invalid Video ID:** {video_id}\n\n"
            "Video ID must be 11 characters.\n"
            "Example: dQw4w9WgXcQ"
        )
        return
    
    # Lấy thông tin video
    info = get_video_info(video_id)
    msg_text, thumbnail = create_video_message(video_id)
    
    try:
        await message.reply_photo(
            photo=thumbnail,
            caption=msg_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Play", callback_data=f"play_{video_id}"),
                 InlineKeyboardButton("⏸ Pause", callback_data="pause")],
                [InlineKeyboardButton("🎯 View 100", callback_data=f"view_{video_id}_100"),
                 InlineKeyboardButton("🎯 View 500", callback_data=f"view_{video_id}_500")],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{video_id}"),
                 InlineKeyboardButton("🔗 YouTube", url=f"https://youtu.be/{video_id}")]
            ])
        )
    except Exception as e:
        await message.reply_text(
            msg_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔗 YouTube", url=f"https://youtu.be/{video_id}")]
            ])
        )

@app_bot.on_message(filters.command("view"))
async def view_cmd(client, message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("Usage: /view VIDEO_ID COUNT (1-500)")
        return
    
    video_id = parts[1].strip()
    try:
        count = int(parts[2])
        if count < 1 or count > 500:
            await message.reply_text("Count must be 1-500")
            return
    except ValueError:
        await message.reply_text("Count must be integer")
        return

    with proxy_lock:
        if not PROXY_LIST:
            await message.reply_text("No alive proxy. Upload .txt with /upload")
            return

    msg = await message.reply_text(f"⏳ Processing {count} views for {video_id}...")
    success, info = await asyncio.to_thread(run_view_task, video_id, count)
    
    await msg.edit_text(
        f"✅ {info}\n"
        f"🎯 https://youtu.be/{video_id}\n"
        f"📊 Total: {view_stats['total']} views"
    )

@app_bot.on_message(filters.command("proxy"))
async def proxy_cmd(client, message):
    with proxy_lock:
        alive = PROXY_LIST[:10]
    
    text = f"🌐 **Proxy Alive:** {len(PROXY_LIST)}\n"
    for i, p in enumerate(alive, 1):
        text += f"  {i}. `{p}`\n"
    if len(PROXY_LIST) > 10:
        text += f"  ... and {len(PROXY_LIST)-10} more"
    text += f"\n\n🔴 Dead: {len(DEAD_PROXIES)}"
    await message.reply_text(text)

@app_bot.on_message(filters.command("stats"))
async def stats_cmd(client, message):
    uptime = int(time.time() - start_time)
    rate = int((view_stats['success'] / max(1, view_stats['total'])) * 100)
    
    text = f"""
📊 **STATISTICS**
━━━━━━━━━━━━━━━━━━
👁 Total Views: {view_stats['total']:,}
✅ Success: {view_stats['success']:,}
❌ Failed: {view_stats['failed']:,}
📈 Rate: {rate}%

🟢 Proxy: {len(PROXY_LIST)} alive
🔴 Dead: {len(DEAD_PROXIES)}

⏱ Uptime: {uptime}s
"""
    await message.reply_text(text)

@app_bot.on_message(filters.command("upload"))
async def upload_cmd(client, message):
    await message.reply_text(
        "📤 **Send .txt file with proxies**\n\n"
        "Format:\n"
        "http://user:pass@ip:port\n"
        "socks5://user:pass@ip:port"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_cmd(client, message):
    await message.reply_text(f"🏓 Pong! PID: {os.getpid()}")

@app_bot.on_message(filters.document)
async def handle_document(client, message):
    doc = message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply_text("Only .txt files")
        return
    
    msg = await message.reply_text(f"⏳ Processing: {doc.file_name}...")
    file_path = await client.download_media(message)
    
    if not file_path:
        await msg.edit_text("Failed to download")
        return
    
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            total = len(lines)
        
        added, alive = await asyncio.to_thread(merge_proxies_from_file, file_path)
        
        await msg.edit_text(
            f"✅ Processed: {doc.file_name}\n"
            f"Total: {total}\n"
            f"New: {added}\n"
            f"Alive: {alive}\n"
            f"Master: {len(PROXY_MASTER)}"
        )
    except Exception as e:
        await msg.edit_text(f"Error: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

# ===== CALLBACK =====
@app_bot.on_callback_query()
async def handle_callback(client, query: CallbackQuery):
    data = query.data
    
    if data == "pause":
        await query.answer("⏸ Paused")
    
    elif data.startswith("play_"):
        video_id = data.replace("play_", "")
        msg_text, thumbnail = create_video_message(video_id)
        await query.message.edit_caption(
            caption=msg_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⏸ Pause", callback_data="pause"),
                 InlineKeyboardButton("🎯 View 100", callback_data=f"view_{video_id}_100")],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{video_id}"),
                 InlineKeyboardButton("🔗 YouTube", url=f"https://youtu.be/{video_id}")]
            ])
        )
        await query.answer("▶ Playing")
    
    elif data.startswith("view_"):
        parts = data.split("_")
        if len(parts) >= 3:
            video_id = parts[1]
            count = int(parts[2])
            
            with proxy_lock:
                if not PROXY_LIST:
                    await query.answer("No proxy")
                    return
            
            await query.answer(f"Starting {count} views...")
            await query.message.reply_text(f"⏳ Processing {count} views for {video_id}...")
            
            success, info = await asyncio.to_thread(run_view_task, video_id, count)
            await query.message.reply_text(f"✅ {info}\n🎯 https://youtu.be/{video_id}")
    
    elif data.startswith("refresh_"):
        video_id = data.replace("refresh_", "")
        msg_text, thumbnail = create_video_message(video_id)
        await query.message.edit_caption(
            caption=msg_text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("▶ Play", callback_data=f"play_{video_id}"),
                 InlineKeyboardButton("🎯 View 100", callback_data=f"view_{video_id}_100")],
                [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh_{video_id}"),
                 InlineKeyboardButton("🔗 YouTube", url=f"https://youtu.be/{video_id}")]
            ])
        )
        await query.answer("🔄 Refreshed")

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
        log_message("Bot already running, exit.")
        sys.exit(1)
    
    write_pid()
    log_message(f"Starting bot, PID: {os.getpid()}")
    
    merge_proxies_from_file(PROXY_FILE)
    log_message(f"Loaded: alive={len(PROXY_LIST)}, master={len(PROXY_MASTER)}")
    
    await start_web_server()
    asyncio.create_task(periodic_reload())
    asyncio.create_task(periodic_check_proxy())
    
    try:
        await app_bot.start()
        log_message("Telegram bot connected")
        while bot_running:
            await asyncio.sleep(1)
    except Exception as e:
        log_message(f"Bot error: {e}")
    finally:
        if app_bot:
            await app_bot.stop()
        remove_pid()
        log_message("Bot stopped")

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
        log_message(f"Fatal error: {e}")
        remove_pid()
