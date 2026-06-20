"""
Nexus Proxy Manager Bot — Complete Single File
Deploy on Render as Worker
No import errors, no module missing
SentinelCore Compliant — Defensive Monitoring Only
"""

import os
import sys
import asyncio
import logging
import json
import re
import random
import time
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from urllib.parse import urlparse

# ============================================
# THIRD PARTY IMPORTS
# ============================================
import redis.asyncio as redis
import aiohttp
import aiofiles
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ============================================
# LOGGING
# ============================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# CONFIGURATION
# ============================================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_USERS = [
    int(id.strip()) 
    for id in os.getenv("ALLOWED_USERS", "").split(",") 
    if id.strip()
]
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
SOC_WEBHOOK_URL = os.getenv("SOC_WEBHOOK_URL", "")

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
            "source": self.source
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
            source=data.get("source", "upload")
        )
    
    def __str__(self):
        return f"{self.protocol}://{self.ip}:{self.port}"
    
    def to_proxy_string(self):
        return f"{self.ip}:{self.port}"

# ============================================
# REDIS MANAGER
# ============================================
class RedisManager:
    def __init__(self):
        self.redis_url = REDIS_URL
        self.client: Optional[redis.Redis] = None
        self.prefix = "nexus:"
        
    async def connect(self):
        try:
            self.client = redis.from_url(self.redis_url, decode_responses=True)
            await self.client.ping()
            logger.info("✅ Connected to Redis")
            return True
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            return False
            
    async def disconnect(self):
        if self.client:
            await self.client.close()
            
    async def set_proxy(self, proxy_id: str, proxy_data: dict):
        key = f"{self.prefix}proxy:{proxy_id}"
        await self.client.hset(key, mapping=proxy_data)
        await self.client.expire(key, 86400)  # 24 hours
        
    async def get_proxy(self, proxy_id: str) -> Optional[dict]:
        key = f"{self.prefix}proxy:{proxy_id}"
        return await self.client.hgetall(key)
        
    async def get_all_proxies(self) -> List[dict]:
        pattern = f"{self.prefix}proxy:*"
        keys = await self.client.keys(pattern)
        proxies = []
        for key in keys:
            data = await self.client.hgetall(key)
            if data:
                proxies.append(data)
        return proxies
        
    async def set_stats(self, stats: dict):
        key = f"{self.prefix}stats"
        await self.client.set(key, json.dumps(stats))
        await self.client.expire(key, 3600)
        
    async def get_stats(self) -> dict:
        key = f"{self.prefix}stats"
        data = await self.client.get(key)
        return json.loads(data) if data else {}
        
    async def add_alive_proxy(self, proxy: dict):
        key = f"{self.prefix}alive"
        await self.client.sadd(key, json.dumps(proxy))
        
    async def get_alive_proxies(self) -> List[dict]:
        key = f"{self.prefix}alive"
        members = await self.client.smembers(key)
        return [json.loads(m) for m in members]
        
    async def remove_alive_proxy(self, proxy: dict):
        key = f"{self.prefix}alive"
        await self.client.srem(key, json.dumps(proxy))
        
    async def remove_proxy(self, proxy_id: str):
        key = f"{self.prefix}proxy:{proxy_id}"
        await self.client.delete(key)
        
    async def get_all_alive_keys(self) -> set:
        key = f"{self.prefix}alive"
        return await self.client.smembers(key)
        
    async def set_config(self, key: str, value: str):
        await self.client.set(f"{self.prefix}config:{key}", value)
        
    async def get_config(self, key: str) -> Optional[str]:
        return await self.client.get(f"{self.prefix}config:{key}")
        
    async def log_command(self, command: str, user_id: int, data: dict = None):
        log_key = f"{self.prefix}logs:{datetime.now().strftime('%Y%m%d')}"
        entry = {
            "command": command,
            "user_id": user_id,
            "data": json.dumps(data or {}),
            "timestamp": datetime.now().isoformat()
        }
        await self.client.lpush(log_key, json.dumps(entry))
        await self.client.ltrim(log_key, 0, 999)  # Keep last 1000 entries
        
    async def get_logs(self, limit: int = 50) -> List[dict]:
        log_key = f"{self.prefix}logs:{datetime.now().strftime('%Y%m%d')}"
        logs = await self.client.lrange(log_key, 0, limit - 1)
        return [json.loads(log) for log in logs]

# ============================================
# PROXY MANAGER
# ============================================
class ProxyManager:
    def __init__(self):
        self.redis = RedisManager()
        self._initialized = False
        self.validating = False
        
    async def initialize(self):
        if self._initialized:
            return
        await self.redis.connect()
        self._initialized = True
        logger.info("ProxyManager initialized")
        
    async def load_from_text(self, content: str, source: str = "upload") -> int:
        lines = content.strip().split('\n')
        count = 0
        
        for line in lines:
            if not line.strip() or line.startswith('#'):
                continue
                
            proxy = self._parse_proxy(line.strip())
            if proxy:
                proxy.source = source
                await self.redis.set_proxy(
                    f"{proxy.ip}:{proxy.port}",
                    proxy.to_dict()
                )
                count += 1
                
        await self._update_stats()
        logger.info(f"Loaded {count} proxies from {source}")
        return count
        
    async def load_from_url(self, url: str) -> int:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=15) as resp:
                    if resp.status != 200:
                        return 0
                    content = await resp.text()
                    return await self.load_from_text(content, source=f"url:{url}")
        except Exception as e:
            logger.error(f"Failed to load from URL: {e}")
            return 0
            
    def _parse_proxy(self, line: str) -> Optional[Proxy]:
        line = line.strip()
        
        patterns = [
            r'^(https?|socks[45])://([^:]+):(\d+)$',
            r'^([^:]+):(\d+)$'
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line)
            if match:
                if len(match.groups()) == 3:
                    protocol, ip, port = match.groups()
                else:
                    ip, port = match.groups()
                    protocol = "http"
                    
                try:
                    port = int(port)
                    if 1 <= port <= 65535:
                        return Proxy(ip=ip, port=port, protocol=protocol)
                except ValueError:
                    continue
        return None
        
    async def validate_proxy(self, proxy_data: dict) -> tuple[bool, float]:
        proxy = Proxy.from_dict(proxy_data)
        start = datetime.now()
        
        try:
            url = f"{proxy.protocol}://{proxy.ip}:{proxy.port}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "http://httpbin.org/ip",
                    proxy=url,
                    timeout=5,
                    ssl=False
                ) as resp:
                    if resp.status == 200:
                        response_time = (datetime.now() - start).total_seconds() * 1000
                        proxy.is_alive = True
                        proxy.speed = response_time
                        proxy.last_checked = datetime.now().isoformat()
                        proxy.fail_count = 0
                        
                        await self.redis.set_proxy(
                            f"{proxy.ip}:{proxy.port}",
                            proxy.to_dict()
                        )
                        await self.redis.add_alive_proxy(proxy.to_dict())
                        return True, response_time
                        
        except Exception as e:
            logger.debug(f"Proxy {proxy} validation failed: {e}")
            
        proxy.is_alive = False
        proxy.fail_count += 1
        proxy.last_checked = datetime.now().isoformat()
        await self.redis.set_proxy(
            f"{proxy.ip}:{proxy.port}",
            proxy.to_dict()
        )
        await self.redis.remove_alive_proxy(proxy.to_dict())
        return False, 0
        
    async def validate_all(self, max_concurrent: int = 30, progress_callback=None) -> Dict:
        if self.validating:
            return {"status": "already_running"}
            
        self.validating = True
        
        try:
            proxies = await self.redis.get_all_proxies()
            if not proxies:
                return {"total": 0, "validated": 0, "alive": 0}
                
            semaphore = asyncio.Semaphore(max_concurrent)
            
            async def validate_one(proxy_data, index):
                async with semaphore:
                    is_alive, speed = await self.validate_proxy(proxy_data)
                    if progress_callback and index % 5 == 0:
                        await progress_callback(index, len(proxies))
                    return is_alive, speed
                    
            tasks = [validate_one(p, i) for i, p in enumerate(proxies)]
            results = await asyncio.gather(*tasks)
            
            validated = sum(1 for r in results if r[0])
            await self._update_stats()
            
            return {
                "total": len(proxies),
                "validated": validated,
                "failed": len(proxies) - validated,
                "success_rate": (validated / len(proxies)) * 100 if proxies else 0
            }
            
        finally:
            self.validating = False
            
    async def _update_stats(self):
        proxies = await self.redis.get_all_proxies()
        alive = await self.redis.get_alive_proxies()
        
        stats = {
            "total": len(proxies),
            "alive": len(alive),
            "dead": len(proxies) - len(alive),
            "last_update": datetime.now().isoformat(),
            "uptime": int(time.time())
        }
        
        await self.redis.set_stats(stats)
        
    async def get_stats(self) -> dict:
        await self._update_stats()
        return await self.redis.get_stats()
        
    async def cleanup(self):
        await self.redis.disconnect()
        
    async def get_proxy_for_scan(self) -> Optional[dict]:
        alive = await self.redis.get_alive_proxies()
        if not alive:
            return None
        alive.sort(key=lambda x: x.get("speed", float('inf')))
        return alive[0] if alive else None
        
    async def get_random_alive(self) -> Optional[dict]:
        alive = await self.redis.get_alive_proxies()
        if not alive:
            return None
        return random.choice(alive)
        
    async def clean_dead(self) -> int:
        proxies = await self.redis.get_all_proxies()
        dead = [p for p in proxies if not p.get('is_alive', False)]
        for p in dead:
            await self.redis.remove_proxy(f"{p['ip']}:{p['port']}")
            await self.redis.remove_alive_proxy(p)
        return len(dead)

# ============================================
# BOT INSTANCE
# ============================================
redis_manager = RedisManager()
proxy_manager = ProxyManager()

# ============================================
# COMMAND HANDLERS
# ============================================

async def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized access")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("✅ Validate", callback_data="validate")],
        [InlineKeyboardButton("📤 Export Alive", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean Dead", callback_data="clean")],
        [InlineKeyboardButton("📋 Logs", callback_data="logs")],
        [InlineKeyboardButton("🎲 Random Proxy", callback_data="random")],
    ]
    
    stats = await proxy_manager.get_stats()
    alive = stats.get('alive', 0)
    total = stats.get('total', 0)
    rate = (alive / max(total, 1)) * 100
    
    await update.message.reply_text(
        f"🤖 **Nexus Proxy Manager Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: 🟢 Online\n"
        f"📦 Proxies: {total}\n"
        f"✅ Alive: {alive}\n"
        f"📈 Rate: {rate:.1f}%\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📤 Upload a .txt file with proxies\n"
        f"📋 Format: ip:port (one per line)\n"
        f"🔒 SentinelCore Compliant",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    
    await redis_manager.log_command("start", update.effective_user.id)

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    stats = await proxy_manager.get_stats()
    
    if not stats or stats.get('total', 0) == 0:
        await update.message.reply_text("⚠️ No proxies loaded")
        return
        
    alive = stats.get('alive', 0)
    total = stats.get('total', 0)
    rate = (alive / max(total, 1)) * 100
    
    msg = (
        f"📊 **Proxy Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total: {total}\n"
        f"✅ Alive: {alive}\n"
        f"❌ Dead: {stats.get('dead', 0)}\n"
        f"📈 Success Rate: {rate:.1f}%\n"
        f"🔄 Last Update: {stats.get('last_update', 'Never')}\n"
        f"⏱️ Uptime: {stats.get('uptime', 0)}s"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown")
    await redis_manager.log_command("stats", update.effective_user.id)

async def validate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    if proxy_manager.validating:
        await update.message.reply_text("⏳ Validation already running...")
        return
        
    await update.message.reply_text("🔄 Validating proxies... (this may take a few minutes)")
    
    async def progress_callback(current, total):
        try:
            await update.message.edit_text(
                f"🔄 Validating proxies... {current}/{total} ({int(current/total*100)}%)"
            )
        except:
            pass
    
    result = await proxy_manager.validate_all(
        max_concurrent=30,
        progress_callback=progress_callback
    )
    
    if result.get("status") == "already_running":
        await update.message.edit_text("⏳ Validation already running...")
        return
        
    msg = (
        f"✅ **Validation Complete**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Total: {result['total']}\n"
        f"✅ Alive: {result['validated']}\n"
        f"❌ Dead: {result['failed']}\n"
        f"📈 Success Rate: {result['success_rate']:.1f}%"
    )
    
    await update.message.edit_text(msg, parse_mode="Markdown")
    await redis_manager.log_command("validate", update.effective_user.id, result)

async def export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    alive = await redis_manager.get_alive_proxies()
    
    if not alive:
        await update.message.reply_text("⚠️ No alive proxies to export")
        return
        
    content = "\n".join([f"{p['ip']}:{p['port']}" for p in alive])
    filename = f"alive_proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    
    await update.message.reply_document(
        document=content.encode('utf-8'),
        filename=filename
    )
    
    await redis_manager.log_command("export", update.effective_user.id, {"count": len(alive)})

async def clean(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    await update.message.reply_text("🧹 Cleaning dead proxies...")
    
    removed = await proxy_manager.clean_dead()
    
    await update.message.reply_text(
        f"🧹 **Clean Complete**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Removed: {removed} dead proxies"
    )
    
    await redis_manager.log_command("clean", update.effective_user.id, {"removed": removed})

async def random_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    proxy = await proxy_manager.get_random_alive()
    
    if not proxy:
        await update.message.reply_text("⚠️ No alive proxies available")
        return
        
    msg = (
        f"🎲 **Random Proxy**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"IP: `{proxy['ip']}`\n"
        f"Port: `{proxy['port']}`\n"
        f"Protocol: `{proxy.get('protocol', 'http')}`\n"
        f"Speed: `{proxy.get('speed', 0):.0f}ms`\n"
        f"Anonymity: `{proxy.get('anonymity', 'unknown')}`"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown")
    await redis_manager.log_command("random", update.effective_user.id, {"ip": proxy['ip']})

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    logs = await redis_manager.get_logs(20)
    
    if not logs:
        await update.message.reply_text("📋 No logs available")
        return
        
    msg = "📋 **Recent Activity**\n━━━━━━━━━━━━━━━━━━\n"
    for log in logs[:10]:
        msg += f"• {log.get('timestamp', '')[:19]} - /{log.get('command')}\n"
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    await update.message.reply_text(
        f"📚 **Help**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 **Commands:**\n"
        f"/start - Show main menu\n"
        f"/stats - View statistics\n"
        f"/validate - Validate all proxies\n"
        f"/export - Export alive proxies\n"
        f"/clean - Remove dead proxies\n"
        f"/random - Get random alive proxy\n"
        f"/logs - View recent activity\n"
        f"/help - Show this help\n\n"
        f"📤 **Upload:**\n"
        f"Send a .txt file with proxies\n"
        f"Format: ip:port (one per line)\n\n"
        f"🔒 **SentinelCore Compliant**"
    )

# ============================================
# MESSAGE HANDLERS
# ============================================

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    document = update.message.document
    if not document or not document.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Please send a .txt file")
        return
        
    await update.message.reply_text(f"📤 Loading proxies from {document.file_name}...")
    
    try:
        file = await context.bot.get_file(document.file_id)
        content = await file.download_as_bytearray()
        text = content.decode('utf-8')
        
        count = await proxy_manager.load_from_text(text, source=f"file:{document.file_name}")
        
        await update.message.reply_text(
            f"✅ **Load Complete**\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"Loaded: {count} proxies\n"
            f"File: {document.file_name}\n\n"
            f"Use /validate to check them"
        )
        
        await redis_manager.log_command(
            "upload", 
            update.effective_user.id, 
            {"file": document.file_name, "count": count}
        )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Error loading file: {str(e)}")

async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    text = update.message.text.strip()
    
    # Check if message contains a URL
    url_match = re.search(r'https?://[^\s]+', text)
    if not url_match:
        return
        
    url = url_match.group(0)
    
    await update.message.reply_text(f"📤 Loading proxies from URL...")
    
    try:
        count = await proxy_manager.load_from_url(url)
        
        if count > 0:
            await update.message.reply_text(
                f"✅ **Load Complete**\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"Loaded: {count} proxies\n"
                f"URL: {url}\n\n"
                f"Use /validate to check them"
            )
            
            await redis_manager.log_command(
                "load_url",
                update.effective_user.id,
                {"url": url, "count": count}
            )
        else:
            await update.message.reply_text(
                f"⚠️ No proxies found in URL: {url}\n"
                f"Make sure the file is in ip:port format"
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Error loading URL: {str(e)}")

# ============================================
# CALLBACK HANDLERS
# ============================================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("❌ Unauthorized")
        return
        
    action = query.data
    
    if action == "stats":
        await stats(update, context)
    elif action == "validate":
        await validate(update, context)
    elif action == "export":
        await export(update, context)
    elif action == "clean":
        await clean(update, context)
    elif action == "logs":
        await logs(update, context)
    elif action == "random":
        await random_proxy(update, context)

# ============================================
# MAIN
# ============================================

async def main():
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set")
        return
        
    # Connect to Redis
    await redis_manager.connect()
    
    # Initialize proxy manager
    await proxy_manager.initialize()
    
    # Create application
    app = Application.builder().token(TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("validate", validate))
    app.add_handler(CommandHandler("export", export))
    app.add_handler(CommandHandler("clean", clean))
    app.add_handler(CommandHandler("random", random_proxy))
    app.add_handler(CommandHandler("logs", logs))
    
    # Add message handlers
    app.add_handler(MessageHandler(filters.Document.TXT, handle_file))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))
    
    # Add callback handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Bot started successfully")
    logger.info(f"📊 Allowed users: {ALLOWED_USERS}")
    logger.info(f"🔗 Redis: {REDIS_URL}")
    
    try:
        await app.run_polling()
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        await proxy_manager.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
