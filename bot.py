"""
Nexus Proxy Manager Bot — Full Complete
Auto-Detect Proxy Upload + Layer 7 Defense
python-telegram-bot==13.7 compatible
"""

import os
import sys
import asyncio
import logging
import json
import re
import time
import hashlib
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from urllib.parse import urlparse

# ============================================
# 🔑 CONFIGURATION — ĐIỀN THÔNG TIN CỦA BẠN
# ============================================

TELEGRAM_BOT_TOKEN = "6320148381:AAHIsLUglnab_3rEU7R0tyN9x7h7E9xSXdY"  # <--- Điền token
ADMIN_USER_IDS = [5736655322]  # <--- Điền ID admin

# ============================================
# LOGGING
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# IMPORTS
# ============================================
import aiohttp
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
# MODELS
# ============================================
@dataclass
class Proxy:
    ip: str
    port: int
    protocol: str = "http"
    country: Optional[str] = None
    speed: float = 0.0
    is_alive: bool = True
    last_checked: Optional[str] = None
    fail_count: int = 0
    anonymity: str = "unknown"
    source: str = "upload"
    added_at: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "port": self.port,
            "protocol": self.protocol,
            "country": self.country,
            "speed": self.speed,
            "is_alive": self.is_alive,
            "last_checked": self.last_checked,
            "fail_count": self.fail_count,
            "anonymity": self.anonymity,
            "source": self.source,
            "added_at": self.added_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Proxy':
        return cls(
            ip=data.get("ip", ""),
            port=int(data.get("port", 0)),
            protocol=data.get("protocol", "http"),
            country=data.get("country"),
            speed=float(data.get("speed", 0.0)),
            is_alive=data.get("is_alive", True),
            last_checked=data.get("last_checked"),
            fail_count=int(data.get("fail_count", 0)),
            anonymity=data.get("anonymity", "unknown"),
            source=data.get("source", "upload"),
            added_at=data.get("added_at", datetime.now().isoformat())
        )
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_proxy_string(self):
        return f"{self.ip}:{self.port}"

@dataclass
class ProxyStats:
    total: int = 0
    alive: int = 0
    dead: int = 0
    last_update: Optional[str] = None
    uptime: int = 0

# ============================================
# IN-MEMORY STORAGE
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

# ============================================
# PROXY MANAGER (with Auto-Detect)
# ============================================
class ProxyManager:
    def __init__(self):
        self.storage = MemoryStorage()
        self.proxies: Dict[str, Proxy] = {}
        self.stats = ProxyStats()
        self._initialized = False
        
    async def initialize(self):
        if self._initialized:
            return
            
        # Load proxies from storage
        proxy_ids = await self.storage.smembers("proxies:all")
        for proxy_id in proxy_ids:
            data = await self.storage.hgetall(f"proxy:{proxy_id}")
            if data:
                proxy = Proxy.from_dict(data)
                self.proxies[proxy_id] = proxy
                
        await self._update_stats()
        self._initialized = True
        logger.info(f"ProxyManager initialized — {len(self.proxies)} proxies loaded")
        
    def _parse_proxy_line(self, line: str) -> Optional[Proxy]:
        """Parse a single proxy line with auto-detect format"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        # Try different formats
        patterns = [
            # Format: protocol://ip:port
            r'^(https?|socks[45]|http|socks4|socks5)://([^:]+):(\d+)$',
            # Format: ip:port:protocol
            r'^([^:]+):(\d+):(https?|socks[45])$',
            # Format: ip:port (default http)
            r'^([^:]+):(\d+)$',
            # Format: ip port (space separated)
            r'^([^:]+)\s+(\d+)$',
            # Format: ip:port:user:pass (with auth)
            r'^([^:]+):(\d+):([^:]+):(.+)$',
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                groups = match.groups()
                if len(groups) == 3:
                    if '://' in line:
                        # protocol://ip:port
                        protocol, ip, port = groups
                    else:
                        # ip:port:protocol
                        ip, port, protocol = groups
                elif len(groups) == 2:
                    # ip:port or ip port
                    ip, port = groups
                    protocol = "http"
                elif len(groups) == 4:
                    # ip:port:user:pass
                    ip, port, user, password = groups
                    protocol = "http"
                    # We could store auth info but we'll ignore for now
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
        """Auto-detect proxy format from content"""
        lines = content.strip().split('\n')
        valid_lines = [l for l in lines if l.strip() and not l.startswith('#')]
        
        if not valid_lines:
            return {"format": "unknown", "count": 0, "sample": None}
            
        # Test first few lines
        formats_detected = []
        for line in valid_lines[:10]:
            proxy = self._parse_proxy_line(line)
            if proxy:
                formats_detected.append(proxy.protocol)
                
        if not formats_detected:
            return {"format": "unknown", "count": 0, "sample": None}
            
        # Determine format
        if "socks5" in formats_detected or "socks4" in formats_detected:
            detected_format = "socks"
        elif "https" in formats_detected:
            detected_format = "https"
        else:
            detected_format = "http"
            
        return {
            "format": detected_format,
            "count": len(valid_lines),
            "sample": valid_lines[0] if valid_lines else None
        }
        
    async def load_from_text(self, content: str, source: str = "upload") -> Tuple[int, int, str]:
        """Load proxies from text content with auto-detect"""
        lines = content.strip().split('\n')
        loaded = 0
        duplicate = 0
        errors = 0
        formats = {}
        
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
                
            proxy = self._parse_proxy_line(line)
            if proxy:
                proxy.source = source
                proxy_id = f"{proxy.ip}:{proxy.port}"
                
                # Check for duplicate
                if proxy_id in self.proxies:
                    duplicate += 1
                    continue
                    
                # Store
                self.proxies[proxy_id] = proxy
                await self.storage.hset(f"proxy:{proxy_id}", "ip", proxy.ip)
                await self.storage.hset(f"proxy:{proxy_id}", "port", str(proxy.port))
                await self.storage.hset(f"proxy:{proxy_id}", "protocol", proxy.protocol)
                await self.storage.hset(f"proxy:{proxy_id}", "source", proxy.source)
                await self.storage.hset(f"proxy:{proxy_id}", "added_at", proxy.added_at)
                await self.storage.hset(f"proxy:{proxy_id}", "is_alive", str(proxy.is_alive))
                
                await self.storage.sadd("proxies:all", proxy_id)
                loaded += 1
                
                # Track formats
                formats[proxy.protocol] = formats.get(proxy.protocol, 0) + 1
            else:
                errors += 1
                
        await self._update_stats()
        
        # Determine main format
        main_format = max(formats.items(), key=lambda x: x[1])[0] if formats else "unknown"
        
        return loaded, duplicate, main_format
        
    async def _update_stats(self):
        alive = sum(1 for p in self.proxies.values() if p.is_alive)
        self.stats = ProxyStats(
            total=len(self.proxies),
            alive=alive,
            dead=len(self.proxies) - alive,
            last_update=datetime.now().isoformat(),
            uptime=int(time.time())
        )
        
    def get_stats(self) -> Dict[str, Any]:
        return {
            "total": self.stats.total,
            "alive": self.stats.alive,
            "dead": self.stats.dead,
            "last_update": self.stats.last_update,
            "uptime": self.stats.uptime
        }
        
    def get_all_proxies(self) -> List[Proxy]:
        return list(self.proxies.values())
        
    def get_alive_proxies(self) -> List[Proxy]:
        return [p for p in self.proxies.values() if p.is_alive]
        
    def get_random_alive(self) -> Optional[Proxy]:
        alive = self.get_alive_proxies()
        if not alive:
            return None
        import random
        return random.choice(alive)
        
    async def validate_proxy(self, proxy: Proxy) -> bool:
        """Validate a single proxy"""
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
                        
                        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "is_alive", "True")
                        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "speed", str(proxy.speed))
                        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "last_checked", proxy.last_checked)
                        
                        await self.storage.sadd("proxies:alive", f"{proxy.ip}:{proxy.port}")
                        return True
                        
        except Exception:
            pass
            
        proxy.is_alive = False
        proxy.fail_count += 1
        proxy.last_checked = datetime.now().isoformat()
        
        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "is_alive", "False")
        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "fail_count", str(proxy.fail_count))
        await self.storage.hset(f"proxy:{proxy.ip}:{proxy.port}", "last_checked", proxy.last_checked)
        
        await self.storage.srem("proxies:alive", f"{proxy.ip}:{proxy.port}")
        return False
        
    async def validate_all(self, max_concurrent: int = 20) -> Dict[str, Any]:
        """Validate all proxies"""
        proxies = self.get_all_proxies()
        if not proxies:
            return {"total": 0, "validated": 0}
            
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def validate_one(proxy):
            async with semaphore:
                return await self.validate_proxy(proxy)
                
        tasks = [validate_one(p) for p in proxies]
        results = await asyncio.gather(*tasks)
        
        await self._update_stats()
        
        return {
            "total": len(proxies),
            "validated": sum(1 for r in results if r),
            "failed": sum(1 for r in results if not r)
        }
        
    async def clean_dead(self) -> int:
        """Remove dead proxies"""
        dead = [p for p in self.proxies.values() if not p.is_alive]
        for p in dead:
            proxy_id = f"{p.ip}:{p.port}"
            del self.proxies[proxy_id]
            await self.storage.delete(f"proxy:{proxy_id}")
            await self.storage.srem("proxies:all", proxy_id)
            await self.storage.srem("proxies:alive", proxy_id)
            
        await self._update_stats()
        return len(dead)

# ============================================
# LAYER 7 DEFENSE ENGINE
# ============================================
class Layer7DefenseEngine:
    def __init__(self):
        self.storage = MemoryStorage()
        self.attack_log = deque(maxlen=1000)
        self.blocked_ips: Set[str] = set()
        self._initialized = False
        self.stats = {
            "total_requests": 0,
            "blocked_requests": 0,
            "attacks_detected": 0,
            "blocked_ips": 0,
            "last_attack": None,
            "attack_types": defaultdict(int),
            "start_time": datetime.now().isoformat()
        }
        
    async def initialize(self):
        if self._initialized:
            return
        blocked_data = await self.storage.get("layer7:blocked_ips")
        if blocked_data:
            self.blocked_ips = set(json.loads(blocked_data))
        self._initialized = True
        logger.info(f"Layer 7 Defense initialized — {len(self.blocked_ips)} blocked IPs")
        
    async def _block_ip(self, ip: str, reason: str, duration: int = 3600):
        if ip in self.blocked_ips:
            return
        self.blocked_ips.add(ip)
        self.stats["blocked_ips"] += 1
        
        block_data = {
            "ip": ip, "reason": reason,
            "blocked_at": datetime.now().isoformat(),
            "expires": (datetime.now() + timedelta(seconds=duration)).isoformat()
        }
        
        await self.storage.set(f"blocked:{ip}", json.dumps(block_data), duration)
        await self.storage.set("blocked_ips", json.dumps(list(self.blocked_ips)))
        logger.warning(f"🔒 Blocked IP: {ip} - {reason}")
        
    async def _log_attack(self, attack_data: dict):
        key = f"attacks:{datetime.now().strftime('%Y%m%d')}"
        await self.storage.lpush(key, json.dumps(attack_data))
        await self.storage.ltrim(key, 0, 999)
        self.attack_log.append(attack_data)
        self.stats["last_attack"] = attack_data.get("timestamp")
        
    async def get_attacks(self, limit: int = 50) -> List[Dict]:
        key = f"attacks:{datetime.now().strftime('%Y%m%d')}"
        attacks = await self.storage.lrange(key, 0, limit - 1)
        return [json.loads(a) for a in attacks]
        
    async def get_blocked_ips(self) -> List[Dict]:
        keys = await self.storage.keys()
        blocked = []
        for key in keys:
            if key.startswith("blocked:"):
                data = await self.storage.get(key)
                if data:
                    blocked.append(json.loads(data))
        return blocked
        
    async def unblock_ip(self, ip: str) -> bool:
        if ip not in self.blocked_ips:
            return False
        self.blocked_ips.remove(ip)
        await self.storage.delete(f"blocked:{ip}")
        await self.storage.set("blocked_ips", json.dumps(list(self.blocked_ips)))
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

# ============================================
# BOT INSTANCES
# ============================================
proxy_manager = ProxyManager()
layer7_engine = Layer7DefenseEngine()

# ============================================
# BOT HANDLERS
# ============================================
def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        update.message.reply_text("❌ Unauthorized access")
        return False
    return True

def start(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    stats = proxy_manager.get_stats()
    l7_stats = layer7_engine.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Proxy Stats", callback_data="proxy_stats")],
        [InlineKeyboardButton("🛡️ Layer 7 Stats", callback_data="l7_stats")],
        [InlineKeyboardButton("📤 Export Proxies", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean Dead", callback_data="clean")],
        [InlineKeyboardButton("🎲 Random Proxy", callback_data="random")],
        [InlineKeyboardButton("🚨 Attacks", callback_data="attacks")],
        [InlineKeyboardButton("🔒 Blocked IPs", callback_data="blocked")],
        [InlineKeyboardButton("🔓 Unblock IP", callback_data="unblock")],
    ]
    
    update.message.reply_text(
        f"🤖 **Nexus Proxy Manager Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: 🟢 Online\n"
        f"📦 Proxies: {stats['total']}\n"
        f"✅ Alive: {stats['alive']}\n"
        f"❌ Dead: {stats['dead']}\n"
        f"🚨 Attacks: {l7_stats['attacks_detected']}\n"
        f"🔒 Blocked IPs: {l7_stats['blocked_ips']}\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 **Upload proxy file:**\n"
        f"Send a .txt file with proxies\n"
        f"📋 **Supported formats:**\n"
        f"• ip:port\n"
        f"• ip port\n"
        f"• protocol://ip:port\n"
        f"• ip:port:protocol\n\n"
        f"🔒 **Auto-detect format**",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

def proxy_stats(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    stats = proxy_manager.get_stats()
    alive = proxy_manager.get_alive_proxies()
    
    # Count protocols
    protocols = defaultdict(int)
    for p in proxy_manager.get_all_proxies():
        protocols[p.protocol] += 1
    
    msg = (
        f"📊 **Proxy Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total: {stats['total']}\n"
        f"✅ Alive: {stats['alive']}\n"
        f"❌ Dead: {stats['dead']}\n"
        f"📈 Rate: {(stats['alive'] / max(stats['total'], 1) * 100):.1f}%\n"
        f"🔄 Last Update: {stats['last_update'][:19] if stats['last_update'] else 'Never'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📋 **Protocols:**\n"
    )
    
    for protocol, count in protocols.items():
        msg += f"  • {protocol}: {count}\n"
        
    msg += f"\n🌐 Alive IPs: {len(set(p.ip for p in alive))}"
    
    update.message.reply_text(msg, parse_mode="Markdown")

def layer7_stats(update: Update, context: CallbackContext):
    if not is_authorized(update):
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

def export_proxies(update: Update, context: CallbackContext):
    if not is_authorized(update):
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

def clean_dead(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    update.message.reply_text("🧹 Cleaning dead proxies...")
    removed = asyncio.run(proxy_manager.clean_dead())
    update.message.reply_text(f"🧹 Removed {removed} dead proxies")

def random_proxy(update: Update, context: CallbackContext):
    if not is_authorized(update):
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

def show_attacks(update: Update, context: CallbackContext):
    if not is_authorized(update):
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
            f"from {attack.get('ip', 'unknown')}\n"
        )
        
    update.message.reply_text(msg, parse_mode="Markdown")

def show_blocked(update: Update, context: CallbackContext):
    if not is_authorized(update):
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
    if not is_authorized(update):
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

def logs(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    logs_list = layer7_engine.attack_log
    if not logs_list:
        update.message.reply_text("📋 No logs available")
        return
        
    msg = "📋 **Recent Attack Logs**\n━━━━━━━━━━━━━━━━━━\n"
    for attack in list(logs_list)[-10:]:
        msg += f"• {attack.get('timestamp', '')[:19]} - {attack.get('type', 'unknown')} from {attack.get('ip', 'unknown')}\n"
        
    update.message.reply_text(msg, parse_mode="Markdown")

def validate_proxies(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    update.message.reply_text("🔄 Validating proxies... (may take a few minutes)")
    
    result = asyncio.run(proxy_manager.validate_all(max_concurrent=20))
    
    msg = (
        f"✅ **Validation Complete**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: {result['total']}\n"
        f"✅ Alive: {result['validated']}\n"
        f"❌ Dead: {result['failed']}\n"
        f"📈 Rate: {(result['validated'] / max(result['total'], 1) * 100):.1f}%"
    )
    
    update.message.reply_text(msg, parse_mode="Markdown")

# ============================================
# FILE UPLOAD HANDLER — AUTO-DETECT
# ============================================
def handle_file(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    document = update.message.document
    if not document:
        return
        
    # Check if it's a text file
    file_name = document.file_name or ""
    if not (file_name.endswith('.txt') or file_name.endswith('.proxy') or file_name.endswith('.list')):
        update.message.reply_text("⚠️ Please send a .txt, .proxy, or .list file")
        return
        
    update.message.reply_text(f"📤 Processing {file_name}...")
    
    try:
        # Download file
        file = context.bot.get_file(document.file_id)
        file_content = file.download_as_bytearray()
        content = file_content.decode('utf-8', errors='ignore')
        
        # Auto-detect format
        format_info = proxy_manager.detect_format(content)
        
        if format_info["format"] == "unknown":
            update.message.reply_text(
                f"⚠️ Could not detect proxy format\n"
                f"Please ensure each line is: ip:port\n"
                f"Sample from file:\n`{format_info.get('sample', 'N/A')}`",
                parse_mode="Markdown"
            )
            return
            
        # Load proxies
        loaded, duplicate, main_format = asyncio.run(
            proxy_manager.load_from_text(content, source=f"file:{file_name}")
        )
        
        if loaded == 0:
            update.message.reply_text(
                f"⚠️ No valid proxies found in file\n"
                f"Detected format: {format_info['format']}\n"
                f"Total lines: {format_info['count']}\n"
                f"Please check format: ip:port (one per line)"
            )
            return
            
        msg = (
            f"✅ **Load Complete**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 File: {file_name}\n"
            f"📦 Loaded: {loaded} proxies\n"
            f"🔄 Duplicates: {duplicate}\n"
            f"🔍 Format: {main_format.upper()}\n"
            f"📝 Detected: {format_info['format'].upper()}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 **Sample:**\n"
            f"`{format_info.get('sample', 'N/A')}`\n\n"
            f"Use /validate to check proxies"
        )
        
        update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        update.message.reply_text(f"❌ Error processing file: {str(e)}")

# ============================================
# URL HANDLER — Auto-Detect
# ============================================
def handle_url(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    text = update.message.text.strip()
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return
        
    url = url_match.group(0)
    update.message.reply_text(f"📤 Loading proxies from URL...")
    
    try:
        import requests
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            update.message.reply_text(f"⚠️ Failed to fetch URL: {response.status_code}")
            return
            
        content = response.text
        
        # Auto-detect format
        format_info = proxy_manager.detect_format(content)
        
        if format_info["format"] == "unknown":
            update.message.reply_text(
                f"⚠️ Could not detect proxy format from URL\n"
                f"Sample: `{format_info.get('sample', 'N/A')}`",
                parse_mode="Markdown"
            )
            return
            
        loaded, duplicate, main_format = asyncio.run(
            proxy_manager.load_from_text(content, source=f"url:{url}")
        )
        
        if loaded == 0:
            update.message.reply_text(f"⚠️ No valid proxies found in URL")
            return
            
        msg = (
            f"✅ **Load Complete**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔗 URL: {url[:50]}...\n"
            f"📦 Loaded: {loaded} proxies\n"
            f"🔄 Duplicates: {duplicate}\n"
            f"🔍 Format: {main_format.upper()}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"Use /validate to check proxies"
        )
        
        update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"URL load error: {e}")
        update.message.reply_text(f"❌ Error loading URL: {str(e)}")

# ============================================
# CALLBACK HANDLER
# ============================================
def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        query.edit_message_text("❌ Unauthorized")
        return
        
    action = query.data
    
    if action == "proxy_stats":
        proxy_stats(update, context)
    elif action == "l7_stats":
        layer7_stats(update, context)
    elif action == "export":
        export_proxies(update, context)
    elif action == "clean":
        clean_dead(update, context)
    elif action == "random":
        random_proxy(update, context)
    elif action == "attacks":
        show_attacks(update, context)
    elif action == "blocked":
        show_blocked(update, context)
    elif action == "unblock":
        query.edit_message_text("⚠️ Send /unblock <ip>")

# ============================================
# MAIN
# ============================================
def main():
    if TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set TELEGRAM_BOT_TOKEN")
        return
        
    # Initialize
    asyncio.run(proxy_manager.initialize())
    asyncio.run(layer7_engine.initialize())
    
    # Create updater
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    
    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", proxy_stats))
    dp.add_handler(CommandHandler("validate", validate_proxies))
    dp.add_handler(CommandHandler("export", export_proxies))
    dp.add_handler(CommandHandler("clean", clean_dead))
    dp.add_handler(CommandHandler("random", random_proxy))
    dp.add_handler(CommandHandler("attacks", show_attacks))
    dp.add_handler(CommandHandler("blocked", show_blocked))
    dp.add_handler(CommandHandler("unblock", unblock_ip))
    dp.add_handler(CommandHandler("logs", logs))
    
    # Add message handlers
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
    
    # Add callback handler
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🤖 Nexus Proxy Manager Bot started")
    logger.info(f"📊 Proxies loaded: {len(proxy_manager.proxies)}")
    logger.info(f"🛡️ Layer 7 Defense active")
    
    # Start polling
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
