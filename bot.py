"""
Nexus Proxy Manager Bot — Public Version
- Ai cũng dùng được (không check admin)
- Rate limiting để tránh spam
- Proxy management (upload, validate, export, clean, random)
- Layer 7 Defense
- 24/7 Keep-alive
- No attack commands — defensive only
"""

import os
import sys
import types
import warnings
import json
import re
import time
import asyncio
import threading
import subprocess
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============================================
# 🔧 CONFIGURATION
# ============================================

TELEGRAM_BOT_TOKEN = "PASTE_YOUR_BOT_TOKEN_HERE"  # <--- Điền token
HEALTH_PORT = 8080
RATE_LIMIT = 10  # Số lệnh tối đa mỗi phút

# ============================================
# 🔧 FIX 1: pkg_resources
# ============================================

def _fix_pkg_resources():
    try:
        import pkg_resources
        return True
    except ImportError:
        try:
            mock_module = types.ModuleType('pkg_resources')
            
            def get_distribution(dist_name):
                class Dist:
                    version = "0.0.0"
                    project_name = dist_name
                    def __str__(self):
                        return f"{self.project_name} {self.version}"
                return Dist()
            
            def require(requirement):
                pass
            
            def iter_entry_points(group, name=None):
                return []
            
            def working_set():
                return []
            
            def parse_version(version):
                return version
            
            mock_module.get_distribution = get_distribution
            mock_module.require = require
            mock_module.iter_entry_points = iter_entry_points
            mock_module.working_set = working_set
            mock_module.parse_version = parse_version
            mock_module.VersionConflict = Exception
            mock_module.DistributionNotFound = Exception
            mock_module.ExtractionError = Exception
            
            sys.modules['pkg_resources'] = mock_module
            return True
        except:
            return False

_fix_pkg_resources()

# ============================================
# 🔧 FIX 2: urllib3.contrib.appengine
# ============================================

def _fix_urllib3_appengine():
    try:
        import urllib3.contrib.appengine
        return True
    except ImportError:
        try:
            mock_module = types.ModuleType('urllib3.contrib.appengine')
            
            def is_appengine_sandbox():
                return False
            def is_appengine():
                return False
            def AppEngineManager(connection_pool):
                return connection_pool
            def _get_connection(connection_pool):
                return connection_pool._get_connection()
            
            mock_module.is_appengine_sandbox = is_appengine_sandbox
            mock_module.is_appengine = is_appengine
            mock_module.AppEngineManager = AppEngineManager
            mock_module._get_connection = _get_connection
            
            import urllib3.contrib
            urllib3.contrib.appengine = mock_module
            sys.modules['urllib3.contrib.appengine'] = mock_module
            return True
        except:
            return False

_fix_urllib3_appengine()

# ============================================
# 🔧 FIX 3: imghdr (Python 3.14+)
# ============================================

def _create_imghdr_mock():
    mock = types.ModuleType("imghdr")
    def what(file, h=None):
        try:
            import filetype
            if isinstance(file, str):
                with open(file, 'rb') as f:
                    data = f.read(261)
            else:
                data = file.read(261) if hasattr(file, 'read') else file
            guess = filetype.guess(data)
            return guess.extension if guess else None
        except:
            return None
    mock.what = what
    return mock

try:
    import imghdr
    if not hasattr(imghdr, 'what'):
        raise ImportError
except (ImportError, AttributeError):
    imghdr = _create_imghdr_mock()
    sys.modules['imghdr'] = imghdr

# ============================================
# 🔧 FIX 4: Suppress warnings
# ============================================
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ============================================
# 🔧 FIX 5: Imports
# ============================================
import logging
import filetype
import aiohttp
import requests
import psutil

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    Filters,
    CallbackContext
)

# ============================================
# 🔧 FIX 6: Logging
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info(f"🐍 Python version: {sys.version}")

# ============================================
# 🔧 FIX 7: Data Models
# ============================================
@dataclass
class Proxy:
    ip: str
    port: int
    protocol: str = "http"
    speed: float = 0.0
    is_alive: bool = True
    last_checked: Optional[str] = None
    fail_count: int = 0
    source: str = "upload"
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "speed": self.speed,
            "is_alive": self.is_alive,
            "last_checked": self.last_checked,
            "fail_count": self.fail_count,
            "source": self.source,
            "added_at": self.added_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Proxy':
        return cls(
            ip=data.get("ip", ""),
            port=int(data.get("port", 0)),
            protocol=data.get("protocol", "http"),
            speed=float(data.get("speed", 0.0)),
            is_alive=data.get("is_alive", True),
            last_checked=data.get("last_checked"),
            fail_count=int(data.get("fail_count", 0)),
            source=data.get("source", "upload"),
            added_at=data.get("added_at", datetime.now().isoformat())
        )
    
    def to_proxy_string(self):
        return f"{self.ip}:{self.port}"

# ============================================
# 🔧 FIX 8: In-Memory Storage
# ============================================
class MemoryStorage:
    def __init__(self):
        self.data = {}
        self.expiry = {}
        self.lists = defaultdict(list)
        self.sets = defaultdict(set)
        self.hashe = defaultdict(dict)
        
    async def set(self, key: str, value: str, ex: int = None):
        self.data[key] = value
        if ex:
            self.expiry[key] = time.time() + ex
            
    async def get(self, key: str) -> Optional[str]:
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
        
    async def delete(self, key: str):
        if key in self.data:
            del self.data[key]
        if key in self.expiry:
            del self.expiry[key]
            
    async def keys(self) -> List[str]:
        return list(self.data.keys())
        
    async def lpush(self, key: str, value: str):
        self.lists[key].insert(0, value)
        
    async def ltrim(self, key: str, start: int, end: int):
        self.lists[key] = self.lists[key][start:end]
        
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        return self.lists.get(key, [])[start:end]
        
    async def sadd(self, key: str, value: str):
        self.sets[key].add(value)
        
    async def srem(self, key: str, value: str):
        if key in self.sets:
            self.sets[key].discard(value)
            
    async def smembers(self, key: str) -> Set[str]:
        return self.sets.get(key, set())
        
    async def hset(self, key: str, field: str, value: str):
        self.hashe[key][field] = value
        
    async def hget(self, key: str, field: str) -> Optional[str]:
        return self.hashe.get(key, {}).get(field)
        
    async def hgetall(self, key: str) -> dict:
        return self.hashe.get(key, {})
        
    async def hdel(self, key: str, field: str):
        if key in self.hashe and field in self.hashe[key]:
            del self.hashe[key][field]

storage = MemoryStorage()

# ============================================
# 🔧 FIX 9: Rate Limiter (Public)
# ============================================
user_commands = defaultdict(list)

def check_rate_limit(user_id: int) -> bool:
    """Kiểm tra rate limit cho user"""
    now = time.time()
    commands = user_commands[user_id]
    # Xóa commands cũ hơn 60 giây
    commands = [t for t in commands if now - t < 60]
    if len(commands) >= RATE_LIMIT:
        return False
    commands.append(now)
    user_commands[user_id] = commands
    return True

# ============================================
# 🔧 FIX 10: Proxy Manager
# ============================================
class ProxyManager:
    def __init__(self):
        self.proxies: Dict[str, Proxy] = {}
        self._initialized = False
        self.validating = False
        
    async def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info(f"ProxyManager initialized — {len(self.proxies)} proxies")
        
    def _parse_proxy_line(self, line: str) -> Optional[Proxy]:
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        patterns = [
            r'^(https?|socks[45])://([^:]+):(\d+)$',
            r'^([^:]+):(\d+):(https?|socks[45])$',
            r'^([^:]+):(\d+)$',
            r'^([^:]+)\s+(\d+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if '://' in line:
                        protocol, ip, port = groups
                    else:
                        ip, port, protocol = groups
                elif len(groups) == 2:
                    ip, port = groups
                    protocol = "http"
                else:
                    continue
                    
                try:
                    port = int(port)
                    if 1 <= port <= 65535:
                        return Proxy(ip=ip, port=port, protocol=protocol)
                except ValueError:
                    continue
        return None
        
    def detect_format(self, content: str) -> Dict[str, Any]:
        lines = content.strip().split('\n')
        valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        
        if not valid_lines:
            return {"format": "unknown", "count": 0, "sample": None}
            
        formats = []
        for line in valid_lines[:10]:
            proxy = self._parse_proxy_line(line)
            if proxy:
                formats.append(proxy.protocol)
                
        if not formats:
            return {"format": "unknown", "count": 0, "sample": None}
            
        return {
            "format": max(set(formats), key=formats.count) if formats else "http",
            "count": len(valid_lines),
            "sample": valid_lines[0] if valid_lines else None
        }
        
    async def load_from_text(self, content: str, source: str = "upload") -> Tuple[int, int, str]:
        lines = content.strip().split('\n')
        loaded = 0
        duplicate = 0
        
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
                
            proxy = self._parse_proxy_line(line)
            if proxy:
                proxy.source = source
                proxy_id = f"{proxy.ip}:{proxy.port}"
                
                if proxy_id in self.proxies:
                    duplicate += 1
                    continue
                    
                self.proxies[proxy_id] = proxy
                loaded += 1
                
        return loaded, duplicate, "http"
        
    async def load_from_url(self, url: str) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        return 0
                    content = await resp.text()
                    loaded, _, _ = await self.load_from_text(content, source=f"url:{url}")
                    return loaded
        except Exception as e:
            logger.error(f"Failed to load from URL: {e}")
            return 0
            
    async def validate_proxy(self, proxy: Proxy) -> bool:
        try:
            url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
            start = time.time()
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=url,
                    timeout=5,
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        proxy.is_alive = True
                        proxy.speed = (time.time() - start) * 1000
                        proxy.last_checked = datetime.now().isoformat()
                        proxy.fail_count = 0
                        return True
        except Exception:
            pass
            
        proxy.is_alive = False
        proxy.fail_count += 1
        proxy.last_checked = datetime.now().isoformat()
        return False
        
    async def validate_all(self, max_concurrent: int = 20) -> Dict[str, Any]:
        if self.validating:
            return {"status": "already_running"}
            
        self.validating = True
        try:
            proxies = list(self.proxies.values())
            if not proxies:
                return {"total": 0, "validated": 0}
                
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def validate_one(proxy):
                async with semaphore:
                    return await self.validate_proxy(proxy)
                    
            tasks = [validate_one(p) for p in proxies]
            results = await asyncio.gather(*tasks)
            
            validated = sum(1 for r in results if r)
            
            return {
                "total": len(proxies),
                "validated": validated,
                "failed": len(proxies) - validated
            }
        finally:
            self.validating = False
            
    def get_stats(self) -> Dict[str, Any]:
        alive = sum(1 for p in self.proxies.values() if p.is_alive)
        return {
            "total": len(self.proxies),
            "alive": alive,
            "dead": len(self.proxies) - alive,
            "last_update": datetime.now().isoformat()
        }
        
    def get_alive_proxies(self) -> List[Proxy]:
        return [p for p in self.proxies.values() if p.is_alive]
        
    def get_random_alive(self) -> Optional[Proxy]:
        alive = self.get_alive_proxies()
        if not alive:
            return None
        import random
        return random.choice(alive)
        
    async def clean_dead(self) -> int:
        dead = [pid for pid, p in self.proxies.items() if not p.is_alive]
        for pid in dead:
            del self.proxies[pid]
        return len(dead)

proxy_manager = ProxyManager()

# ============================================
# 🔧 FIX 11: Layer 7 Defense Engine
# ============================================
class Layer7DefenseEngine:
    def __init__(self):
        self.attack_log = deque(maxlen=1000)
        self.blocked_ips: Set[str] = set()
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "attacks_detected": 0,
            "blocked_ips": 0,
            "last_attack": None,
            "attack_types": defaultdict(int),
            "start_time": datetime.now().isoformat()
        }
        
    async def _block_ip(self, ip: str, reason: str, duration: int = 3600):
        if ip in self.blocked_ips:
            return
        self.blocked_ips.add(ip)
        self.stats["blocked_ips"] += 1
        
        block_data = {
            "ip": ip,
            "reason": reason,
            "blocked_at": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(seconds=duration)).isoformat()
        }
        
        await storage.set(f"blocked:{ip}", json.dumps(block_data), duration)
        await storage.set("blocked_ips", json.dumps(list(self.blocked_ips)))
        logger.warning(f"🔒 Blocked IP: {ip} - {reason}")
        
    async def _log_attack(self, attack_data: dict):
        key = f"attacks:{datetime.now().strftime('%Y%m%d')}"
        await storage.lpush(key, json.dumps(attack_data))
        await storage.ltrim(key, 0, 999)
        self.attack_log.append(attack_data)
        self.stats["last_attack"] = attack_data.get("timestamp")
        
    async def get_attacks(self, limit: int = 50) -> List[Dict]:
        key = f"attacks:{datetime.now().strftime('%Y%m%d')}"
        attacks = await storage.lrange(key, 0, limit - 1)
        return [json.loads(a) for a in attacks]
        
    async def get_blocked_ips(self) -> List[Dict]:
        keys = await storage.keys()
        blocked = []
        for key in keys:
            if key.startswith("blocked:"):
                data = await storage.get(key)
                if data:
                    blocked.append(json.loads(data))
        return blocked
        
    async def unblock_ip(self, ip: str) -> bool:
        if ip not in self.blocked_ips:
            return False
        self.blocked_ips.remove(ip)
        await storage.delete(f"blocked:{ip}")
        await storage.set("blocked_ips", json.dumps(list(self.blocked_ips)))
        logger.info(f"🔓 Unblocked IP: {ip}")
        return True
        
    def get_stats(self) -> Dict[str, Any]:
        return {
            **self.stats,
            "attack_types": dict(self.stats["attack_types"]),
            "blocked_ips_count": len(self.blocked_ips),
            "attack_log_count": len(self.attack_log),
            "mode": "In-Memory"
        }

layer7_engine = Layer7DefenseEngine()

# ============================================
# 🔧 FIX 12: Uptime Monitor
# ============================================
class UptimeMonitor:
    def __init__(self):
        self.start_time = datetime.now()
        self.last_ping = datetime.now()
        self.ping_count = 0
        self.error_count = 0
        self.restart_count = 0
        
    def get_uptime(self):
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_stats(self):
        try:
            mem = psutil.Process().memory_info().rss / 1024 / 1024
            cpu = psutil.Process().cpu_percent()
        except:
            mem = 0
            cpu = 0
            
        return {
            "uptime_seconds": self.get_uptime(),
            "uptime_hours": self.get_uptime() / 3600,
            "ping_count": self.ping_count,
            "error_count": self.error_count,
            "restart_count": self.restart_count,
            "last_ping": self.last_ping.isoformat(),
            "memory_usage_mb": mem,
            "cpu_percent": cpu
        }
    
    def record_ping(self):
        self.ping_count += 1
        self.last_ping = datetime.now()
    
    def record_error(self):
        self.error_count += 1
    
    def record_restart(self):
        self.restart_count += 1

uptime_monitor = UptimeMonitor()

# ============================================
# 🔧 FIX 13: Health Check Server
# ============================================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            stats = proxy_manager.get_stats()
            stats['uptime'] = uptime_monitor.get_stats()
            self.wfile.write(json.dumps(stats).encode())
        else:
            self.send_response(404)
            self.end_headers()

def start_health_server(port=8080):
    try:
        server = HTTPServer(('0.0.0.0', port), HealthHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        logger.info(f"✅ Health check server running on port {port}")
        return server
    except Exception as e:
        logger.warning(f"⚠️ Health server failed: {e}")
        return None

# ============================================
# 🔧 FIX 14: Bot Handlers (PUBLIC — No Admin Check)
# ============================================

def check_user_rate_limit(update: Update) -> bool:
    """Kiểm tra rate limit cho user"""
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        update.message.reply_text(
            f"⏳ **Rate limit exceeded**\n"
            f"Maximum {RATE_LIMIT} commands per minute.\n"
            f"Please wait a moment."
        )
        return False
    return True

# --- COMMAND HANDLERS ---

def start(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    stats = proxy_manager.get_stats()
    l7_stats = layer7_engine.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("✅ Validate", callback_data="validate")],
        [InlineKeyboardButton("📤 Export Alive", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean Dead", callback_data="clean")],
        [InlineKeyboardButton("🎲 Random Proxy", callback_data="random")],
        [InlineKeyboardButton("🛡️ Layer 7 Stats", callback_data="l7_stats")],
        [InlineKeyboardButton("🚨 Attacks", callback_data="attacks")],
        [InlineKeyboardButton("🔒 Blocked IPs", callback_data="blocked")],
        [InlineKeyboardButton("⏱️ Uptime", callback_data="uptime")],
    ]
    
    update.message.reply_text(
        f"🛡️ **Nexus Proxy Manager Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: 🟢 Online\n"
        f"📦 Proxies: {stats['total']}\n"
        f"✅ Alive: {stats['alive']}\n"
        f"❌ Dead: {stats['dead']}\n"
        f"🚨 Attacks: {l7_stats['attacks_detected']}\n"
        f"🔒 Blocked IPs: {l7_stats['blocked_ips']}\n"
        f"⏱️ Uptime: {uptime_monitor.get_stats()['uptime_hours']:.1f}h\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👥 **Public Mode** — Everyone can use\n"
        f"⏳ Rate limit: {RATE_LIMIT} commands/minute\n"
        f"📤 Upload .txt file with proxies\n"
        f"📋 Format: ip:port (one per line)\n"
        f"🔒 **Defensive Mode Only**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def stats(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    stats = proxy_manager.get_stats()
    
    msg = (
        f"📊 **Proxy Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total: {stats['total']}\n"
        f"✅ Alive: {stats['alive']}\n"
        f"❌ Dead: {stats['dead']}\n"
        f"📈 Rate: {(stats['alive'] / max(stats['total'], 1) * 100):.1f}%\n"
        f"🔄 Last Update: {stats['last_update'][:19] if stats['last_update'] else 'Never'}"
    )
    
    update.message.reply_text(msg, parse_mode="Markdown")

def validate(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    if proxy_manager.validating:
        update.message.reply_text("⏳ Validation already running...")
        return
        
    update.message.reply_text("🔄 Validating proxies... (may take a few minutes)")
    
    result = asyncio.run(proxy_manager.validate_all(max_concurrent=20))
    
    if result.get("status") == "already_running":
        update.message.reply_text("⏳ Validation already running...")
        return
        
    msg = (
        f"✅ **Validation Complete**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: {result['total']}\n"
        f"✅ Alive: {result['validated']}\n"
        f"❌ Dead: {result['failed']}\n"
        f"📈 Rate: {(result['validated'] / max(result['total'], 1) * 100):.1f}%"
    )
    
    update.message.reply_text(msg, parse_mode="Markdown")

def export(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    alive = proxy_manager.get_alive_proxies()
    
    if not alive:
        update.message.reply_text("⚠️ No alive proxies to export")
        return
        
    content = "\n".join([p.to_proxy_string() for p in alive])
    filename = f"alive_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    update.message.reply_document(
        document=content.encode('utf-8'),
        filename=filename
    )

def clean(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    update.message.reply_text("🧹 Cleaning dead proxies...")
    removed = asyncio.run(proxy_manager.clean_dead())
    update.message.reply_text(f"🧹 Removed {removed} dead proxies")

def random_proxy(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    proxy = proxy_manager.get_random_alive()
    
    if not proxy:
        update.message.reply_text("⚠️ No alive proxies available")
        return
        
    msg = (
        f"🎲 **Random Proxy**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"IP: `{proxy.ip}`\n"
        f"Port: `{proxy.port}`\n"
        f"Protocol: `{proxy.protocol}`\n"
        f"Speed: `{proxy.speed:.0f}ms`\n"
        f"Source: `{proxy.source}`"
    )
    
    update.message.reply_text(msg, parse_mode="Markdown")

def l7_stats(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    stats = layer7_engine.get_stats()
    
    msg = (
        f"🛡️ **Layer 7 Defense Stats**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📊 Total Requests: {stats['total_requests']}\n"
        f"🚫 Blocked: {stats['blocked_requests']}\n"
        f"🚨 Attacks Detected: {stats['attacks_detected']}\n"
        f"🔒 Blocked IPs: {stats['blocked_ips']}\n"
        f"💾 Mode: {stats.get('mode', 'In-Memory')}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 **Attack Types:**\n"
    )
    
    for attack_type, count in stats.get('attack_types', {}).items():
        msg += f"  • {attack_type}: {count}\n"
        
    msg += f"\n🕒 Last Attack: {stats.get('last_attack', 'None')}"
    
    update.message.reply_text(msg, parse_mode="Markdown")

def show_attacks(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    attacks = asyncio.run(layer7_engine.get_attacks(20))
    
    if not attacks:
        update.message.reply_text("✅ No attacks detected")
        return
        
    msg = "🚨 **Recent Attacks**\n━━━━━━━━━━━━━━━━━━\n"
    for attack in attacks[:10]:
        msg += (
            f"• {attack.get('timestamp', '')[:19]} - "
            f"{attack.get('type', 'unknown')} "
            f"from {attack.get('ip', 'unknown')} "
            f"({attack.get('severity', 'low')})\n"
        )
        
    update.message.reply_text(msg, parse_mode="Markdown")

def show_blocked(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    blocked = asyncio.run(layer7_engine.get_blocked_ips())
    
    if not blocked:
        update.message.reply_text("✅ No IPs blocked")
        return
        
    msg = "🔒 **Blocked IPs**\n━━━━━━━━━━━━━━━━━━\n"
    for entry in blocked[:10]:
        msg += (
            f"• {entry.get('ip')} - {entry.get('reason')}\n"
            f"  Expires: {entry.get('expires', '')[:19]}\n"
        )
        
    update.message.reply_text(msg, parse_mode="Markdown")

def unblock_ip(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    args = context.args
    if not args:
        update.message.reply_text("⚠️ Usage: /unblock <ip>")
        return
        
    ip = args[0]
    success = asyncio.run(layer7_engine.unblock_ip(ip))
    
    if success:
        update.message.reply_text(f"✅ Unblocked IP: {ip}")
    else:
        update.message.reply_text(f"❌ IP not found: {ip}")

def uptime_command(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    stats = uptime_monitor.get_stats()
    proxy_stats = proxy_manager.get_stats()
    
    msg = (
        f"⏱️ **Uptime & Status**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🟢 Status: Online\n"
        f"⏱️ Uptime: {stats['uptime_hours']:.1f} hours\n"
        f"💓 Heartbeats: {stats['ping_count']}\n"
        f"⚠️ Errors: {stats['error_count']}\n"
        f"🔄 Restarts: {stats['restart_count']}\n"
        f"💾 Memory: {stats['memory_usage_mb']:.0f} MB\n"
        f"📦 Proxies: {proxy_stats['total']}\n"
        f"✅ Alive: {proxy_stats['alive']}\n"
        f"🕒 Last Ping: {stats['last_ping'][:19]}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"🔗 Health: http://localhost:8080/health"
    )
    
    update.message.reply_text(msg, parse_mode="Markdown")

def handle_file(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    document = update.message.document
    if not document:
        return
        
    file_name = document.file_name or ""
    if not (file_name.endswith('.txt') or file_name.endswith('.proxy') or file_name.endswith('.list')):
        update.message.reply_text("⚠️ Please send a .txt, .proxy, or .list file")
        return
        
    update.message.reply_text(f"📤 Processing {file_name}...")
    
    try:
        file = context.bot.get_file(document.file_id)
        content = file.download_as_bytearray().decode('utf-8', errors='ignore')
        
        format_info = proxy_manager.detect_format(content)
        
        if format_info["format"] == "unknown":
            update.message.reply_text(
                f"⚠️ Could not detect proxy format\n"
                f"Sample: `{format_info.get('sample', 'N/A')}`",
                parse_mode="Markdown"
            )
            return
            
        loaded, duplicate, _ = asyncio.run(
            proxy_manager.load_from_text(content, source=f"file:{file_name}")
        )
        
        if loaded == 0:
            update.message.reply_text(
                f"⚠️ No valid proxies found\n"
                f"Format: {format_info['format']}\n"
                f"Lines: {format_info['count']}"
            )
            return
            
        msg = (
            f"✅ **Load Complete**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 File: {file_name}\n"
            f"📦 Loaded: {loaded} proxies\n"
            f"🔄 Duplicates: {duplicate}\n"
            f"🔍 Format: {format_info['format'].upper()}\n\n"
            f"Use /validate to check proxies"
        )
        
        update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"File error: {e}")
        update.message.reply_text(f"❌ Error: {str(e)}")

def handle_url(update: Update, context: CallbackContext):
    if not check_user_rate_limit(update):
        return
        
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return
        
    url = url_match.group(0)
    update.message.reply_text(f"📤 Loading from URL...")
    
    try:
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            update.message.reply_text(f"⚠️ Failed: {response.status_code}")
            return
            
        content = response.text
        loaded, duplicate, _ = asyncio.run(
            proxy_manager.load_from_text(content, source=f"url:{url}")
        )
        
        if loaded == 0:
            update.message.reply_text(f"⚠️ No valid proxies found")
            return
            
        update.message.reply_text(
            f"✅ Loaded {loaded} proxies from URL\n"
            f"Duplicates: {duplicate}\n\n"
            f"Use /validate to check them"
        )
        
    except Exception as e:
        update.message.reply_text(f"❌ Error: {str(e)}")

def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    if not check_rate_limit(user_id):
        query.edit_message_text(
            f"⏳ **Rate limit exceeded**\n"
            f"Maximum {RATE_LIMIT} commands per minute."
        )
        return
        
    action = query.data
    
    if action == "stats":
        stats(update, context)
    elif action == "validate":
        validate(update, context)
    elif action == "export":
        export(update, context)
    elif action == "clean":
        clean(update, context)
    elif action == "random":
        random_proxy(update, context)
    elif action == "l7_stats":
        l7_stats(update, context)
    elif action == "attacks":
        show_attacks(update, context)
    elif action == "blocked":
        show_blocked(update, context)
    elif action == "uptime":
        uptime_command(update, context)

# ============================================
# 🔧 FIX 15: Main
# ============================================
def main():
    if TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set TELEGRAM_BOT_TOKEN")
        sys.exit(1)
    
    # Start health check server
    health_server = start_health_server(port=HEALTH_PORT)
    
    # Initialize proxy manager
    asyncio.run(proxy_manager.initialize())
    
    # Create updater
    try:
        updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    except Exception as e:
        logger.error(f"❌ Failed to create updater: {e}")
        sys.exit(1)
    
    dp = updater.dispatcher
    
    # Command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("validate", validate))
    dp.add_handler(CommandHandler("export", export))
    dp.add_handler(CommandHandler("clean", clean))
    dp.add_handler(CommandHandler("random", random_proxy))
    dp.add_handler(CommandHandler("l7stats", l7_stats))
    dp.add_handler(CommandHandler("attacks", show_attacks))
    dp.add_handler(CommandHandler("blocked", show_blocked))
    dp.add_handler(CommandHandler("unblock", unblock_ip))
    dp.add_handler(CommandHandler("uptime", uptime_command))
    
    # Message handlers
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
    
    # Callback handler
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("=" * 50)
    logger.info("🚀 Nexus Proxy Manager Bot Started")
    logger.info("=" * 50)
    logger.info(f"📦 Proxies: {len(proxy_manager.proxies)}")
    logger.info(f"👥 Mode: PUBLIC (everyone can use)")
    logger.info(f"⏳ Rate Limit: {RATE_LIMIT} commands/minute")
    logger.info(f"🐍 Python: {sys.version}")
    logger.info(f"🌐 Health: http://localhost:{HEALTH_PORT}/health")
    logger.info("=" * 50)
    
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
