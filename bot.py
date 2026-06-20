"""
Nexus Proxy Manager Bot — Full Fix
- Không cần Pillow
- Mock imghdr cho Python 3.14+
- In-Memory storage (không cần Redis)
- Auto-detect proxy format
- python-telegram-bot 13.7 compatible
- Chạy trên Render với Python 3.11+
"""

import os
import sys
import asyncio
import logging
import json
import re
import time
import hashlib
import types
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Set, Tuple
from collections import defaultdict, deque
from dataclasses import dataclass, field
from urllib.parse import urlparse

# ============================================
# 🔧 FIX 1: Mock imghdr cho Python 3.14+
# ============================================

def _create_imghdr_mock():
    """Tạo mock imghdr khi bị xóa trong Python 3.14+"""
    mock = types.ModuleType("imghdr")
    
    def what(file, h=None):
        """Mock imghdr.what() - detect image type from file"""
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

# Kiểm tra và mock nếu cần
try:
    import imghdr
    if not hasattr(imghdr, 'what'):
        raise ImportError("imghdr.what not found")
except (ImportError, AttributeError):
    imghdr = _create_imghdr_mock()
    sys.modules['imghdr'] = imghdr

# ============================================
# 🔧 FIX 2: Suppress warnings
# ============================================
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=FutureWarning)

# ============================================
# 🔧 FIX 3: Configuration
# ============================================

# Điền thông tin của bạn
TELEGRAM_BOT_TOKEN = "6320148381:AAFvtpr4l8t61IRgynsiUkwKVbCNMw9kdtU"  # <--- Điền token
ADMIN_USER_IDS = [5736655322]  # <--- Điền ID admin

# ============================================
# 🔧 FIX 4: Logging
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Log Python version để debug
logger.info(f"🐍 Python version: {sys.version}")

# ============================================
# 🔧 FIX 5: Imports
# ============================================
import filetype
import aiohttp
import requests
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
# 🔧 FIX 6: Data Models
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

# ============================================
# 🔧 FIX 7: In-Memory Storage (không cần Redis)
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
# 🔧 FIX 8: Proxy Manager
# ============================================
class ProxyManager:
    def __init__(self):
        self.storage = MemoryStorage()
        self.proxies: Dict[str, Proxy] = {}
        self._initialized = False
        self.validating = False
        
    async def initialize(self):
        if self._initialized:
            return
        self._initialized = True
        logger.info(f"ProxyManager initialized — {len(self.proxies)} proxies")
        
    def _parse_proxy_line(self, line: str) -> Optional[Proxy]:
        """Parse proxy line với auto-detect format"""
        line = line.strip()
        if not line or line.startswith('#'):
            return None
            
        patterns = [
            r'^(https?|socks[45]|http|socks4|socks5)://([^:]+):(\d+)$',
            r'^([^:]+):(\d+):(https?|socks[45])$',
            r'^([^:]+):(\d+)$',
            r'^([^:]+)\s+(\d+)$',
            r'^([^:]+):(\d+):([^:]+):(.+)$',
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
                elif len(groups) == 4:
                    ip, port, user, password = groups
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
        """Auto-detect proxy format"""
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
            
        main_format = max(set(formats), key=formats.count) if formats else "http"
        
        return {
            "format": main_format,
            "count": len(valid_lines),
            "sample": valid_lines[0] if valid_lines else None
        }
        
    async def load_from_text(self, content: str, source: str = "upload") -> Tuple[int, int, str]:
        """Load proxies từ text với auto-detect"""
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
                
        # Update stats
        alive = sum(1 for p in self.proxies.values() if p.is_alive)
        logger.info(f"Loaded {loaded} proxies from {source} (Total: {len(self.proxies)}, Alive: {alive})")
        return loaded, duplicate, "http"  # format main
        
    async def load_from_url(self, url: str) -> int:
        """Load proxies từ URL"""
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
                        return True
                        
        except Exception:
            pass
            
        proxy.is_alive = False
        proxy.fail_count += 1
        proxy.last_checked = datetime.now().isoformat()
        return False
        
    async def validate_all(self, max_concurrent: int = 20) -> Dict[str, Any]:
        """Validate all proxies"""
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

# ============================================
# 🔧 FIX 9: Bot Instance
# ============================================
proxy_manager = ProxyManager()

def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        update.message.reply_text("❌ Unauthorized")
        return False
    return True

def start(update: Update, context: CallbackContext):
    if not is_authorized(update):
        return
        
    stats = proxy_manager.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("✅ Validate", callback_data="validate")],
        [InlineKeyboardButton("📤 Export Alive", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean Dead", callback_data="clean")],
        [InlineKeyboardButton("🎲 Random Proxy", callback_data="random")],
    ]
    
    update.message.reply_text(
        f"🤖 **Nexus Proxy Manager Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: 🟢 Online\n"
        f"📦 Proxies: {stats['total']}\n"
        f"✅ Alive: {stats['alive']}\n"
        f"❌ Dead: {stats['dead']}\n"
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

def stats(update: Update, context: CallbackContext):
    if not is_authorized(update):
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
    if not is_authorized(update):
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

def clean(update: Update, context: CallbackContext):
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

def handle_file(update: Update, context: CallbackContext):
    if not is_authorized(update):
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
        
        # Auto-detect format
        format_info = proxy_manager.detect_format(content)
        
        if format_info["format"] == "unknown":
            update.message.reply_text(
                f"⚠️ Could not detect proxy format\n"
                f"Sample: `{format_info.get('sample', 'N/A')}`\n\n"
                f"Please ensure each line is: ip:port",
                parse_mode="Markdown"
            )
            return
            
        loaded, duplicate, main_format = asyncio.run(
            proxy_manager.load_from_text(content, source=f"file:{file_name}")
        )
        
        if loaded == 0:
            update.message.reply_text(
                f"⚠️ No valid proxies found in file\n"
                f"Detected format: {format_info['format']}\n"
                f"Total lines: {format_info['count']}"
            )
            return
            
        msg = (
            f"✅ **Load Complete**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📄 File: {file_name}\n"
            f"📦 Loaded: {loaded} proxies\n"
            f"🔄 Duplicates: {duplicate}\n"
            f"🔍 Format: {format_info['format'].upper()}\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 **Sample:**\n"
            f"`{format_info.get('sample', 'N/A')}`\n\n"
            f"Use /validate to check proxies"
        )
        
        update.message.reply_text(msg, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"File upload error: {e}")
        update.message.reply_text(f"❌ Error: {str(e)}")

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
        response = requests.get(url, timeout=15)
        if response.status_code != 200:
            update.message.reply_text(f"⚠️ Failed: {response.status_code}")
            return
            
        content = response.text
        format_info = proxy_manager.detect_format(content)
        
        if format_info["format"] == "unknown":
            update.message.reply_text(f"⚠️ Could not detect format from URL")
            return
            
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
    if user_id not in ADMIN_USER_IDS:
        query.edit_message_text("❌ Unauthorized")
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

# ============================================
# 🔧 FIX 10: Main
# ============================================
def main():
    # Kiểm tra token
    if TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set TELEGRAM_BOT_TOKEN")
        logger.error("Edit bot.py and change: TELEGRAM_BOT_TOKEN = 'your_token'")
        sys.exit(1)
        
    if not ADMIN_USER_IDS or ADMIN_USER_IDS == [123456789]:
        logger.warning("⚠️ Please set ADMIN_USER_IDS")
        logger.warning("Edit bot.py and change: ADMIN_USER_IDS = [your_id]")
        
    # Initialize
    asyncio.run(proxy_manager.initialize())
    
    # Create updater
    try:
        updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    except Exception as e:
        logger.error(f"❌ Failed to create updater: {e}")
        logger.error("Check your TELEGRAM_BOT_TOKEN")
        sys.exit(1)
        
    dp = updater.dispatcher
    
    # Add command handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stats", stats))
    dp.add_handler(CommandHandler("validate", validate))
    dp.add_handler(CommandHandler("export", export))
    dp.add_handler(CommandHandler("clean", clean))
    dp.add_handler(CommandHandler("random", random_proxy))
    
    # Add message handlers
    dp.add_handler(MessageHandler(Filters.document, handle_file))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_url))
    
    # Add callback handler
    dp.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("=" * 50)
    logger.info("🚀 Nexus Proxy Manager Bot Started")
    logger.info("=" * 50)
    logger.info(f"📦 Proxies loaded: {len(proxy_manager.proxies)}")
    logger.info(f"👥 Admin users: {ADMIN_USER_IDS}")
    logger.info(f"🐍 Python version: {sys.version}")
    logger.info(f"✅ imghdr available: {hasattr(imghdr, 'what')}")
    logger.info("=" * 50)
    logger.info("📋 Commands:")
    logger.info("  /start - Show menu")
    logger.info("  /stats - Proxy statistics")
    logger.info("  /validate - Validate proxies")
    logger.info("  /export - Export alive proxies")
    logger.info("  /clean - Remove dead proxies")
    logger.info("  /random - Get random proxy")
    logger.info("=" * 50)
    logger.info("📤 Upload .txt file to load proxies")
    logger.info("=" * 50)
    
    # Start polling
    try:
        updater.start_polling()
        updater.idle()
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        sys.exit(1)
