⏱ Đã xem: {random.randint(30, video_info['duration']//2)}/{video_info['duration']}s

━━━━━━━━━━━━━━━━━━━━━
🌐 **PROXY STATUS:**
├ 📡 Sống: {alive}
├ 💀 Chết: {dead}
├ 📂 Master: {len(state.proxy_master)}
├ ✅ Thành công: {state.view_stats['success']}
└ ❌ Thất bại: {state.view_stats['failed']}

━━━━━━━━━━━━━━━━━━━━━
📈 **THỐNG KÊ:**
├ 👁 Tổng view: {state.view_stats['total']}
├ 🎯 View đang chạy: {count}
├ 📊 Tỷ lệ: {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%
└ 🕒 Uptime: {int(time.time() - state.start_time)}s

━━━━━━━━━━━━━━━━━━━━━
🔘 **ĐIỀU KHIỂN:**
⏸ Tạm dừng  |  ⏭ Tiếp theo  |  🔄 Làm mới
"""
    return gui

# ===== WEB SERVER =====
async def handle_health(request):
    stats = {
        "status": "running",
        "pid": os.getpid(),
        "proxy_alive": len(state.proxy_list),
        "proxy_master": len(state.proxy_master),
        "proxy_dead": len(state.dead_proxies),
        "uptime": int(time.time() - state.start_time),
        "view_stats": {
            "total": state.view_stats["total"],
            "success": state.view_stats["success"],
            "failed": state.view_stats["failed"],
            "queued": state.view_stats["queued"],
        },
        "timestamp": datetime.now().isoformat()
    }
    return web.json_response(stats)

async def handle_stats_html(request):
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>YouTube View Bot Dashboard</title>
        <meta charset="UTF-8">
        <meta http-equiv="refresh" content="10">
        <style>
            * {{ margin: 0; padding: 0; box-sizing: border-box; }}
            body {{ font-family: 'Segoe UI', Arial, sans-serif; background: #0f0f0f; color: #fff; padding: 20px; min-height: 100vh; }}
            .container {{ max-width: 900px; margin: 0 auto; }}
            .header {{ text-align: center; padding: 30px 0; border-bottom: 1px solid #333; margin-bottom: 30px; }}
            .header h1 {{ font-size: 2.5em; color: #ff0000; }}
            .header p {{ color: #888; margin-top: 10px; }}
            .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 30px; }}
            .card {{ background: #1a1a1a; padding: 20px; border-radius: 12px; border: 1px solid #333; text-align: center; }}
            .card .value {{ font-size: 2em; font-weight: bold; margin: 10px 0; }}
            .card .label {{ color: #888; font-size: 0.9em; text-transform: uppercase; }}
            .green {{ color: #0f0; }}
            .red {{ color: #f00; }}
            .yellow {{ color: #ff0; }}
            .blue {{ color: #00f; }}
            .proxy-list {{ background: #1a1a1a; border-radius: 12px; padding: 20px; border: 1px solid #333; }}
            .proxy-list h3 {{ margin-bottom: 15px; color: #888; }}
            .proxy-item {{ padding: 5px 0; border-bottom: 1px solid #222; font-size: 0.9em; color: #aaa; }}
            .status-dot {{ display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 10px; }}
            .status-dot.online {{ background: #0f0; }}
            .status-dot.offline {{ background: #f00; }}
            .footer {{ text-align: center; margin-top: 30px; padding-top: 20px; border-top: 1px solid #333; color: #555; font-size: 0.8em; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎬 YouTube View Bot</h1>
                <p>🟢 Status: <span style="color:#0f0;">Running</span> | PID: {os.getpid()} | Uptime: {int(time.time() - state.start_time)}s</p>
            </div>
            
            <div class="grid">
                <div class="card">
                    <div class="value green">{state.view_stats['total']}</div>
                    <div class="label">Total Views</div>
                </div>
                <div class="card">
                    <div class="value green">{state.view_stats['success']}</div>
                    <div class="label">Success</div>
                </div>
                <div class="card">
                    <div class="value red">{state.view_stats['failed']}</div>
                    <div class="label">Failed</div>
                </div>
                <div class="card">
                    <div class="value green">{len(state.proxy_list)}</div>
                    <div class="label">Proxy Alive</div>
                </div>
                <div class="card">
                    <div class="value red">{len(state.dead_proxies)}</div>
                    <div class="label">Proxy Dead</div>
                </div>
                <div class="card">
                    <div class="value yellow">{len(state.proxy_master)}</div>
                    <div class="label">Proxy Master</div>
                </div>
            </div>
            
            <div class="proxy-list">
                <h3>🌐 Proxy Alive ({len(state.proxy_list)})</h3>
                {''.join([f'<div class="proxy-item"><span class="status-dot online"></span>{p[:60]}</div>' for p in list(state.proxy_list)[:10]])}
                {f'<div class="proxy-item" style="color:#555;">... và {len(state.proxy_list)-10} proxy khác</div>' if len(state.proxy_list) > 10 else ''}
            </div>
            
            <div class="footer">
                YouTube View Bot v3.0 | Web Server: {config.WEB_HOST}:{config.WEB_PORT} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
            </div>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_stats_html)
    app.router.add_get("/health", handle_health)
    app.router.add_get("/stats", handle_stats_html)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, config.WEB_HOST, config.WEB_PORT)
    await site.start()
    logger.info(f"Web server: http://{config.WEB_HOST}:{config.WEB_PORT}")

# ===== TELEGRAM BOT =====
app_bot = Client("view_bot", api_id=config.API_ID, api_hash=config.API_HASH, bot_token=config.BOT_TOKEN)

# ===== BACKGROUND TASKS =====
async def periodic_reload():
    while state.running:
        await asyncio.sleep(config.PROXY_RELOAD_INTERVAL)
        if state.running:
            alive, added = await asyncio.to_thread(reload_proxies)
            logger.info(f"Auto reload: {alive} alive, {added} added")

async def periodic_check_proxy():
    while state.running:
        await asyncio.sleep(config.PROXY_CHECK_INTERVAL)
        if state.running:
            dead = await asyncio.to_thread(scan_dead_proxies)
            logger.info(f"Proxy check: {dead} dead removed")

async def periodic_save_stats():
    while state.running:
        await asyncio.sleep(config.HEARTBEAT_INTERVAL)
        if state.running:
            await asyncio.to_thread(save_stats)
            logger.debug(f"Stats saved: total={state.view_stats['total']}")

async def heartbeat():
    while state.running:
        await asyncio.sleep(config.HEARTBEAT_INTERVAL)
        if state.running:
            with state.proxy_lock:
                alive = len(state.proxy_list)
                master = len(state.proxy_master)
                dead = len(state.dead_proxies)
            logger.info(f"Heartbeat: alive={alive}, master={master}, dead={dead}, views={state.view_stats['total']}")

# ===== TELEGRAM COMMANDS =====
@app_bot.on_message(filters.command("start"))
async def start_cmd(client, message: Message):
    with state.proxy_lock:
        alive = len(state.proxy_list)
        master = len(state.proxy_master)
        dead = len(state.dead_proxies)
    
    await message.reply_text(
        f"🎬 **YouTube View Bot v3.0**\n\n"
        f"📌 **LỆNH:**\n"
        f"├ `/view VIDEO_ID SỐ_LƯỢNG` - Cày view (1-500)\n"
        f"├ `/view_gui VIDEO_ID SỐ_LƯỢNG` - Cày view với GUI\n"
        f"├ `/player VIDEO_ID` - Trình phát mô phỏng\n"
        f"├ `/gui` - Menu GUI chính\n"
        f"├ `/upload` - Upload file .txt (proxy)\n"
        f"├ `/reload` - Tải lại proxy\n"
        f"├ `/proxy` - Xem proxy sống\n"
        f"├ `/dead` - Xem proxy chết\n"
        f"├ `/check` - Quét proxy chết\n"
        f"├ `/addproxy PROXY` - Thêm proxy\n"
        f"├ `/stats` - Thống kê\n"
        f"├ `/ping` - Kiểm tra bot\n"
        f"└ `/settings` - Cài đặt\n\n"
        f"📂 **Proxy sống:** {alive}\n"
        f"📂 **Proxy master:** {master}\n"
        f"💀 **Proxy chết:** {dead}\n"
        f"👁 **Tổng view:** {state.view_stats['total']}"
    )

@app_bot.on_message(filters.command("view"))
async def view_cmd(client, message: Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.reply_text("❌ **Cách dùng:** `/view VIDEO_ID SỐ_LƯỢNG`\nSố lượng: 1-500")
        return
    
    video_id = parts[1].strip()
    if len(video_id) != 11:
        await message.reply_text("❌ Video ID phải có 11 ký tự")
        return
    
    try:
        count = int(parts[2])
        if count < 1 or count > 500:
            await message.reply_text("❌ Số lượng phải từ 1-500")
            return
    except ValueError:
        await message.reply_text("❌ Số lượng phải là số nguyên")
        return

    with state.proxy_lock:
        if not state.proxy_list:
            await message.reply_text("❌ Không có proxy sống. Upload file .txt")
            return

    msg = await message.reply_text(f"⏳ Đang cày {count} view cho video...")
    
    try:
        success, info = await asyncio.to_thread(run_view_task, video_id, count)
        await msg.edit_text(
            f"✅ **{info}**\n"
            f"🎯 https://youtu.be/{video_id}\n"
            f"📊 Tổng: {state.view_stats['total']} views\n"
            f"📈 Tỷ lệ: {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")

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

    with state.proxy_lock:
        if not state.proxy_list:
            await message.reply_text("❌ Không có proxy sống")
            return

    gui_text = create_video_gui(video_id, count)
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
    video_info = VIDEO_DB.get(video_id, {"title": f"Video {video_id}", "duration": random.randint(180, 420)})
    
    player_text = f"""
🎬 **YOUTUBE PLAYER PRO**
━━━━━━━━━━━━━━━━━━━━━

📹 **Đang phát:**
└ {video_info['title']}

🖼 **Thumbnail:** https://img.youtube.com/vi/{video_id}/hqdefault.jpg

━━━━━━━━━━━━━━━━━━━━━
▶️ **TRẠNG THÁI:**
├ 🟢 Đang phát
├ ⏱ 00:42 / {video_info['duration']//60}:{video_info['duration']%60:02d}
├ 📹 1080p60
└ 🔊 {random.randint(60, 95)}%

━━━━━━━━━━━━━━━━━━━━━
⚡ **THÔNG TIN:**
├ 👁 {random.randint(100000, 9999999):,} lượt xem
├ 👍 {random.randint(1000, 99999):,} lượt thích
├ 💬 {random.randint(100, 9999):,} bình luận
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
🎮 **BOT GUI CONTROLLER v3.0**
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
   └ `/upload` - Upload file .txt
   └ `/addproxy PROXY` - Thêm proxy

5️⃣ **⚙️ Cài đặt**
   └ `/settings`

━━━━━━━━━━━━━━━━━━━━━
🟢 **Trạng thái:** Đang chạy
🔄 **Proxy sống:** {len(state.proxy_list)}
💀 **Proxy chết:** {len(state.dead_proxies)}
📂 **Proxy master:** {len(state.proxy_master)}
👁 **Tổng view:** {state.view_stats['total']}
📈 **Tỷ lệ:** {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%
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

@app_bot.on_message(filters.command("upload"))
async def upload_cmd(client, message: Message):
    await message.reply_text(
        "📤 **Gửi file .txt** bất kỳ (đính kèm)\n"
        "Bot sẽ đọc proxy từ file và merge vào danh sách\n\n"
        "✅ **Định dạng proxy:**\n"
        "├ http://user:pass@ip:port\n"
        "├ https://user:pass@ip:port\n"
        "├ socks4://user:pass@ip:port\n"
        "└ socks5://user:pass@ip:port"
    )

@app_bot.on_message(filters.document)
async def handle_document(client, message: Message):
    doc = message.document
    if not doc.file_name.endswith(".txt"):
        await message.reply_text("⚠️ Chỉ chấp nhận file .txt")
        return
    
    msg = await message.reply_text(f"⏳ Đang xử lý: `{doc.file_name}`...")
    file_path = await client.download_media(message)
    
    if not file_path:
        await msg.edit_text("❌ Không thể tải file")
        return
    
    try:
        # Đếm proxy
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith("#")]
            total_in_file = len(lines)
        
        # Merge
        added, alive = await asyncio.to_thread(merge_proxies_from_file, file_path)
        
        await msg.edit_text(
            f"✅ **Đã xử lý: {doc.file_name}**\n"
            f"├ Tổng proxy trong file: {total_in_file}\n"
            f"├ Đã thêm mới: {added}\n"
            f"├ Proxy sống: {alive}\n"
            f"├ Proxy master: {len(state.proxy_master)}\n"
            f"└ Proxy chết: {len(state.dead_proxies)}"
        )
    except Exception as e:
        await msg.edit_text(f"❌ Lỗi: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app_bot.on_message(filters.command("reload"))
async def reload_cmd(client, message: Message):
    alive, added = await asyncio.to_thread(reload_proxies)
    with state.proxy_lock:
        master = len(state.proxy_master)
        dead = len(state.dead_proxies)
    await message.reply_text(
        f"🔄 **Đã reload proxy**\n"
        f"├ Thêm mới: {added}\n"
        f"├ Proxy sống: {alive}\n"
        f"├ Proxy master: {master}\n"
        f"└ Proxy chết: {dead}"
    )

@app_bot.on_message(filters.command("proxy"))
async def proxy_cmd(client, message: Message):
    with state.proxy_lock:
        if state.proxy_list:
            sample = state.proxy_list[:10]
            text = f"📋 **Proxy SỐNG:** {len(state.proxy_list)}\n"
            for i, p in enumerate(sample, 1):
                text += f"├ {i}. {p}\n"
            if len(state.proxy_list) > 10:
                text += f"└ ... và {len(state.proxy_list)-10} proxy khác"
            await message.reply_text(text)
        else:
            await message.reply_text("❌ Không có proxy sống. Upload file .txt")

@app_bot.on_message(filters.command("dead"))
async def dead_cmd(client, message: Message):
    with state.proxy_lock:
        dead_list = list(state.dead_proxies)
        if dead_list:
            sample = dead_list[:10]
            text = f"💀 **Proxy CHẾT:** {len(dead_list)}\n"
            for i, p in enumerate(sample, 1):
                text += f"├ {i}. {p}\n"
            if len(dead_list) > 10:
                text += f"└ ... và {len(dead_list)-10} proxy khác"
            await message.reply_text(text)
        else:
            await message.reply_text("✅ Chưa có proxy chết nào")

@app_bot.on_message(filters.command("addproxy"))
async def addproxy_cmd(client, message: Message):
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply_text(
            "❌ **Cách dùng:** `/addproxy PROXY`\n\n"
            "✅ **Ví dụ:**\n"
            "├ /addproxy http://user:pass@1.2.3.4:8080\n"
            "└ /addproxy socks5://user:pass@1.2.3.4:1080"
        )
        return
    
    new_proxy = parts[1].strip()
    
    # Kiểm tra định dạng
    if not re.match(r'^(\w+://)?[\w\.\-]+:\d+(@[\w\.\-]+:\d+)?$', new_proxy):
        if ':' not in new_proxy:
            await message.reply_text("❌ Định dạng proxy không hợp lệ")
            return
    
    if new_proxy in state.proxy_master:
        await message.reply_text("⚠️ Proxy đã tồn tại trong master")
        return
    
    # Thêm vào file và master
    with open(config.PROXY_FILE, "a", encoding="utf-8") as f:
        f.write(new_proxy + "\n")
    
    with state.proxy_lock:
        state.proxy_master.add(new_proxy)
        state.proxy_stats[new_proxy] = {"fail": 0, "success": 0, "last_used": 0}
        state.proxy_list.append(new_proxy)
    
    await message.reply_text(
        f"✅ **Đã thêm proxy:** {new_proxy}\n"
        f"├ Proxy sống: {len(state.proxy_list)}\n"
        f"└ Proxy master: {len(state.proxy_master)}"
    )

@app_bot.on_message(filters.command("check"))
async def check_cmd(client, message: Message):
    msg = await message.reply_text("⏳ Đang quét proxy chết...")
    dead = await asyncio.to_thread(scan_dead_proxies)
    with state.proxy_lock:
        alive = len(state.proxy_list)
    await msg.edit_text(
        f"✅ **Quét hoàn tất**\n"
        f"├ Proxy chết đã loại: {dead}\n"
        f"├ Proxy sống còn: {alive}\n"
        f"└ Tổng proxy đã chết: {len(state.dead_proxies)}"
    )

@app_bot.on_message(filters.command("stats"))
async def stats_cmd(client, message: Message):
    uptime = int(time.time() - state.start_time)
    with state.proxy_lock:
        alive = len(state.proxy_list)
        master = len(state.proxy_master)
        dead = len(state.dead_proxies)
    
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    seconds = uptime % 60
    
    await message.reply_text(
        f"📊 **THỐNG KÊ CHI TIẾT**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"👁 **Tổng view:** {state.view_stats['total']:,}\n"
        f"✅ **Thành công:** {state.view_stats['success']:,}\n"
        f"❌ **Thất bại:** {state.view_stats['failed']:,}\n"
        f"📈 **Tỷ lệ:** {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%\n"
        f"\n"
        f"🌐 **Proxy sống:** {alive}\n"
        f"📂 **Proxy master:** {master}\n"
        f"💀 **Proxy chết:** {dead}\n"
        f"\n"
        f"⏱ **Uptime:** {hours}h {minutes}m {seconds}s\n"
        f"🕒 **Bắt đầu:** {datetime.fromtimestamp(state.start_time).strftime('%d/%m/%Y %H:%M:%S')}\n"
        f"📊 **PID:** {os.getpid()}\n"
        f"🌐 **Web:** http://{config.WEB_HOST}:{config.WEB_PORT}"
    )

@app_bot.on_message(filters.command("ping"))
async def ping_cmd(client, message: Message):
    await message.reply_text(
        f"🏓 **Pong!**\n"
        f"├ PID: {os.getpid()}\n"
        f"├ Proxy: {len(state.proxy_list)} sống\n"
        f"└ Views: {state.view_stats['total']}"
    )

@app_bot.on_message(filters.command("settings"))
async def settings_cmd(client, message: Message):
    settings_text = f"""
⚙️ **CÀI ĐẶT BOT v3.0**
━━━━━━━━━━━━━━━━━━━━━

🎯 **Cấu hình cày view:**
├ 🔢 Max workers: {config.MAX_WORKERS}
├ ⏱ Thời gian xem: {config.MIN_WATCH_TIME}-{config.MAX_WATCH_TIME}s
├ 🔄 Retry: {config.VIEW_RETRY} lần
└ 📦 Batch size: {config.VIEW_BATCH_SIZE}

🌐 **Proxy settings:**
├ 📂 File: {config.PROXY_FILE}
├ 💀 Dead: {config.DEAD_PROXY_FILE}
├ 🔄 Auto reload: {config.PROXY_RELOAD_INTERVAL//60} phút
├ 🔍 Auto check: {config.PROXY_CHECK_INTERVAL//60} phút
└ ✅ Hỗ trợ: HTTP, HTTPS, SOCKS4, SOCKS5

🔒 **Security:**
├ 🔑 API ID: {config.API_ID}
└ 📱 Bot: {config.BOT_TOKEN[:15]}...

📊 **Thống kê:**
├ 👁 View: {state.view_stats['total']:,}
├ ✅ Success: {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%
└ 🕒 Uptime: {int(time.time() - state.start_time)}s

💾 **Backup:** {'✅ Bật' if config.AUTO_BACKUP else '❌ Tắt'}
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
        uptime = int(time.time() - state.start_time)
        await callback_query.message.reply_text(
            f"📊 **THỐNG KÊ**\n"
            f"├ 👁 Views: {state.view_stats['total']:,}\n"
            f"├ ✅ Success: {state.view_stats['success']:,}\n"
            f"├ ❌ Failed: {state.view_stats['failed']:,}\n"
            f"├ 📈 Rate: {int((state.view_stats['success'] / max(1, state.view_stats['total'])) * 100)}%\n"
            f"├ 🌐 Proxy: {len(state.proxy_list)} sống\n"
            f"└ ⏱ Uptime: {uptime}s"
        )
    elif data == "show_proxy":
        with state.proxy_lock:
            if state.proxy_list:
                sample = state.proxy_list[:5]
                text = f"🌐 **Proxy sống:** {len(state.proxy_list)}\n"
                for p in sample:
                    text += f"├ {p}\n"
                await callback_query.message.reply_text(text)
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
    logger.info(f"Signal {sig}, shutting down...")
    state.running = False
    save_stats()
    remove_pid()
    sys.exit(0)

# ===== MAIN =====
async def main():
    global app_bot
    
    if check_already_running():
        logger.info("Bot đã chạy, thoát.")
        sys.exit(1)
    
    write_pid()
    logger.info(f"Khởi động bot v3.0, PID: {os.getpid()}")
    
    # Load stats
    load_stats()
    
    # Load proxy
    merge_proxies_from_file(config.PROXY_FILE)
    logger.info(f"Loaded: alive={len(state.proxy_list)}, master={len(state.proxy_master)}")
    
    # Backup lần đầu
    if config.AUTO_BACKUP:
        backup_proxies()
    
    # Start web server
    await start_web_server()
    
    # Start background tasks
    asyncio.create_task(periodic_reload())
    asyncio.create_task(periodic_check_proxy())
    asyncio.create_task(periodic_save_stats())
    asyncio.create_task(heartbeat())
    
    try:
        await app_bot.start()
        logger.info("Bot Telegram đã kết nối")
        
        while state.running:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Lỗi bot: {e}")
    finally:
        if app_bot:
            await app_bot.stop()
        save_stats()
        remove_pid()
        logger.info("Bot đã dừng")

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
        logger.info("Keyboard interrupt")
        remove_pid()
    except Exception as e:
        logger.error(f"Lỗi fatal: {e}")
        remove_pid()
