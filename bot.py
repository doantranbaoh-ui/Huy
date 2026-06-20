"""
Nexus Proxy Manager Bot — Layer 7 Defense
WITHOUT REDIS — In-Memory Storage Mode
SentinelCore Compliant — Defensive Monitoring Only
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
from typing import Optional, List, Dict, Any, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from urllib.parse import urlparse, parse_qs

# ============================================
# 🔑 CONFIGURATION — ĐIỀN THÔNG TIN CỦA BẠN
# ============================================

TELEGRAM_BOT_TOKEN = "6320148381:AAHIsLUglnab_3rEU7R0tyN9x7h7E9xSXdY"  # <--- Điền token
ADMIN_USER_IDS = [5736655322]  # <--- Điền ID admin
SOC_WEBHOOK_URL = ""

# Layer 7 Defense Config
RATE_LIMIT_REQUESTS = 60  # requests per minute per IP
RATE_LIMIT_WINDOW = 60  # seconds
BURST_THRESHOLD = 30  # requests in 10 seconds
USER_AGENT_BLOCKLIST = [
    "python-requests",
    "curl",
    "wget",
    "nmap",
    "nikto",
    "sqlmap",
    "gobuster",
    "dirb",
]
PATH_ATTACK_PATTERNS = [
    r"\.\./",
    r"etc/passwd",
    r"proc/self/environ",
    r"wp-admin",
    r"wp-login",
    r"admin/",
    r"\.env",
    r"\.git/",
    r"\.sql",
    r"\.bak",
    r"config\.php",
    r"\.htaccess",
    r"\.htpasswd",
]
SQL_INJECTION_PATTERNS = [
    r"union\s+select",
    r"or\s+1=1",
    r"' or '1'='1",
    r'" or "1"="1',
    r";\s*drop\s+table",
    r";\s*delete\s+from",
    r"information_schema",
    r"@@version",
]
XSS_PATTERNS = [
    r"<script",
    r"javascript:",
    r"onerror=",
    r"onload=",
    r"alert\(",
    r"prompt\(",
    r"confirm\(",
]

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
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# ============================================
# IN-MEMORY STORAGE (Thay thế Redis)
# ============================================
class MemoryStorage:
    """In-memory storage — fallback khi không có Redis"""
    
    def __init__(self):
        self.data = {}
        self.expiry = {}
        self.lists = defaultdict(list)
        self.sets = defaultdict(set)
        
    async def set(self, key: str, value: str, ex: int = None):
        """Set value with optional expiry"""
        self.data[key] = value
        if ex:
            self.expiry[key] = time.time() + ex
            
    async def get(self, key: str) -> Optional[str]:
        """Get value"""
        if key in self.expiry and time.time() > self.expiry[key]:
            del self.data[key]
            del self.expiry[key]
            return None
        return self.data.get(key)
        
    async def delete(self, key: str):
        """Delete key"""
        if key in self.data:
            del self.data[key]
        if key in self.expiry:
            del self.expiry[key]
            
    async def keys(self, pattern: str = "*") -> List[str]:
        """Get all keys matching pattern"""
        return list(self.data.keys())
        
    async def lpush(self, key: str, value: str):
        """Push to list"""
        self.lists[key].insert(0, value)
        
    async def ltrim(self, key: str, start: int, end: int):
        """Trim list"""
        self.lists[key] = self.lists[key][start:end]
        
    async def lrange(self, key: str, start: int, end: int) -> List[str]:
        """Get range from list"""
        return self.lists.get(key, [])[start:end]
        
    async def sadd(self, key: str, value: str):
        """Add to set"""
        self.sets[key].add(value)
        
    async def srem(self, key: str, value: str):
        """Remove from set"""
        if key in self.sets:
            self.sets[key].discard(value)
            
    async def smembers(self, key: str) -> Set[str]:
        """Get all members of set"""
        return self.sets.get(key, set())
        
    async def hset(self, key: str, mapping: dict):
        """Set hash fields"""
        if key not in self.data:
            self.data[key] = {}
        self.data[key].update(mapping)
        
    async def hgetall(self, key: str) -> dict:
        """Get all hash fields"""
        return self.data.get(key, {})
        
    async def ping(self) -> bool:
        """Check if storage is available"""
        return True
        
    async def close(self):
        """Close storage"""
        pass

# ============================================
# DATA MODELS
# ============================================
@dataclass
class Layer7Attack:
    ip: str
    attack_type: str
    path: str
    method: str
    user_agent: str
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    severity: str = "medium"

@dataclass
class RateLimitEntry:
    ip: str
    requests: int = 0
    first_seen: float = 0
    blocked: bool = False
    blocked_until: float = 0

# ============================================
# LAYER 7 DEFENSE ENGINE (No Redis)
# ============================================
class Layer7DefenseEngine:
    def __init__(self):
        self.storage = MemoryStorage()
        self.rate_limits = defaultdict(lambda: RateLimitEntry(""))
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
            
        # Load blocked IPs from storage
        blocked_data = await self.storage.get("layer7:blocked_ips")
        if blocked_data:
            self.blocked_ips = set(json.loads(blocked_data))
            
        self._initialized = True
        logger.info(f"Layer 7 Defense initialized (In-Memory Mode) — {len(self.blocked_ips)} blocked IPs")
        
    async def analyze_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze incoming HTTP request for Layer 7 attacks"""
        self.stats["total_requests"] += 1
        
        result = {
            "blocked": False,
            "attack_detected": False,
            "attack_type": None,
            "severity": "low",
            "reason": None
        }
        
        ip = request_data.get("ip", "")
        path = request_data.get("path", "/")
        method = request_data.get("method", "GET")
        user_agent = request_data.get("user_agent", "")
        query = request_data.get("query", "")
        body = request_data.get("body", "")
        headers = request_data.get("headers", {})
        
        # 1. Check if IP is blocked
        if ip in self.blocked_ips:
            result["blocked"] = True
            result["reason"] = "IP blocked"
            self.stats["blocked_requests"] += 1
            return result
            
        # 2. Rate limiting check
        rate_check = await self._check_rate_limit(ip)
        if rate_check["blocked"]:
            result["blocked"] = True
            result["reason"] = rate_check["reason"]
            self.stats["blocked_requests"] += 1
            self.stats["attacks_detected"] += 1
            self.stats["attack_types"]["rate_limit"] += 1
            return result
            
        # 3. Check for User-Agent attacks
        ua_check = self._check_user_agent(user_agent)
        if ua_check["attack"]:
            result["attack_detected"] = True
            result["attack_type"] = "bad_user_agent"
            result["severity"] = ua_check["severity"]
            self.stats["attacks_detected"] += 1
            self.stats["attack_types"]["bad_user_agent"] += 1
            
            await self._log_attack(Layer7Attack(
                ip=ip,
                attack_type="bad_user_agent",
                path=path,
                method=method,
                user_agent=user_agent,
                timestamp=datetime.now().isoformat(),
                details={"user_agent": user_agent},
                severity=ua_check["severity"]
            ))
            
            if ua_check["severity"] == "high":
                await self._block_ip(ip, "Bad User-Agent", 3600)
                result["blocked"] = True
                result["reason"] = "Blocked for bad user agent"
                self.stats["blocked_requests"] += 1
                
            return result
            
        # 4. Check for path traversal
        path_check = self._check_path_attacks(path, query)
        if path_check["attack"]:
            result["attack_detected"] = True
            result["attack_type"] = path_check["type"]
            result["severity"] = path_check["severity"]
            self.stats["attacks_detected"] += 1
            self.stats["attack_types"][path_check["type"]] += 1
            
            await self._log_attack(Layer7Attack(
                ip=ip,
                attack_type=path_check["type"],
                path=path,
                method=method,
                user_agent=user_agent,
                timestamp=datetime.now().isoformat(),
                details={"path": path, "query": query},
                severity=path_check["severity"]
            ))
            
            if path_check["severity"] in ["high", "critical"]:
                await self._block_ip(ip, f"Path attack: {path_check['type']}", 86400)
                result["blocked"] = True
                result["reason"] = f"Blocked for path attack: {path_check['type']}"
                self.stats["blocked_requests"] += 1
                
            return result
            
        # 5. Check for SQL Injection
        if query or body:
            sqli_check = self._check_sql_injection(query, body)
            if sqli_check["attack"]:
                result["attack_detected"] = True
                result["attack_type"] = "sql_injection"
                result["severity"] = "critical"
                self.stats["attacks_detected"] += 1
                self.stats["attack_types"]["sql_injection"] += 1
                
                await self._log_attack(Layer7Attack(
                    ip=ip,
                    attack_type="sql_injection",
                    path=path,
                    method=method,
                    user_agent=user_agent,
                    timestamp=datetime.now().isoformat(),
                    details={"query": query, "body": body[:200]},
                    severity="critical"
                ))
                
                await self._block_ip(ip, "SQL Injection detected", 86400)
                result["blocked"] = True
                result["reason"] = "Blocked for SQL injection"
                self.stats["blocked_requests"] += 1
                
                return result
                
        # 6. Check for XSS
        if query or body:
            xss_check = self._check_xss(query, body)
            if xss_check["attack"]:
                result["attack_detected"] = True
                result["attack_type"] = "xss"
                result["severity"] = "high"
                self.stats["attacks_detected"] += 1
                self.stats["attack_types"]["xss"] += 1
                
                await self._log_attack(Layer7Attack(
                    ip=ip,
                    attack_type="xss",
                    path=path,
                    method=method,
                    user_agent=user_agent,
                    timestamp=datetime.now().isoformat(),
                    details={"query": query, "body": body[:200]},
                    severity="high"
                ))
                
                await self._block_ip(ip, "XSS detected", 3600)
                result["blocked"] = True
                result["reason"] = "Blocked for XSS attempt"
                self.stats["blocked_requests"] += 1
                
                return result
                
        # 7. Check for HTTP method attacks
        method_check = self._check_method_attack(method, path)
        if method_check["attack"]:
            result["attack_detected"] = True
            result["attack_type"] = "bad_method"
            result["severity"] = "medium"
            self.stats["attacks_detected"] += 1
            self.stats["attack_types"]["bad_method"] += 1
            
            await self._log_attack(Layer7Attack(
                ip=ip,
                attack_type="bad_method",
                path=path,
                method=method,
                user_agent=user_agent,
                timestamp=datetime.now().isoformat(),
                details={"method": method},
                severity="medium"
            ))
            
            return result
            
        return result
        
    async def _check_rate_limit(self, ip: str) -> Dict[str, Any]:
        """Check rate limit (in-memory)"""
        key = f"rate:{ip}"
        now = time.time()
        
        # Get current count
        data = await self.storage.get(key)
        if data:
            count, first_seen = data.split(":")
            count = int(count)
            first_seen = float(first_seen)
        else:
            count = 0
            first_seen = now
            
        # Check window
        if now - first_seen > RATE_LIMIT_WINDOW:
            count = 0
            first_seen = now
            
        count += 1
        await self.storage.set(key, f"{count}:{first_seen}", RATE_LIMIT_WINDOW)
        
        # Check limit
        if count > RATE_LIMIT_REQUESTS:
            await self._block_ip(ip, f"Rate limit ({count} requests)", 300)
            return {"blocked": True, "reason": f"Rate limit ({count} requests)"}
            
        # Check burst
        burst_key = f"burst:{ip}"
        burst_count = await self.storage.get(burst_key)
        if burst_count:
            burst_count = int(burst_count)
            if burst_count > BURST_THRESHOLD:
                await self._block_ip(ip, f"Burst ({burst_count})", 600)
                return {"blocked": True, "reason": f"Burst ({burst_count})"}
            await self.storage.set(burst_key, str(burst_count + 1), 10)
        else:
            await self.storage.set(burst_key, "1", 10)
            
        return {"blocked": False}
        
    def _check_user_agent(self, user_agent: str) -> Dict[str, Any]:
        if not user_agent:
            return {"attack": True, "severity": "medium"}
            
        user_agent_lower = user_agent.lower()
        for pattern in USER_AGENT_BLOCKLIST:
            if pattern in user_agent_lower:
                return {"attack": True, "severity": "high"}
                
        if len(user_agent) < 5:
            return {"attack": True, "severity": "medium"}
            
        return {"attack": False}
        
    def _check_path_attacks(self, path: str, query: str) -> Dict[str, Any]:
        combined = f"{path}?{query}".lower()
        for pattern in PATH_ATTACK_PATTERNS:
            if re.search(pattern.lower(), combined):
                if "passwd" in pattern or "proc/" in pattern:
                    return {"attack": True, "type": "file_inclusion", "severity": "critical"}
                elif "wp-admin" in pattern or "wp-login" in pattern:
                    return {"attack": True, "type": "admin_bruteforce", "severity": "high"}
                elif ".env" in pattern or ".git" in pattern:
                    return {"attack": True, "type": "config_exposure", "severity": "high"}
                else:
                    return {"attack": True, "type": "path_traversal", "severity": "high"}
        return {"attack": False}
        
    def _check_sql_injection(self, query: str, body: str) -> Dict[str, Any]:
        combined = f"{query} {body}".lower()
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern.lower(), combined):
                return {"attack": True}
        return {"attack": False}
        
    def _check_xss(self, query: str, body: str) -> Dict[str, Any]:
        combined = f"{query} {body}".lower()
        for pattern in XSS_PATTERNS:
            if re.search(pattern.lower(), combined):
                return {"attack": True}
        return {"attack": False}
        
    def _check_method_attack(self, method: str, path: str) -> Dict[str, Any]:
        dangerous_methods = ["PUT", "DELETE", "OPTIONS", "TRACE", "CONNECT", "PATCH"]
        if method in dangerous_methods:
            return {"attack": True, "severity": "medium"}
        if method and len(method) > 10:
            return {"attack": True, "severity": "medium"}
        return {"attack": False}
        
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
        
        key = f"blocked:{ip}"
        await self.storage.set(key, json.dumps(block_data), duration)
        await self.storage.set("blocked_ips", json.dumps(list(self.blocked_ips)))
        
        logger.warning(f"🔒 Blocked IP: {ip} - {reason} ({duration}s)")
        
    async def _log_attack(self, attack: Layer7Attack):
        key = f"attacks:{datetime.now().strftime('%Y%m%d')}"
        await self.storage.lpush(key, json.dumps({
            "ip": attack.ip,
            "type": attack.attack_type,
            "path": attack.path,
            "method": attack.method,
            "user_agent": attack.user_agent,
            "timestamp": attack.timestamp,
            "severity": attack.severity
        }))
        await self.storage.ltrim(key, 0, 999)
        self.attack_log.append(attack)
        self.stats["last_attack"] = attack.timestamp
        logger.warning(f"🚨 Attack: {attack.attack_type} from {attack.ip} ({attack.severity})")
        
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
            "mode": "In-Memory (No Redis)"
        }

# ============================================
# BOT HANDLERS
# ============================================
layer7_engine = Layer7DefenseEngine()

async def is_authorized(update: Update) -> bool:
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await update.message.reply_text("❌ Unauthorized")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    stats = layer7_engine.get_stats()
    
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("🛡️ Layer 7 Stats", callback_data="l7_stats")],
        [InlineKeyboardButton("🚨 Attacks", callback_data="attacks")],
        [InlineKeyboardButton("🔒 Blocked IPs", callback_data="blocked")],
        [InlineKeyboardButton("🔓 Unblock IP", callback_data="unblock")],
        [InlineKeyboardButton("📋 Logs", callback_data="logs")],
    ]
    
    await update.message.reply_text(
        f"🛡️ **Nexus Layer 7 Defense Bot**\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n"
        f"📡 Status: 🟢 Online\n"
        f"🔄 Total Requests: {stats['total_requests']}\n"
        f"🚫 Blocked: {stats['blocked_requests']}\n"
        f"🚨 Attacks: {stats['attacks_detected']}\n"
        f"🔒 Blocked IPs: {stats['blocked_ips']}\n"
        f"💾 Mode: {stats.get('mode', 'In-Memory')}\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🛡️ **Layer 7 Protection Active**\n"
        f"• Rate Limiting: {RATE_LIMIT_REQUESTS}/min\n"
        f"• Burst Protection: {BURST_THRESHOLD}/10s\n"
        f"• SQL Injection Detection\n"
        f"• XSS Detection\n"
        f"• Path Traversal Detection\n"
        f"• Bad User-Agent Blocking",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def layer7_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    stats = layer7_engine.get_stats()
    
    msg = (
        f"🛡️ **Layer 7 Defense Statistics**\n"
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
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_attacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    attacks = await layer7_engine.get_attacks(20)
    
    if not attacks:
        await update.message.reply_text("✅ No attacks detected")
        return
        
    msg = "🚨 **Recent Attacks**\n━━━━━━━━━━━━━━━━━━\n"
    for attack in attacks[:10]:
        msg += (
            f"• {attack.get('timestamp', '')[:19]} - "
            f"{attack.get('type', 'unknown')} "
            f"from {attack.get('ip', 'unknown')} "
            f"({attack.get('severity', 'low')})\n"
        )
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def show_blocked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    blocked = await layer7_engine.get_blocked_ips()
    
    if not blocked:
        await update.message.reply_text("✅ No IPs blocked")
        return
        
    msg = "🔒 **Blocked IPs**\n━━━━━━━━━━━━━━━━━━\n"
    for entry in blocked[:10]:
        msg += (
            f"• {entry.get('ip')} - {entry.get('reason')}\n"
            f"  Expires: {entry.get('expires', '')[:19]}\n"
        )
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def unblock_ip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /unblock <ip>")
        return
        
    ip = args[0]
    success = await layer7_engine.unblock_ip(ip)
    
    if success:
        await update.message.reply_text(f"✅ Unblocked IP: {ip}")
    else:
        await update.message.reply_text(f"❌ IP not found: {ip}")

async def logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    logs = layer7_engine.attack_log
    if not logs:
        await update.message.reply_text("📋 No logs available")
        return
        
    msg = "📋 **Recent Attack Logs**\n━━━━━━━━━━━━━━━━━━\n"
    for attack in list(logs)[-10:]:
        msg += (
            f"• {attack.timestamp[:19]} - "
            f"{attack.attack_type} from {attack.ip}\n"
        )
        
    await update.message.reply_text(msg, parse_mode="Markdown")

async def test_attack(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update):
        return
        
    await update.message.reply_text("🧪 Logging test attack...")
    
    test_attack = Layer7Attack(
        ip="192.168.1.100",
        attack_type="sql_injection",
        path="/login.php?id=1' OR '1'='1",
        method="GET",
        user_agent="python-requests/2.28.1",
        timestamp=datetime.now().isoformat(),
        details={"query": "id=1' OR '1'='1"},
        severity="critical"
    )
    
    await layer7_engine._log_attack(test_attack)
    await update.message.reply_text("✅ Test attack logged")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id not in ADMIN_USER_IDS:
        await query.edit_message_text("❌ Unauthorized")
        return
        
    action = query.data
    
    if action == "stats":
        await start(update, context)
    elif action == "l7_stats":
        await layer7_stats(update, context)
    elif action == "attacks":
        await show_attacks(update, context)
    elif action == "blocked":
        await show_blocked(update, context)
    elif action == "unblock":
        await query.edit_message_text("⚠️ Send /unblock <ip>")
    elif action == "logs":
        await logs(update, context)

# ============================================
# MAIN
# ============================================
async def main():
    if TELEGRAM_BOT_TOKEN == "PASTE_YOUR_BOT_TOKEN_HERE":
        logger.error("❌ Please set TELEGRAM_BOT_TOKEN")
        return
        
    await layer7_engine.initialize()
    
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", layer7_stats))
    app.add_handler(CommandHandler("attacks", show_attacks))
    app.add_handler(CommandHandler("blocked", show_blocked))
    app.add_handler(CommandHandler("unblock", unblock_ip))
    app.add_handler(CommandHandler("logs", logs))
    app.add_handler(CommandHandler("test", test_attack))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🛡️ Layer 7 Defense Bot started (In-Memory Mode)")
    logger.info("📊 Bot running without Redis — data stored in memory")
    
    try:
        await app.run_polling()
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
