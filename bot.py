⏱ Đã xem: {random.randint(30, 90)}/{random.randint(180, 420)}s

━━━━━━━━━━━━━━━━━━━━━
🌐 **PROXY STATUS:**
├ 📡 Đang kết nối: {proxy_count} proxy
├ 🔄 Proxy hiện tại: {random.choice(PROXY_LIST) if PROXY_LIST else 'Không có'}
├ ✅ Thành công: {view_stats['success']}
└ ❌ Thất bại: {view_stats['failed']}

━━━━━━━━━━━━━━━━━━━━━
📈 **THỐNG KÊ:**
├ 👁 Tổng view: {view_stats['total']}
├ 🎯 View đang chạy: {count}
├ ⏳ Ước tính: ~{count * 120} giây
└ 🕒 Uptime: {int(time.time() - start_time)}s

━━━━━━━━━━━━━━━━━━━━━
🔘 **ĐIỀU KHIỂN:**
⏸ Tạm dừng  |  ⏭ Tiếp theo  |  🔄 Làm mới
"""
    return gui

def create_progress_bar(percent, length=20):
    filled = int(length * percent / 100)
    bar = '█' * filled + '░' * (length - filled)
    return f"[{bar}] {percent}%"

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
    <!DOCTYPE html>
    <html>
    <head><title>YouTube View Bot</title>
    <style>
        body {{ font-family: Arial; background: #0f0f0f; color: #fff; padding: 20px; }}
        .status {{ background: #1a1a1a; padding: 20px; border-radius: 10px; }}
        .green {{ color: #0f0; }}
        .red {{ color: #f00; }}
    </style>
    </head>
    <body>
    <div class="status">
        <h1>🎬 YouTube View Bot</h1>
        <p>🟢 Status: <span class="green">Running</span></p>
        <p>📊 PID: {os.getpid()}</p>
        <p>🌐 Proxy sống: {len(PROXY_LIST)}</p>
        <p>💀 Proxy chết: {len(DEAD_PROXIES)}</p>
        <p>👁 Total Views: {view_stats['total']}</p>
        <p>✅ Success: {view_stats['success']}</p>
        <p>❌ Failed: {view_stats['failed']}</p>
        <p>⏱ Uptime: {int(time.time() - start_time)}s</p>
        <p><a href="/health" style="color: #0f0;">Health Check</a></p>
    </div>
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

# ===== TELEGRAM BOT =====
app_bot = Client("view_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# ===== BACKGROUND TASKS =====
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

# ===== TELEGRAM COMMANDS =====
@app_bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    with proxy_lock:
        alive = len(PROXY_LIST)
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"🎬 **YouTube View Bot 24/7**\n\n"
        f"📌 **LỆNH:**\n"
        f"├ `/view VIDEO_ID SỐ_LƯỢNG` - Cày view\n"
        f"├ `/view_gui VIDEO_ID SỐ_LƯỢNG` - Cày view với GUI\n"
        f"├ `/player VIDEO_ID` - Trình phát mô phỏng\n"
        f"├ `/gui` - Menu GUI chính\n"
        f"├ `/reload` - Tải lại proxy (merge)\n"
        f"├ `/proxy` - Xem proxy sống\n"
        f"├ `/dead` - Xem proxy chết\n"
        f"├ `/addproxy PROXY` - Thêm proxy\n"
        f"├ `/upload` - Upload file proxy.txt\n"
        f"├ `/check` - Quét proxy chết\n"
        f"├ `/stats` - Thống kê\n"
        f"├ `/ping` - Kiểm tra bot\n"
        f"└ `/settings` - Cài đặt\n\n"
        f"📂 **Proxy sống:** {alive}\n"
        f"📂 **Proxy master:** {master}\n"
        f"💀 **Proxy chết:** {dead}\n"
        f"👁 **Tổng view:** {view_stats['total']}"
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
            await message.reply_text("❌ Không có proxy sống. Upload file proxy.txt")
            return

    msg = await message.reply_text(f"⏳ Đang cày {count} view...")
    success, info = await asyncio.to_thread(run_view_task, video_id, count)
    await msg.edit_text(
        f"✅ **{info}**\n"
        f"🎯 https://youtu.be/{video_id}\n"
        f"📊 Tổng: {view_stats['total']} views"
    )

@app_bot.on_message(filters.command("view_gui"))
async def view_gui_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("❌ **Cách dùng:** `/view_gui VIDEO_ID SỐ_LƯỢNG`")
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
            await message.reply_text("❌ Không có proxy sống")
            return
        proxy_count = len(PROXY_LIST)

    gui_text = create_video_gui(video_id, count, proxy_count)
    await message.reply_text(
        gui_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("⏸ Tạm dừng", callback_data="pause"),
             InlineKeyboardButton("⏭ Tiếp theo", callback_data="next")],
            [InlineKeyboardButton("🔄 Làm mới", callback_data="refresh"),
             InlineKeyboardButton("📊 Stats", callback_data="show_stats")]
        ])
    )

    await message.reply_text(f"⏳ Đang cày {count} view...")
    success, info = await asyncio.to_thread(run_view_task, video_id, count)
    await message.reply_text(
        f"✅ **{info}**\n"
        f"🎯 https://youtu.be/{video_id}"
    )

@app_bot.on_message(filters.command("player"))
async def player_cmd(client, message: Message):
    parts = message.text.split()
    video_id = parts[1] if len(parts) > 1 else "dQw4w9WgXcQ"
    
    player_text = f"""
🎬 **YOUTUBE PLAYER PRO**
━━━━━━━━━━━━━━━━━━━━━

📹 **Đang phát:**
└ {DEMO_VIDEOS.get(video_id, f"Video {video_id}")}

🖼 **Thumbnail:** https://img.youtube.com/vi/{video_id}/hqdefault.jpg

━━━━━━━━━━━━━━━━━━━━━
▶️ **TRẠNG THÁI:**
├ 🟢 Đang phát
├ ⏱ 00:42 / 03:15
├ 📹 1080p60
└ 🔊 80%

━━━━━━━━━━━━━━━━━━━━━
⚡ **THÔNG TIN:**
├ 👁 {random.randint(100000, 9999999)} lượt xem
├ 👍 {random.randint(1000, 99999)} lượt thích
├ 💬 {random.randint(100, 9999)} bình luận
└ 📅 Đăng tải: {datetime.now().strftime('%d/%m/%Y')}

━━━━━━━━━━━━━━━━━━━━━
🎯 **HÀNH ĐỘNG:**
├ 🔄 Chia sẻ
├ 💾 Lưu vào danh sách phát
└ 📌 Báo cáo
"""
    await message.reply_text(
        player_text,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("▶ Phát", callback_data="play"),
             InlineKeyboardButton("⏸ Tạm dừng", callback_data="pause")],
            [InlineKeyboardButton("🔊 Tăng âm", callback_data="vol_up"),
             InlineKeyboardButton("🔉 Giảm âm", callback_data="vol_down")],
            [InlineKeyboardButton("📥 Tải video", callback_data="download")]
        ])
    )

@app_bot.on_message(filters.command("gui"))
async def gui_cmd(client, message: Message):
    gui_menu = f"""
🎮 **BOT GUI CONTROLLER**
━━━━━━━━━━━━━━━━━━━━━

📌 **MENU CHÍNH:**

1️⃣ **📹 Xem video**
   └ `/view_gui VIDEO_ID SỐ_LƯỢNG`

2️⃣ **🎬 Trình phát**
   └ `/player VIDEO_ID`

3️⃣ **📊 Thống kê**
   └ `/stats`

4️⃣ **🌐 Proxy Manager**
   └ `/proxy` - Xem proxy sống
   └ `/dead` - Xem proxy chết
   └ `/check` - Quét proxy chết
   └ `/upload` - Upload file proxy.txt

5️⃣ **⚙️ Cài đặt**
   └ `/settings`

━━━━━━━━━━━━━━━━━━━━━
🟢 **Trạng thái:** Đang chạy
🔄 **Proxy sống:** {len(PROXY_LIST)}
💀 **Proxy chết:** {len(DEAD_PROXIES)}
👁 **Tổng view:** {view_stats['total']}
"""
    await message.reply_text(
        gui_menu,
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📹 Xem video", callback_data="view_video"),
             InlineKeyboardButton("🎬 Player", callback_data="player")],
            [InlineKeyboardButton("📊 Stats", callback_data="show_stats"),
             InlineKeyboardButton("🌐 Proxy", callback_data="show_proxy")],
            [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_gui")]
        ])
    )

@app_bot.on_message(filters.command("reload"))
async def reload_cmd(client, message: Message):
    alive, added = await asyncio.to_thread(reload_proxies)
    with proxy_lock:
        master = len(PROXY_MASTER)
        dead = len(DEAD_PROXIES)
    await message.reply_text(
        f"🔄 **Đã merge proxy từ file**\n"
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
                f"📋 **Proxy SỐNG:** {len(PROXY_LIST)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(PROXY_LIST)>5 else ''}\n"
                f"📄 File: {PROXY_FILE}"
            )
        else:
            await message.reply_text("❌ Không có proxy sống")

@app_bot.on_message(filters.command("dead"))
async def dead_cmd(client, message: Message):
    with proxy_lock:
        dead_list = list(DEAD_PROXIES)
        if dead_list:
            sample = dead_list[:5]
            await message.reply_text(
                f"💀 **Proxy CHẾT:** {len(dead_list)}\n"
                f"🔹 Mẫu: {', '.join(sample)}{'...' if len(dead_list)>5 else ''}\n"
                f"📄 File: {DEAD_PROXY_FILE}"
            )
        else:
            await message.reply_text("✅ Chưa có proxy chết nào")

@app_bot.on_message(filters.command("addproxy"))
async def addproxy_cmd(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text("❌ **Cách dùng:** `/addproxy http://user:pass@ip:port` hoặc `socks5://user:pass@ip:port`")
        return
    new_proxy = parts[1].strip()
    if not (new_proxy.startswith("http://") or new_proxy.startswith("socks5://") or new_proxy.startswith("socks4://")):
        await message.reply_text("❌ Proxy phải bắt đầu http://, socks4:// hoặc socks5://")
        return
    
    if new_proxy in PROXY_MASTER:
        await message.reply_text("⚠️ Proxy đã tồn tại trong master")
        return
    
    with open(PROXY_FILE, "a", encoding="utf-8") as f:
        f.write(new_proxy + "\n")
    
    PROXY_MASTER.add(new_proxy)
    with proxy_lock:
        PROXY_LIST.append(new_proxy)
    
    await message.reply_text(
        f"✅ **Đã thêm proxy:** {new_proxy}\n"
        f"📊 Proxy sống: {len(PROXY_LIST)}\n"
        f"📊 Proxy master: {len(PROXY_MASTER)}"
    )

@app_bot.on_message(filters.command("upload"))
async def upload_cmd(client, message: Message):
    await message.reply_text("📤 **Gửi file proxy.txt** (đính kèm) để merge")

@app_bot.on_message(filters.document)
async def handle_document(client, message: Message):
    doc = message.document
    if doc.file_name != "proxy.txt":
        await message.reply_text("⚠️ Chỉ chấp nhận file tên: `proxy.txt`")
        return
    
    msg = await message.reply_text("⏳ Đang tải và merge proxy...")
    file_path = await client.download_media(message)
    
    if not file_path:
        await msg.edit_text("❌ Không thể tải file")
        return
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            new_proxies = [line.strip() for line in f if line.strip() and not line.startswith("#")]
        
        added = 0
        for p in new_proxies:
            if p not in PROXY_MASTER:
                PROXY_MASTER.add(p)
                added += 1
                with open(PROXY_FILE, "a", encoding="utf-8") as fw:
                    fw.write(p + "\n")
        
        with proxy_lock:
            PROXY_LIST = [p for p in PROXY_MASTER if p not in DEAD_PROXIES]
        
        await msg.edit_text(
            f"✅ **Đã merge {added} proxy mới**\n"
            f"├ Tổng master: {len(PROXY_MASTER)}\n"
            f"├ Proxy sống: {len(PROXY_LIST)}\n"
            f"└ Proxy chết: {len(DEAD_PROXIES)}"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

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
        f"├ Tỷ lệ: {int((view_stats['success'] / max(1, view_stats['total'])) * 100)}%\n"
        f"├ Proxy sống: {alive}\n"
        f"├ Proxy master: {master}\n"
        f"├ Proxy chết: {dead}\n"
        f"├ PID: {os.getpid()}\n"
        f"├ Uptime: {uptime}s\n"
        f"└ Web: http://{WEB_HOST}:{WEB_PORT}"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    await message.reply_text(f"🏓 **Pong!** PID: {os.getpid()}")

@app_bot.on_message(filters.command("settings"))
async def settings_cmd(client, message: Message):
    settings_text = f"""
⚙️ **CÀI ĐẶT BOT**
━━━━━━━━━━━━━━━━━━━━━

🎯 **Cấu hình cày view:**
├ 🔢 Max workers: {MAX_WORKERS}
├ ⏱ Thời gian xem: {MIN_WATCH_TIME}-{MAX_WATCH_TIME}s
├ 🔄 Retry: {VIEW_RETRY} lần
└ 📊 Tự động check proxy: 30 phút

🌐 **Proxy settings:**
├ 📂 File: {PROXY_FILE}
├ 💀 Dead proxy: {DEAD_PROXY_FILE}
├ 🔄 Tự động reload: 60 phút
└ ✅ Hỗ trợ: HTTP, SOCKS4, SOCKS5

🔒 **Security:**
├ 🔑 API ID: {API_ID}
└ 📱 Bot Token: {BOT_TOKEN[:15]}...

📊 **Thống kê:**
├ 👁 View: {view_stats['total']}
├ ✅ Success rate: {int((view_stats['success'] / max(1, view_stats['total'])) * 100)}%
└ 🕒 Uptime: {int(time.time() - start_time)}s
"""
    await message.reply_text(settings_text)

# ===== CALLBACK HANDLER =====
@app_bot.on_callback_query()
async def handle_callback(client, callback_query):
    data = callback_query.data
    
    if data == "pause":
        await callback_query.answer("⏸ Đã tạm dừng")
    elif data == "play":
        await callback_query.answer("▶ Tiếp tục phát")
    elif data == "next":
        await callback_query.answer("⏭ Video tiếp theo")
    elif data == "refresh":
        await callback_query.answer("🔄 Đã làm mới")
    elif data == "vol_up":
        await callback_query.answer("🔊 Tăng âm lượng")
    elif data == "vol_down":
        await callback_query.answer("🔉 Giảm âm lượng")
    elif data == "download":
        await callback_query.answer("📥 Đang tải xuống...")
    elif data == "show_stats":
        await callback_query.answer("📊 Đang lấy thống kê")
        stats_text = f"""
📊 **THỐNG KÊ CHI TIẾT**
━━━━━━━━━━━━━━━━━━━━━

👁 **Tổng view:** {view_stats['total']}
✅ **Thành công:** {view_stats['success']}
❌ **Thất bại:** {view_stats['failed']}
📈 **Tỷ lệ:** {int((view_stats['success'] / max(1, view_stats['total'])) * 100)}%

🌐 **Proxy sống:** {len(PROXY_LIST)}
💀 **Proxy chết:** {len(DEAD_PROXIES)}
📂 **Proxy master:** {len(PROXY_MASTER)}

⏱ **Uptime:** {int(time.time() - start_time)} giây
"""
        await callback_query.message.reply_text(stats_text)
    elif data == "show_proxy":
        with proxy_lock:
            if PROXY_LIST:
                sample = PROXY_LIST[:5]
                proxy_text = f"""
🌐 **DANH SÁCH PROXY**
━━━━━━━━━━━━━━━━━━━━━

🟢 **Proxy sống:** {len(PROXY_LIST)}
🔴 **Proxy chết:** {len(DEAD_PROXIES)}
📂 **Tổng master:** {len(PROXY_MASTER)}

📋 **Mẫu proxy sống:**
{chr(10).join(['├ ' + p for p in sample])}
"""
                await callback_query.message.reply_text(proxy_text)
            else:
                await callback_query.message.reply_text("❌ Không có proxy sống")
    elif data == "refresh_gui":
        await callback_query.answer("🔄 Đã làm mới GUI")
    elif data == "view_video":
        await callback_query.message.reply_text(
            "📹 **Xem video mới**\n"
            "Dùng lệnh: `/view_gui VIDEO_ID SỐ_LƯỢNG`"
        )
    elif data == "player":
        await callback_query.message.reply_text(
            "🎬 **Trình phát**\n"
            "Dùng lệnh: `/player VIDEO_ID`"
        )

# ===== SIGNAL HANDLER =====
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
    
    merge_new_proxies()
    log_message(f"Loaded: alive={len(PROXY_LIST)}, master={len(PROXY_MASTER)}")
    
    await start_web_server()
    asyncio.create_task(periodic_reload())
    asyncio.create_task(periodic_check_proxy())
    asyncio.create_task(heartbeat())
    
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
