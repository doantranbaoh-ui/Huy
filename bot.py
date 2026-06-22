#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =====================================================================
# bot.py — FULL LICENSE SYSTEM — 2000+ DÒNG — RENDER READY
# Bao gồm: Telegram Bot + Flask API + Keygen + Quản lý thiết bị + Log
# =====================================================================

import os, sys, sqlite3, json, base64, datetime, hashlib, secrets, logging
import threading, time, uuid, string, random, ipaddress, hashlib, hmac
from functools import wraps
from collections import defaultdict
from typing import Optional, Dict, List, Tuple, Any

# Telegram Bot
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand,
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo, MenuButtonWebApp
)
from telegram.ext import (
    Application, ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler, ConversationHandler,
    CallbackContext
)
from telegram.constants import ParseMode, ChatAction

# Flask API Server
from flask import (
    Flask, request, jsonify, g, Response, make_response,
    redirect, url_for, send_file, abort
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.security import safe_str_cmp

# Cryptography
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa, ec
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, MultiFernet
from cryptography.x509 import load_pem_x509_certificate
from cryptography.exceptions import InvalidSignature

# =====================================================================
# CONSTANTS & CONFIGURATION
# =====================================================================

# --- Bot & Admin ---
BOT_TOKEN: str = "8515267798:AAEUWB-9qZFcW2ZcDwbaLg8Vi0CtrrUO4gE"
ADMIN_IDS: List[int] = [5736655322, 8782842024]
SUPER_ADMIN_ID: int = 5736655322  # Super admin có quyền cao nhất

# --- Server ---
API_PORT: int = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL: str = os.environ.get("RENDER_EXTERNAL_URL", "https://huy-93ob.onrender.com")
SERVER_URL: str = RENDER_EXTERNAL_URL
WEBHOOK_SECRET: str = os.environ.get("WEBHOOK_SECRET", secrets.token_hex(32))

# --- Paths ---
RENDER_DATA_DIR: str = "/opt/render/project/data"
if not os.path.exists(RENDER_DATA_DIR):
    os.makedirs(RENDER_DATA_DIR, exist_ok=True)

DB_PATH: str = os.path.join(RENDER_DATA_DIR, "license.db")
PRIV_PATH: str = os.path.join(RENDER_DATA_DIR, "private_key.pem")
PUB_PATH: str = os.path.join(RENDER_DATA_DIR, "public_key.pem")
FER_PATH: str = os.path.join(RENDER_DATA_DIR, "fernet.key")
BACKUP_DIR: str = os.path.join(RENDER_DATA_DIR, "backups")
LOG_PATH: str = os.path.join(RENDER_DATA_DIR, "server.log")

if not os.path.exists(BACKUP_DIR):
    os.makedirs(BACKUP_DIR, exist_ok=True)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)
log: logging.Logger = logging.getLogger("LICENSE_SYSTEM")

# --- Feature Flags ---
FEATURES: Dict[str, bool] = {
    "ENABLE_RATE_LIMITING": True,
    "ENABLE_AUTO_BACKUP": True,
    "ENABLE_IP_BLACKLIST": True,
    "ENABLE_API_LOGGING": True,
    "ENABLE_HEARTBEAT_MONITOR": True,
    "ENABLE_DEVICE_FINGERPRINT": True,
    "ENABLE_TELEGRAM_LOGGING": True,
    "ENABLE_MAINTENANCE_MODE": False,
}

# --- Rate Limiting ---
RATE_LIMIT_ACTIVATE: str = "3 per minute"
RATE_LIMIT_VERIFY: str = "10 per minute"
RATE_LIMIT_HEARTBEAT: str = "60 per minute"
RATE_LIMIT_CONFIG: str = "5 per minute"

# --- License Defaults ---
DEFAULT_EXPIRY_DAYS: int = 30
DEFAULT_DEVICE_LIMIT: int = 1
MAX_DEVICE_LIMIT: int = 100
MIN_PASSWORD_LENGTH: int = 8
MAX_LOGIN_ATTEMPTS: int = 5

# =====================================================================
# DATABASE MANAGER
# =====================================================================

class DatabaseManager:
    """Quản lý kết nối và thao tác database."""
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.db_path = DB_PATH
            self.initialized = True
    
    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor
    
    def executemany(self, query: str, params_list: List[tuple]) -> sqlite3.Cursor:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor
    
    def fetchone(self, query: str, params: tuple = ()) -> Optional[sqlite3.Row]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        row = cursor.fetchone()
        conn.close()
        return row
    
    def fetchall(self, query: str, params: tuple = ()) -> List[sqlite3.Row]:
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return rows
    
    def table_exists(self, table_name: str) -> bool:
        row = self.fetchone(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        return row is not None
    
    def count(self, table_name: str, where: str = "", params: tuple = ()) -> int:
        query = f"SELECT COUNT(*) as cnt FROM {table_name}"
        if where:
            query += f" WHERE {where}"
        row = self.fetchone(query, params)
        return row['cnt'] if row else 0
    
    def backup(self) -> str:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")
        import shutil
        shutil.copy2(self.db_path, backup_path)
        log.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def vacuum(self):
        self.execute("VACUUM")
        log.info("Database vacuumed")

db_manager = DatabaseManager()

def db() -> sqlite3.Connection:
    return db_manager.get_connection()

# =====================================================================
# DATABASE SCHEMA
# =====================================================================

def init_database():
    """Khởi tạo tất cả bảng trong database."""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # --- Bảng License Keys ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS license_keys(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_full TEXT NOT NULL,
            key_short TEXT NOT NULL,
            key_hash TEXT UNIQUE NOT NULL,
            product TEXT NOT NULL,
            type TEXT DEFAULT 'standard',
            expiry TEXT NOT NULL,
            duration_days INTEGER DEFAULT 0,
            duration_hours INTEGER DEFAULT 0,
            quantity INTEGER DEFAULT NULL,
            features TEXT DEFAULT '[]',
            prefix TEXT,
            key_id TEXT UNIQUE,
            is_active INTEGER DEFAULT 1,
            created_by INTEGER,
            created_by_username TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    
    # --- Bảng Activated Keys ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS activated_keys(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activation_id TEXT UNIQUE NOT NULL,
            key_hash TEXT NOT NULL,
            key_short TEXT NOT NULL,
            license_key_id INTEGER,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            device_udid TEXT,
            device_name TEXT,
            device_model TEXT,
            device_os TEXT,
            device_fingerprint TEXT,
            product TEXT,
            expiry TEXT,
            features TEXT DEFAULT '[]',
            source TEXT DEFAULT 'unknown',
            ip_address TEXT,
            country TEXT,
            city TEXT,
            is_active INTEGER DEFAULT 1,
            activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_heartbeat TIMESTAMP,
            FOREIGN KEY (license_key_id) REFERENCES license_keys(id)
        )
    ''')
    
    # --- Bảng Revoked Keys ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS revoked_keys(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key_short TEXT NOT NULL,
            key_hash TEXT UNIQUE,
            license_key_id INTEGER,
            reason TEXT,
            revoked_by INTEGER,
            revoked_by_username TEXT,
            revoked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (license_key_id) REFERENCES license_keys(id)
        )
    ''')
    
    # --- Bảng API Tokens ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_tokens(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            token_hash TEXT UNIQUE NOT NULL,
            token_prefix TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            token_name TEXT DEFAULT 'Default Token',
            permissions TEXT DEFAULT 'activate,verify,heartbeat,config',
            is_active INTEGER DEFAULT 1,
            device_limit INTEGER DEFAULT 5,
            request_limit INTEGER DEFAULT 1000,
            requests_used INTEGER DEFAULT 0,
            last_reset_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_used_at TIMESTAMP,
            expires_at TIMESTAMP,
            ip_whitelist TEXT DEFAULT '[]',
            notes TEXT
        )
    ''')
    
    # --- Bảng Devices ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registered_devices(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_udid TEXT NOT NULL,
            device_name TEXT DEFAULT 'Unknown',
            device_model TEXT DEFAULT 'Unknown',
            device_os TEXT DEFAULT 'Unknown',
            device_os_version TEXT DEFAULT 'Unknown',
            app_version TEXT DEFAULT '1.0',
            app_bundle_id TEXT,
            device_fingerprint TEXT,
            api_token_id INTEGER,
            user_id INTEGER,
            license_key_id INTEGER,
            activation_id TEXT,
            is_active INTEGER DEFAULT 1,
            is_trusted INTEGER DEFAULT 0,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            heartbeat_count INTEGER DEFAULT 0,
            ip_address TEXT,
            country TEXT,
            city TEXT,
            FOREIGN KEY (api_token_id) REFERENCES api_tokens(id),
            FOREIGN KEY (license_key_id) REFERENCES license_keys(id)
        )
    ''')
    
    # --- Bảng Heartbeats ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS heartbeats(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_udid TEXT NOT NULL,
            activation_id TEXT,
            license_key_id INTEGER,
            api_token_id INTEGER,
            ip_address TEXT,
            app_version TEXT,
            device_status TEXT DEFAULT 'active',
            battery_level INTEGER,
            network_type TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Bảng API Logs ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS api_logs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token_hash TEXT,
            token_prefix TEXT,
            endpoint TEXT NOT NULL,
            method TEXT NOT NULL,
            ip_address TEXT,
            user_agent TEXT,
            request_body TEXT,
            response_code INTEGER,
            response_time_ms REAL,
            error_message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Bảng IP Blacklist ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ip_blacklist(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ip_address TEXT NOT NULL,
            ip_range TEXT,
            reason TEXT DEFAULT 'Manual block',
            blocked_by INTEGER,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    # --- Bảng Users (Telegram) ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS telegram_users(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            language_code TEXT,
            is_admin INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0,
            total_activated INTEGER DEFAULT 0,
            first_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_interaction TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT
        )
    ''')
    
    # --- Bảng Audit Log ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Bảng Server Config ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_config(
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Bảng Rate Limit ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS rate_limits(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            identifier TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            request_count INTEGER DEFAULT 1,
            window_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Bảng Notifications ---
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notifications(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            title TEXT,
            message TEXT NOT NULL,
            type TEXT DEFAULT 'info',
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # --- Tạo Indexes ---
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activated_key_hash ON activated_keys(key_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activated_user_id ON activated_keys(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_activated_udid ON activated_keys(device_udid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_hash ON api_tokens(token_hash)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_tokens_user ON api_tokens(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_udid ON registered_devices(device_udid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_devices_token ON registered_devices(api_token_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_heartbeats_udid ON heartbeats(device_udid)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_heartbeats_time ON heartbeats(timestamp)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_endpoint ON api_logs(endpoint)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_logs_time ON api_logs(created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_blacklist_ip ON ip_blacklist(ip_address)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_user ON audit_log(user_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_log(action)')
    
    # --- Default Config ---
    cursor.execute('''
        INSERT OR IGNORE INTO server_config(key, value) VALUES 
        ('server_version', '4.0.0'),
        ('min_app_version', '1.0.0'),
        ('maintenance_mode', 'false'),
        ('max_devices_per_user', '10'),
        ('heartbeat_interval_seconds', '300'),
        ('session_timeout_seconds', '86400')
    ''')
    
    conn.commit()
    conn.close()
    log.info("Database initialized successfully with all tables and indexes")

# =====================================================================
# CRYPTOGRAPHY MANAGER
# =====================================================================

class CryptoManager:
    """Quản lý RSA keys, Fernet encryption, và signing."""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.private_key = None
            self.public_key = None
            self.fernet = None
            self.fernet_key = None
            self.prefix = None
            self.public_key_b64 = None
            self.public_key_fingerprint = None
            self._load_or_create_keys()
            self._load_or_create_fernet()
            self._generate_prefix()
            self.initialized = True
    
    def _load_or_create_keys(self):
        """Tải hoặc tạo cặp khóa RSA 2048-bit."""
        if not os.path.exists(PRIV_PATH) or not os.path.exists(PUB_PATH):
            log.info("Generating new RSA 2048-bit key pair...")
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )
            public_key = private_key.public_key()
            
            # Lưu private key
            with open(PRIV_PATH, "wb") as f:
                f.write(private_key.private_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PrivateFormat.PKCS8,
                    encryption_algorithm=serialization.NoEncryption()
                ))
            
            # Lưu public key
            with open(PUB_PATH, "wb") as f:
                f.write(public_key.public_bytes(
                    encoding=serialization.Encoding.PEM,
                    format=serialization.PublicFormat.SubjectPublicKeyInfo
                ))
            
            log.info("RSA key pair generated and saved")
        
        # Tải keys
        with open(PRIV_PATH, "rb") as f:
            self.private_key = serialization.load_pem_private_key(
                f.read(),
                password=None,
                backend=default_backend()
            )
        
        with open(PUB_PATH, "rb") as f:
            self.public_key = serialization.load_pem_public_key(
                f.read(),
                backend=default_backend()
            )
        
        # Public key base64
        self.public_key_b64 = base64.b64encode(
            self.public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
        ).decode()
        
        # Fingerprint
        der = self.public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        self.public_key_fingerprint = hashlib.sha256(der).hexdigest()[:16]
    
    def _load_or_create_fernet(self):
        """Tải hoặc tạo Fernet key cho mã hóa đối xứng."""
        if not os.path.exists(FER_PATH):
            log.info("Generating new Fernet key...")
            key = Fernet.generate_key()
            with open(FER_PATH, "wb") as f:
                f.write(key)
        
        with open(FER_PATH, "rb") as f:
            self.fernet_key = f.read()
            self.fernet = Fernet(self.fernet_key)
    
    def _generate_prefix(self):
        """Tạo prefix ngẫu nhiên dựa trên public key fingerprint."""
        chars = string.ascii_uppercase + string.digits
        random.seed(int(self.public_key_fingerprint, 16))
        self.prefix = ''.join(random.choice(chars) for _ in range(6))
    
    def sign_payload(self, payload_bytes: bytes) -> bytes:
        """Ký payload bằng RSA-PSS SHA256."""
        return self.private_key.sign(
            payload_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
    
    def verify_signature(self, payload_bytes: bytes, signature: bytes) -> bool:
        """Xác minh chữ ký RSA-PSS SHA256."""
        try:
            self.public_key.verify(
                signature,
                payload_bytes,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except InvalidSignature:
            return False
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Mã hóa dữ liệu bằng Fernet."""
        return self.fernet.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Giải mã dữ liệu bằng Fernet."""
        return self.fernet.decrypt(encrypted_data)
    
    def encrypt_json(self, data: dict) -> str:
        """Mã hóa JSON thành base64 string."""
        encrypted = self.encrypt_data(json.dumps(data).encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_json(self, encrypted_str: str) -> dict:
        """Giải mã base64 string thành JSON."""
        encrypted = base64.b64decode(encrypted_str)
        decrypted = self.decrypt_data(encrypted)
        return json.loads(decrypted)

crypto = CryptoManager()

# =====================================================================
# LICENSE MANAGER
# =====================================================================

class LicenseManager:
    """Quản lý tạo và xác minh license key."""
    
    @staticmethod
    def generate_license(
        product: str,
        days: int = 30,
        features: List[str] = None,
        quantity: int = 0,
        custom_data: dict = None
    ) -> str:
        """Tạo license key có chữ ký RSA."""
        if features is None:
            features = ['basic']
        
        expiry_date = datetime.date.today() + datetime.timedelta(days=days)
        payload = {
            'product': product,
            'expiry': expiry_date.strftime('%Y-%m-%d'),
            'duration_days': days,
            'features': features,
            'quantity': quantity if quantity > 0 else None,
            'prefix': crypto.prefix,
            'generated_at': datetime.datetime.now().isoformat(),
            'key_id': str(uuid.uuid4())[:8],
            'version': '4.0',
            'platform': 'ios'
        }
        
        if custom_data:
            payload['custom'] = custom_data
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = crypto.sign_payload(payload_bytes)
        
        # Đóng gói: [4 bytes len] + [payload] + [signature]
        payload_len = len(payload_bytes).to_bytes(4, byteorder='big')
        packed = payload_len + payload_bytes + signature
        
        return base64.urlsafe_b64encode(packed).decode('utf-8').rstrip('=')
    
    @staticmethod
    def generate_license_hours(
        product: str,
        hours: int = 24,
        features: List[str] = None,
        quantity: int = 0
    ) -> str:
        """Tạo license key theo giờ."""
        if features is None:
            features = ['trial']
        
        expiry_dt = datetime.datetime.now() + datetime.timedelta(hours=hours)
        payload = {
            'product': product,
            'expiry': expiry_dt.strftime('%Y-%m-%d %H:%M:%S'),
            'duration_hours': hours,
            'features': features,
            'quantity': quantity if quantity > 0 else None,
            'prefix': crypto.prefix,
            'generated_at': datetime.datetime.now().isoformat(),
            'key_id': str(uuid.uuid4())[:8],
            'version': '4.0',
            'platform': 'ios'
        }
        
        payload_bytes = json.dumps(payload).encode('utf-8')
        signature = crypto.sign_payload(payload_bytes)
        
        payload_len = len(payload_bytes).to_bytes(4, byteorder='big')
        packed = payload_len + payload_bytes + signature
        
        return base64.urlsafe_b64encode(packed).decode('utf-8').rstrip('=')
    
    @staticmethod
    def verify_license(
        license_key: str,
        user_id: int = None,
        device_udid: str = None,
        source: str = 'api'
    ) -> Tuple[bool, str, Optional[dict], Optional[str]]:
        """Xác minh license key."""
        try:
            # Thêm padding base64 nếu cần
            padding_needed = 4 - len(license_key) % 4
            if padding_needed != 4:
                license_key += '=' * padding_needed
            
            # Giải mã
            decoded = base64.urlsafe_b64decode(license_key)
            
            # Tách payload và signature
            payload_len = int.from_bytes(decoded[:4], byteorder='big')
            payload_bytes = decoded[4:4+payload_len]
            signature = decoded[4+payload_len:]
            
            # Xác minh chữ ký
            if not crypto.verify_signature(payload_bytes, signature):
                return False, "❌ CHỮ KÝ KHÔNG HỢP LỆ", None, None
            
            # Parse payload
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            # Kiểm tra hết hạn
            expiry_str = payload.get('expiry', '')
            try:
                # Thử định dạng datetime trước
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    # Thử định dạng date
                    expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d')
                    expiry_dt = datetime.datetime.combine(
                        expiry_dt.date(),
                        datetime.time.max
                    )
                except ValueError:
                    return False, "❌ ĐỊNH DẠNG NGÀY KHÔNG HỢP LỆ", None, None
            
            if datetime.datetime.now() > expiry_dt:
                return False, f"⏰ KEY ĐÃ HẾT HẠN ({expiry_str})", None, None
            
            # Hash key
            key_hash = hashlib.sha256(license_key.encode()).hexdigest()
            key_short = license_key[:30]
            
            # Kiểm tra trong database
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Kiểm tra đã kích hoạt chưa
            cursor.execute(
                "SELECT id, user_id, device_udid FROM activated_keys WHERE key_hash = ? AND is_active = 1",
                (key_hash,)
            )
            existing = cursor.fetchone()
            if existing:
                conn.close()
                if user_id and existing['user_id'] == user_id:
                    return False, "⚠️ BẠN ĐÃ KÍCH HOẠT KEY NÀY RỒI", None, None
                elif device_udid and existing['device_udid'] == device_udid:
                    return False, "⚠️ THIẾT BỊ NÀY ĐÃ KÍCH HOẠT KEY", None, None
                else:
                    return False, "⚠️ KEY ĐÃ ĐƯỢC KÍCH HOẠT BỞI NGƯỜI KHÁC", None, None
            
            # Kiểm tra số lượng
            quantity = payload.get('quantity')
            if quantity is not None:
                cursor.execute(
                    "SELECT COUNT(*) as cnt FROM activated_keys WHERE key_hash = ? AND is_active = 1",
                    (key_hash,)
                )
                count = cursor.fetchone()['cnt']
                if count >= quantity:
                    conn.close()
                    return False, f"📱 ĐÃ ĐẠT GIỚI HẠN {quantity} THIẾT BỊ", None, None
            
            # Kiểm tra bị thu hồi
            cursor.execute(
                "SELECT id FROM revoked_keys WHERE key_short = ?",
                (key_short,)
            )
            if cursor.fetchone():
                conn.close()
                return False, "🚫 KEY ĐÃ BỊ THU HỒI", None, None
            
            conn.close()
            
            key_id = payload.get('key_id', 'unknown')
            return True, f"✅ HỢP LỆ: {payload['product']}", payload, key_id
            
        except Exception as e:
            log.error(f"License verification error: {e}")
            return False, f"❌ LỖI XÁC MINH: {str(e)[:80]}", None, None
    
    @staticmethod
    def save_generated_key(
        license_key: str,
        product: str,
        key_type: str,
        expiry: str,
        duration_days: int,
        duration_hours: int,
        quantity: int,
        features: List[str],
        created_by: int,
        created_by_username: str,
        notes: str = None
    ) -> int:
        """Lưu key đã tạo vào database."""
        key_short = license_key[:30]
        key_hash = hashlib.sha256(license_key.encode()).hexdigest()
        key_id = str(uuid.uuid4())[:8]
        
        cursor = db_manager.execute(
            """INSERT INTO license_keys 
            (key_full, key_short, key_hash, product, type, expiry, 
             duration_days, duration_hours, quantity, features, prefix, 
             key_id, created_by, created_by_username, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (license_key, key_short, key_hash, product, key_type, expiry,
             duration_days, duration_hours, quantity if quantity > 0 else None,
             json.dumps(features), crypto.prefix, key_id,
             created_by, created_by_username, notes)
        )
        
        return cursor.lastrowid
    
    @staticmethod
    def save_activated_key(
        license_key: str,
        user_id: int,
        username: str,
        first_name: str,
        last_name: str,
        device_udid: str,
        device_name: str,
        device_model: str,
        device_os: str,
        device_fingerprint: str,
        payload: dict,
        source: str,
        ip_address: str
    ) -> bool:
        """Lưu key đã kích hoạt vào database."""
        try:
            activation_id = str(uuid.uuid4())
            key_hash = hashlib.sha256(license_key.encode()).hexdigest()
            key_short = license_key[:30]
            
            cursor = db_manager.execute(
                """INSERT INTO activated_keys 
                (activation_id, key_hash, key_short, user_id, username, 
                 first_name, last_name, device_udid, device_name, device_model,
                 device_os, device_fingerprint, product, expiry, features,
                 source, ip_address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (activation_id, key_hash, key_short, user_id, username,
                 first_name, last_name, device_udid, device_name, device_model,
                 device_os, device_fingerprint, payload['product'], payload['expiry'],
                 json.dumps(payload.get('features', [])), source, ip_address)
            )
            
            # Cập nhật thống kê user
            db_manager.execute(
                "UPDATE telegram_users SET total_activated = total_activated + 1 WHERE user_id = ?",
                (user_id,)
            )
            
            return True
        except Exception as e:
            log.error(f"Error saving activated key: {e}")
            return False

license_manager = LicenseManager()

# =====================================================================
# TOKEN MANAGER
# =====================================================================

class TokenManager:
    """Quản lý API tokens."""
    
    @staticmethod
    def generate_token(
        user_id: int,
        username: str,
        first_name: str,
        token_name: str = "Default Token",
        device_limit: int = 5,
        permissions: str = "activate,verify,heartbeat,config",
        request_limit: int = 1000,
        expires_days: int = 365
    ) -> Tuple[str, str]:
        """Tạo API token mới."""
        token = secrets.token_hex(32)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        token_prefix = token[:10]
        
        expires_at = None
        if expires_days > 0:
            expires_at = (datetime.datetime.now() + datetime.timedelta(days=expires_days)).isoformat()
        
        db_manager.execute(
            """INSERT INTO api_tokens 
            (token, token_hash, token_prefix, user_id, username, first_name,
             token_name, permissions, device_limit, request_limit, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (token, token_hash, token_prefix, user_id, username, first_name,
             token_name, permissions, device_limit, request_limit, expires_at)
        )
        
        return token, token_hash
    
    @staticmethod
    def verify_token(token: str) -> Tuple[bool, Optional[dict], str]:
        """Xác minh API token. Trả về (valid, token_info, error_message)."""
        if not token:
            return False, None, "Thiếu X-API-Token header"
        
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        
        row = db_manager.fetchone(
            """SELECT * FROM api_tokens 
            WHERE token_hash = ? AND is_active = 1""",
            (token_hash,)
        )
        
        if not row:
            return False, None, "Token không tồn tại hoặc đã bị vô hiệu hóa"
        
        # Kiểm tra hết hạn
        if row['expires_at']:
            expires_dt = datetime.datetime.fromisoformat(row['expires_at'])
            if datetime.datetime.now() > expires_dt:
                return False, None, "Token đã hết hạn"
        
        # Kiểm tra request limit
        if row['request_limit'] > 0:
            if row['requests_used'] >= row['request_limit']:
                return False, None, "Đã vượt quá giới hạn request"
        
        # Kiểm tra IP whitelist
        if row['ip_whitelist'] and row['ip_whitelist'] != '[]':
            whitelist = json.loads(row['ip_whitelist'])
            if whitelist:
                # IP check sẽ được thực hiện ở middleware
                pass
        
        # Cập nhật last_used_at và requests_used
        db_manager.execute(
            "UPDATE api_tokens SET last_used_at = CURRENT_TIMESTAMP, requests_used = requests_used + 1 WHERE id = ?",
            (row['id'],)
        )
        
        # Reset request count nếu đã qua ngày mới
        if row['last_reset_at']:
            last_reset = datetime.datetime.fromisoformat(row['last_reset_at'])
            if datetime.datetime.now().date() > last_reset.date():
                db_manager.execute(
                    "UPDATE api_tokens SET requests_used = 0, last_reset_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (row['id'],)
                )
        
        token_info = {
            'id': row['id'],
            'user_id': row['user_id'],
            'username': row['username'],
            'token_name': row['token_name'],
            'permissions': row['permissions'].split(','),
            'device_limit': row['device_limit'],
            'token_prefix': row['token_prefix']
        }
        
        return True, token_info, ""
    
    @staticmethod
    def revoke_token(token_id: int) -> bool:
        """Thu hồi API token."""
        db_manager.execute(
            "UPDATE api_tokens SET is_active = 0 WHERE id = ?",
            (token_id,)
        )
        return True
    
    @staticmethod
    def list_tokens(user_id: int = None) -> List[dict]:
        """Liệt kê API tokens."""
        if user_id:
            rows = db_manager.fetchall(
                "SELECT id, token_prefix, token_name, username, user_id, permissions, is_active, device_limit, request_limit, requests_used, created_at, last_used_at, expires_at FROM api_tokens WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            )
        else:
            rows = db_manager.fetchall(
                "SELECT id, token_prefix, token_name, username, user_id, permissions, is_active, device_limit, request_limit, requests_used, created_at, last_used_at, expires_at FROM api_tokens ORDER BY created_at DESC"
            )
        return [dict(row) for row in rows]

token_manager = TokenManager()

# =====================================================================
# DEVICE MANAGER
# =====================================================================

class DeviceManager:
    """Quản lý thiết bị đã đăng ký."""
    
    @staticmethod
    def register_device(
        api_token_id: int,
        device_udid: str,
        device_name: str = "Unknown",
        device_model: str = "Unknown",
        device_os: str = "Unknown",
        device_os_version: str = "Unknown",
        app_version: str = "1.0",
        app_bundle_id: str = None,
        device_fingerprint: str = None,
        activation_id: str = None,
        license_key_id: int = None,
        user_id: int = None,
        ip_address: str = None
    ) -> bool:
        """Đăng ký hoặc cập nhật thiết bị."""
        db_manager.execute(
            """INSERT OR REPLACE INTO registered_devices 
            (device_udid, device_name, device_model, device_os, device_os_version,
             app_version, app_bundle_id, device_fingerprint, api_token_id, 
             user_id, license_key_id, activation_id, is_active, ip_address, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, CURRENT_TIMESTAMP)""",
            (device_udid, device_name, device_model, device_os, device_os_version,
             app_version, app_bundle_id, device_fingerprint, api_token_id,
             user_id, license_key_id, activation_id, ip_address)
        )
        return True
    
    @staticmethod
    def get_device_count(api_token_id: int, exclude_udid: str = None) -> int:
        """Đếm số thiết bị đang active của một token."""
        if exclude_udid:
            return db_manager.count(
                "registered_devices",
                "api_token_id = ? AND is_active = 1 AND device_udid != ?",
                (api_token_id, exclude_udid)
            )
        return db_manager.count(
            "registered_devices",
            "api_token_id = ? AND is_active = 1",
            (api_token_id,)
        )
    
    @staticmethod
    def update_last_seen(device_udid: str, api_token_id: int, ip_address: str = None):
        """Cập nhật thời gian last_seen của thiết bị."""
        db_manager.execute(
            """UPDATE registered_devices 
            SET last_seen = CURRENT_TIMESTAMP, heartbeat_count = heartbeat_count + 1,
                ip_address = COALESCE(?, ip_address)
            WHERE device_udid = ? AND api_token_id = ?""",
            (ip_address, device_udid, api_token_id)
        )
    
    @staticmethod
    def record_heartbeat(
        device_udid: str,
        activation_id: str = None,
        license_key_id: int = None,
        api_token_id: int = None,
        ip_address: str = None,
        app_version: str = None,
        device_status: str = 'active',
        battery_level: int = None,
        network_type: str = None
    ):
        """Ghi nhận heartbeat từ thiết bị."""
        db_manager.execute(
            """INSERT INTO heartbeats 
            (device_udid, activation_id, license_key_id, api_token_id, 
             ip_address, app_version, device_status, battery_level, network_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (device_udid, activation_id, license_key_id, api_token_id,
             ip_address, app_version, device_status, battery_level, network_type)
        )

device_manager = DeviceManager()

# =====================================================================
# AUDIT LOGGER
# =====================================================================

class AuditLogger:
    """Ghi log hoạt động hệ thống."""
    
    @staticmethod
    def log_action(
        user_id: int,
        username: str,
        action: str,
        details: str = None,
        ip_address: str = None
    ):
        """Ghi một hành động vào audit log."""
        db_manager.execute(
            """INSERT INTO audit_log (user_id, username, action, details, ip_address)
            VALUES (?, ?, ?, ?, ?)""",
            (user_id, username, action, details, ip_address)
        )
    
    @staticmethod
    def get_recent_logs(limit: int = 100) -> List[dict]:
        """Lấy các log gần đây."""
        rows = db_manager.fetchall(
            "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in rows]

audit_logger = AuditLogger()

# =====================================================================
# FLASK APPLICATION
# =====================================================================

app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
app.config['SECRET_KEY'] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config['JSON_AS_ASCII'] = False
app.config['JSON_SORT_KEYS'] = False

# Rate Limiter
limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="memory://"
)

# =====================================================================
# FLASK MIDDLEWARE
# =====================================================================

@app.before_request
def before_request_middleware():
    """Middleware chạy trước mỗi request."""
    g.start_time = time.time()
    g.request_id = str(uuid.uuid4())
    
    # Kiểm tra maintenance mode
    if FEATURES.get('ENABLE_MAINTENANCE_MODE', False):
        if not request.path.startswith('/api/health'):
            return jsonify({
                'status': 'error',
                'message': 'Server đang bảo trì, vui lòng thử lại sau.',
                'request_id': g.request_id
            }), 503
    
    # Kiểm tra IP blacklist
    if FEATURES.get('ENABLE_IP_BLACKLIST', True):
        ip = request.remote_addr
        row = db_manager.fetchone(
            "SELECT id FROM ip_blacklist WHERE ip_address = ? AND is_active = 1 AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)",
            (ip,)
        )
        if row:
            return jsonify({
                'status': 'error',
                'message': 'IP bị chặn. Liên hệ admin để được hỗ trợ.',
                'request_id': g.request_id
            }), 403

@app.after_request
def after_request_middleware(response: Response) -> Response:
    """Middleware chạy sau mỗi request."""
    elapsed_ms = (time.time() - g.start_time) * 1000
    
    # Thêm headers
    response.headers['X-Request-ID'] = g.request_id
    response.headers['X-Response-Time'] = f"{elapsed_ms:.2f}ms"
    response.headers['X-Server'] = 'License-System/4.0'
    response.headers['X-Powered-By'] = 'Huy-93ob'
    
    # Log API request
    if FEATURES.get('ENABLE_API_LOGGING', True) and request.path.startswith('/api/'):
        token = request.headers.get('X-API-Token', 'none')
        token_hash = hashlib.sha256(token.encode()).hexdigest() if token != 'none' else 'none'
        token_prefix = token[:10] if token != 'none' else 'none'
        
        try:
            db_manager.execute(
                """INSERT INTO api_logs 
                (token_hash, token_prefix, endpoint, method, ip_address, 
                 user_agent, request_body, response_code, response_time_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (token_hash, token_prefix, request.path, request.method,
                 request.remote_addr, request.headers.get('User-Agent', '')[:500],
                 str(request.get_json(silent=True))[:1000] if request.is_json else None,
                 response.status_code, round(elapsed_ms, 2))
            )
        except Exception as e:
            log.error(f"API log error: {e}")
    
    return response

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Endpoint không tồn tại',
        'request_id': g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'status': 'error',
        'message': 'Lỗi máy chủ nội bộ',
        'request_id': g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    }), 500

# =====================================================================
# API ENDPOINTS - PUBLIC
# =====================================================================

@app.route('/')
def api_root():
    """Trang chủ API."""
    return jsonify({
        'status': 'running',
        'server': 'iOS License System',
        'version': '4.0.0',
        'server_url': SERVER_URL,
        'prefix': crypto.prefix,
        'public_key_fingerprint': crypto.public_key_fingerprint,
        'endpoints': {
            'health': f'{SERVER_URL}/api/health',
            'status': f'{SERVER_URL}/api/status',
            'activate': f'{SERVER_URL}/api/activate',
            'verify': f'{SERVER_URL}/api/verify',
            'heartbeat': f'{SERVER_URL}/api/heartbeat',
            'config': f'{SERVER_URL}/api/ios/config',
            'report': f'{SERVER_URL}/api/report'
        },
        'documentation': f'{SERVER_URL}/api/docs',
        'contact': {
            'telegram': '@huy_93ob',
            'support': f'{SERVER_URL}/api/support'
        }
    })

@app.route('/api/health')
def api_health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'server': SERVER_URL,
        'prefix': crypto.prefix,
        'timestamp': datetime.datetime.now().isoformat(),
        'uptime': 'running',
        'version': '4.0.0'
    })

@app.route('/api/status')
def api_status():
    """Trạng thái server."""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    stats = {
        'license_keys': cursor.execute("SELECT COUNT(*) as cnt FROM license_keys").fetchone()['cnt'],
        'activated_keys': cursor.execute("SELECT COUNT(*) as cnt FROM activated_keys WHERE is_active = 1").fetchone()['cnt'],
        'revoked_keys': cursor.execute("SELECT COUNT(*) as cnt FROM revoked_keys").fetchone()['cnt'],
        'active_devices': cursor.execute("SELECT COUNT(*) as cnt FROM registered_devices WHERE is_active = 1").fetchone()['cnt'],
        'active_tokens': cursor.execute("SELECT COUNT(*) as cnt FROM api_tokens WHERE is_active = 1").fetchone()['cnt'],
        'total_heartbeats': cursor.execute("SELECT COUNT(*) as cnt FROM heartbeats").fetchone()['cnt'],
        'total_users': cursor.execute("SELECT COUNT(*) as cnt FROM telegram_users").fetchone()['cnt'],
        'api_calls_today': cursor.execute(
            "SELECT COUNT(*) as cnt FROM api_logs WHERE date(created_at) = date('now')"
        ).fetchone()['cnt']
    }
    
    conn.close()
    
    return jsonify({
        'status': 'running',
        'server': SERVER_URL,
        'prefix': crypto.prefix,
        'fingerprint': crypto.public_key_fingerprint,
        'stats': stats,
        'timestamp': datetime.datetime.now().isoformat()
    })

# =====================================================================
# API ENDPOINTS - LICENSE ACTIVATION
# =====================================================================

@app.route('/api/activate', methods=['POST'])
@limiter.limit(RATE_LIMIT_ACTIVATE)
def api_activate():
    """Kích hoạt license key."""
    request_id = g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    
    # Xác thực token
    token = request.headers.get('X-API-Token', '')
    valid, token_info, error_msg = token_manager.verify_token(token)
    if not valid:
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'request_id': request_id
        }), 401
    
    # Kiểm tra quyền
    if 'activate' not in token_info['permissions']:
        return jsonify({
            'status': 'error',
            'message': 'Token không có quyền kích hoạt',
            'request_id': request_id
        }), 403
    
    # Parse request body
    data = request.get_json(silent=True)
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'Body không hợp lệ',
            'request_id': request_id
        }), 400
    
    license_key = data.get('license_key', '').strip()
    device_udid = data.get('udid', '').strip()
    
    if not license_key or not device_udid:
        return jsonify({
            'status': 'error',
            'message': 'Thiếu license_key hoặc udid',
            'request_id': request_id
        }), 400
    
    # Kiểm tra device limit
    device_count = device_manager.get_device_count(token_info['id'], device_udid)
    if device_count >= token_info['device_limit']:
        return jsonify({
            'status': 'error',
            'message': f"Đã đạt giới hạn {token_info['device_limit']} thiết bị cho token này",
            'request_id': request_id
        }), 403
    
    # Xác minh license key
    is_valid, message, payload, key_id = license_manager.verify_license(
        license_key,
        user_id=token_info['user_id'],
        device_udid=device_udid,
        source='api'
    )
    
    if not is_valid or not payload:
        return jsonify({
            'status': 'error',
            'message': message,
            'request_id': request_id
        }), 403
    
    # Lưu key đã kích hoạt
    device_name = data.get('device_name', 'Unknown')
    device_model = data.get('device_model', 'Unknown')
    device_os = data.get('ios_version', 'Unknown')
    device_fingerprint = data.get('device_fingerprint', hashlib.sha256(device_udid.encode()).hexdigest()[:16])
    
    saved = license_manager.save_activated_key(
        license_key=license_key,
        user_id=token_info['user_id'],
        username=token_info['username'],
        first_name=data.get('first_name', ''),
        last_name=data.get('last_name', ''),
        device_udid=device_udid,
        device_name=device_name,
        device_model=device_model,
        device_os=device_os,
        device_fingerprint=device_fingerprint,
        payload=payload,
        source='ios_api',
        ip_address=request.remote_addr
    )
    
    # Đăng ký thiết bị
    device_manager.register_device(
        api_token_id=token_info['id'],
        device_udid=device_udid,
        device_name=device_name,
        device_model=device_model,
        device_os='iOS',
        device_os_version=device_os,
        app_version=data.get('app_version', '1.0'),
        app_bundle_id=data.get('app_bundle_id'),
        device_fingerprint=device_fingerprint,
        activation_id=str(uuid.uuid4()),
        user_id=token_info['user_id'],
        ip_address=request.remote_addr
    )
    
    # Ghi audit log
    audit_logger.log_action(
        user_id=token_info['user_id'],
        username=token_info['username'],
        action='LICENSE_ACTIVATED',
        details=f"Product: {payload['product']}, Key ID: {key_id}, Device: {device_udid}",
        ip_address=request.remote_addr
    )
    
    return jsonify({
        'status': 'success',
        'message': message,
        'data': {
            'product': payload['product'],
            'expiry': payload['expiry'],
            'features': payload.get('features', []),
            'key_id': key_id,
            'duration_days': payload.get('duration_days', 0),
            'duration_hours': payload.get('duration_hours', 0),
            'activated_at': datetime.datetime.now().isoformat(),
            'server': SERVER_URL
        },
        'request_id': request_id
    })

# =====================================================================
# API ENDPOINTS - VERIFY
# =====================================================================

@app.route('/api/verify', methods=['POST'])
@limiter.limit(RATE_LIMIT_VERIFY)
def api_verify():
    """Kiểm tra license key không kích hoạt."""
    request_id = g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    
    token = request.headers.get('X-API-Token', '')
    valid, token_info, error_msg = token_manager.verify_token(token)
    if not valid:
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'request_id': request_id
        }), 401
    
    data = request.get_json(silent=True) or {}
    license_key = data.get('license_key', '').strip()
    
    if not license_key:
        return jsonify({
            'status': 'error',
            'message': 'Thiếu license_key',
            'request_id': request_id
        }), 400
    
    is_valid, message, payload, key_id = license_manager.verify_license(
        license_key,
        user_id=token_info['user_id'],
        device_udid=data.get('udid', ''),
        source='api'
    )
    
    response = {
        'status': 'valid' if is_valid else 'invalid',
        'message': message,
        'server': SERVER_URL,
        'request_id': request_id
    }
    
    if payload:
        response['data'] = {
            'product': payload['product'],
            'expiry': payload['expiry'],
            'features': payload.get('features', []),
            'key_id': key_id,
            'duration_days': payload.get('duration_days', 0),
            'duration_hours': payload.get('duration_hours', 0)
        }
    
    return jsonify(response), 200 if is_valid else 403

# =====================================================================
# API ENDPOINTS - HEARTBEAT
# =====================================================================

@app.route('/api/heartbeat', methods=['POST'])
@limiter.limit(RATE_LIMIT_HEARTBEAT)
def api_heartbeat():
    """Nhận heartbeat từ thiết bị iOS."""
    request_id = g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    
    token = request.headers.get('X-API-Token', '')
    valid, token_info, error_msg = token_manager.verify_token(token)
    if not valid:
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'request_id': request_id
        }), 401
    
    data = request.get_json(silent=True) or {}
    device_udid = data.get('udid', '').strip()
    
    if not device_udid:
        return jsonify({
            'status': 'error',
            'message': 'Thiếu udid',
            'request_id': request_id
        }), 400
    
    # Cập nhật last_seen
    device_manager.update_last_seen(
        device_udid=device_udid,
        api_token_id=token_info['id'],
        ip_address=request.remote_addr
    )
    
    # Ghi heartbeat
    device_manager.record_heartbeat(
        device_udid=device_udid,
        api_token_id=token_info['id'],
        ip_address=request.remote_addr,
        app_version=data.get('app_version', '1.0'),
        device_status=data.get('device_status', 'active'),
        battery_level=data.get('battery_level'),
        network_type=data.get('network_type')
    )
    
    return jsonify({
        'status': 'ok',
        'server': SERVER_URL,
        'server_time': datetime.datetime.now().isoformat(),
        'heartbeat_interval': 300,
        'request_id': request_id
    })

# =====================================================================
# API ENDPOINTS - iOS CONFIG
# =====================================================================

@app.route('/api/ios/config')
@limiter.limit(RATE_LIMIT_CONFIG)
def api_ios_config():
    """Trả về cấu hình cho iOS client (đã mã hóa)."""
    request_id = g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    
    token = request.headers.get('X-API-Token', '')
    valid, token_info, error_msg = token_manager.verify_token(token)
    if not valid:
        return jsonify({
            'status': 'error',
            'message': error_msg,
            'request_id': request_id
        }), 401
    
    # Tạo cấu hình
    config = {
        'server_url': SERVER_URL,
        'prefix': crypto.prefix,
        'public_key_base64': crypto.public_key_b64,
        'public_key_fingerprint': crypto.public_key_fingerprint,
        'fernet_key_base64': base64.b64encode(crypto.fernet_key).decode(),
        'endpoints': {
            'activate': f"{SERVER_URL}/api/activate",
            'verify': f"{SERVER_URL}/api/verify",
            'heartbeat': f"{SERVER_URL}/api/heartbeat",
            'report': f"{SERVER_URL}/api/report",
            'config': f"{SERVER_URL}/api/ios/config"
        },
        'token_info': {
            'user_id': token_info['user_id'],
            'username': token_info['username'],
            'device_limit': token_info['device_limit'],
            'token_prefix': token_info['token_prefix']
        },
        'timestamp': datetime.datetime.now().isoformat(),
        'version': '4.0.0'
    }
    
    # Mã hóa config
    encrypted = crypto.encrypt_json(config)
    
    return jsonify({
        'encrypted_config': encrypted,
        'request_id': request_id
    })

# =====================================================================
# API ENDPOINTS - REPORT
# =====================================================================

@app.route('/api/report', methods=['POST'])
def api_report():
    """Nhận báo cáo lỗi/tamper từ client."""
    request_id = g.request_id if hasattr(g, 'request_id') else str(uuid.uuid4())
    
    data = request.get_json(silent=True) or {}
    
    log.warning(f"Client Report - IP: {request.remote_addr}, Data: {json.dumps(data)[:500]}")
    
    # Ghi audit log
    audit_logger.log_action(
        user_id=data.get('user_id', 0),
        username=data.get('username', 'unknown'),
        action='CLIENT_REPORT',
        details=f"Type: {data.get('type', 'unknown')}, Message: {data.get('message', '')[:200]}",
        ip_address=request.remote_addr
    )
    
    return jsonify({
        'status': 'received',
        'server': SERVER_URL,
        'request_id': request_id
    })

# =====================================================================
# TELEGRAM BOT HANDLERS
# =====================================================================

def admin_only(func):
    """Decorator yêu cầu quyền admin."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ Bạn không có quyền sử dụng lệnh này.\nLiên hệ @huy_93ob để được cấp quyền.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

def super_admin_only(func):
    """Decorator yêu cầu quyền super admin."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id != SUPER_ADMIN_ID:
            await update.message.reply_text("⛔ Chỉ Super Admin mới có quyền này.")
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# =====================================================================
# TELEGRAM COMMAND: /start
# =====================================================================

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /start - Hiển thị menu chính."""
    user = update.effective_user
    
    # Lưu user vào database
    db_manager.execute(
        """INSERT OR REPLACE INTO telegram_users 
        (user_id, username, first_name, last_name, language_code, last_interaction)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)""",
        (user.id, user.username, user.first_name, user.last_name, user.language_code)
    )
    
    welcome_text = f"""
╔══════════════════════════════════════╗
║   🔐 iOS LICENSE SYSTEM v4.0       ║
║   Server: huy-93ob.onrender.com    ║
╚══════════════════════════════════════╝

👤 Xin chào, **{user.first_name}**!

📋 **LỆNH NGƯỜI DÙNG:**
  /start - Menu chính
  /activate - Kích hoạt license key
  /mykeys - Xem key đã kích hoạt
  /help - Hướng dẫn chi tiết
  /info - Thông tin server
  /contact - Liên hệ hỗ trợ

🌐 **API SERVER:**
  `{SERVER_URL}`

📡 **ENDPOINTS:**
  POST /api/activate
  POST /api/verify
  POST /api/heartbeat
  GET  /api/ios/config
  GET  /api/status

⚙️ **ADMIN COMMANDS:**
  /key - Tạo key nhanh
  /token - Quản lý API token
  /status - Thống kê
  /admin - Menu admin
"""
    
    # Tạo keyboard
    keyboard = [
        [KeyboardButton("🔑 Kích hoạt key"), KeyboardButton("📱 Key của tôi")],
        [KeyboardButton("ℹ️ Thông tin"), KeyboardButton("📞 Hỗ trợ")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=reply_markup
    )

# =====================================================================
# TELEGRAM COMMAND: /activate
# =====================================================================

async def cmd_activate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /activate - Kích hoạt license key."""
    user = update.effective_user
    message_text = update.message.text.strip()
    
    # Xử lý input
    if message_text.startswith('/activate'):
        parts = message_text.split(maxsplit=1)
        if len(parts) < 2:
            await update.message.reply_text(
                "⚠️ **CÁCH DÙNG:**\n"
                "`/activate <license_key>`\n\n"
                "Hoặc gửi trực tiếp license key cho bot.\n\n"
                "📌 Ví dụ:\n"
                "`/activate ABCDEF123456...`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        license_key = parts[1].strip()
    else:
        # User gửi trực tiếp key
        if len(message_text) < 50:
            return  # Không phải key, bỏ qua
        license_key = message_text
    
    # Gửi trạng thái đang xử lý
    processing_msg = await update.message.reply_text(
        "⏳ Đang xác minh license key...\nVui lòng đợi trong giây lát.",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Xác minh key
    is_valid, message, payload, key_id = license_manager.verify_license(
        license_key,
        user_id=user.id,
        source='telegram'
    )
    
    if is_valid and payload:
        # Lưu key đã kích hoạt
        saved = license_manager.save_activated_key(
            license_key=license_key,
            user_id=user.id,
            username=user.username or '',
            first_name=user.first_name or '',
            last_name=user.last_name or '',
            device_udid='TELEGRAM',
            device_name='Telegram Bot',
            device_model='Telegram',
            device_os='Telegram',
            device_fingerprint=f"tg_{user.id}",
            payload=payload,
            source='telegram',
            ip_address='Telegram'
        )
        
        # Ghi audit log
        audit_logger.log_action(
            user_id=user.id,
            username=user.username or user.first_name,
            action='LICENSE_ACTIVATED_TELEGRAM',
            details=f"Product: {payload['product']}, Key ID: {key_id}"
        )
    
    # Hiển thị kết quả
    icon = "✅" if is_valid else "❌"
    result_text = f"{icon} **{message}**"
    
    if payload:
        features = payload.get('features', [])
        result_text += f"""
        
📦 **Sản phẩm:** `{payload['product']}`
⏰ **Hết hạn:** `{payload['expiry']}`
🛠 **Tính năng:** {', '.join(features) if features else 'Cơ bản'}
🆔 **Key ID:** `{key_id}`
📅 **Ngày tạo:** `{payload.get('generated_at', 'N/A')[:10]}`

🌐 **Server:** `{SERVER_URL}`
"""
    
    await processing_msg.edit_text(result_text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /mykeys
# =====================================================================

async def cmd_mykeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lệnh /mykeys - Xem key đã kích hoạt."""
    user = update.effective_user
    
    rows = db_manager.fetchall(
        """SELECT product, expiry, features, source, activated_at, 
           last_heartbeat, is_active
           FROM activated_keys 
           WHERE user_id = ? 
           ORDER BY activated_at DESC""",
        (user.id,)
    )
    
    if not rows:
        await update.message.reply_text(
            "📭 **Bạn chưa kích hoạt key nào.**\n\n"
            "Dùng lệnh `/activate <key>` để kích hoạt.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    text = f"🔑 **KEY CỦA BẠN** ({len(rows)} key):\n\n"
    
    for i, row in enumerate(rows, 1):
        features = json.loads(row['features']) if row['features'] else []
        status_icon = "🟢" if row['is_active'] else "🔴"
        expiry_str = row['expiry']
        
        # Kiểm tra hết hạn
        try:
            expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d %H:%M:%S')
        except:
            try:
                expiry_dt = datetime.datetime.strptime(expiry_str, '%Y-%m-%d')
            except:
                expiry_dt = None
        
        if expiry_dt and expiry_dt < datetime.datetime.now():
            status_icon = "⏰"
        
        text += f"{status_icon} **#{i}** | 📦 `{row['product']}`\n"
        text += f"   ⏰ Hết hạn: `{expiry_str}`\n"
        if features:
            text += f"   🛠 Tính năng: {', '.join(features[:3])}\n"
        text += f"   📡 Nguồn: `{row['source']}` | 📅 Kích hoạt: `{row['activated_at'][:10]}`\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /key (Admin tạo key nhanh)
# =====================================================================

@admin_only
async def cmd_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/key <tên> <ngày> - Tạo key ngày, không giới hạn thiết bị."""
    args = update.message.text.split()
    
    if len(args) < 3:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n"
            "`/key <tên_sản_phẩm> <số_ngày>`\n\n"
            "📌 **Ví dụ:**\n"
            "`/key ProApp 365` - Key 365 ngày\n"
            "`/key TestApp 30` - Key 30 ngày\n\n"
            "📋 **Các lệnh tạo key khác:**\n"
            "/keyd - Key ngày + giới hạn máy\n"
            "/keyh - Key theo giờ\n"
            "/keyvip - Key VIP đầy đủ",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    product = args[1]
    try:
        days = int(args[2])
    except ValueError:
        await update.message.reply_text("⚠️ Số ngày phải là số nguyên.")
        return
    
    if days <= 0 or days > 36500:
        await update.message.reply_text("⚠️ Số ngày phải từ 1 đến 36500.")
        return
    
    # Tạo key
    license_key = license_manager.generate_license(
        product=product,
        days=days,
        features=['basic'],
        quantity=0
    )
    
    expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    
    # Lưu vào database
    license_manager.save_generated_key(
        license_key=license_key,
        product=product,
        key_type='standard',
        expiry=expiry_date,
        duration_days=days,
        duration_hours=0,
        quantity=0,
        features=['basic'],
        created_by=update.effective_user.id,
        created_by_username=update.effective_user.username or update.effective_user.first_name
    )
    
    # Ghi audit log
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='KEY_GENERATED',
        details=f"Product: {product}, Days: {days}, Type: standard"
    )
    
    await update.message.reply_text(
        f"✅ **KEY ĐÃ TẠO**\n\n"
        f"📦 **Sản phẩm:** `{product}`\n"
        f"⏰ **Hết hạn:** `{expiry_date}` ({days} ngày)\n"
        f"📱 **Giới hạn:** Không giới hạn thiết bị\n"
        f"🏷 **Prefix:** `{crypto.prefix}`\n\n"
        f"🔑 **LICENSE KEY:**\n"
        f"`{license_key}`\n\n"
        f"📋 **Kích hoạt:**\n"
        f"`/activate {license_key[:60]}...`\n\n"
        f"🌐 **API:**\n"
        f"```bash\n"
        f"curl -X POST {SERVER_URL}/api/activate \\\n"
        f"  -H \"X-API-Token: YOUR_TOKEN\" \\\n"
        f"  -d '{{\"license_key\":\"{license_key[:40]}...\",\"udid\":\"DEVICE_UDID\"}}'\n"
        f"```",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /keyd (Key ngày + giới hạn thiết bị)
# =====================================================================

@admin_only
async def cmd_keyd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/keyd <tên> <ngày> <số_lượng> - Key ngày + giới hạn máy."""
    args = update.message.text.split()
    
    if len(args) < 4:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n"
            "`/keyd <tên> <ngày> <số_lượng_máy>`\n\n"
            "📌 **Ví dụ:**\n"
            "`/keyd ProApp 365 5` - 365 ngày, 5 máy",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    product = args[1]
    try:
        days = int(args[2])
        quantity = int(args[3])
    except ValueError:
        await update.message.reply_text("⚠️ Ngày và số lượng phải là số nguyên.")
        return
    
    if quantity <= 0 or quantity > MAX_DEVICE_LIMIT:
        await update.message.reply_text(f"⚠️ Số lượng phải từ 1 đến {MAX_DEVICE_LIMIT}.")
        return
    
    license_key = license_manager.generate_license(
        product=product,
        days=days,
        features=['basic'],
        quantity=quantity
    )
    
    expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    
    license_manager.save_generated_key(
        license_key=license_key,
        product=product,
        key_type='limited',
        expiry=expiry_date,
        duration_days=days,
        duration_hours=0,
        quantity=quantity,
        features=['basic'],
        created_by=update.effective_user.id,
        created_by_username=update.effective_user.username or update.effective_user.first_name
    )
    
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='KEY_GENERATED_LIMITED',
        details=f"Product: {product}, Days: {days}, Quantity: {quantity}"
    )
    
    await update.message.reply_text(
        f"✅ **KEY ĐÃ TẠO (GIỚI HẠN)**\n\n"
        f"📦 **Sản phẩm:** `{product}`\n"
        f"⏰ **Hết hạn:** `{expiry_date}` ({days} ngày)\n"
        f"📱 **Giới hạn:** `{quantity}` thiết bị\n"
        f"🏷 **Prefix:** `{crypto.prefix}`\n\n"
        f"🔑 **LICENSE KEY:**\n"
        f"`{license_key}`",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /keyh (Key theo giờ)
# =====================================================================

@admin_only
async def cmd_keyh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/keyh <tên> <giờ> - Key theo giờ, 1 máy."""
    args = update.message.text.split()
    
    if len(args) < 3:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n"
            "`/keyh <tên> <số_giờ>`\n\n"
            "📌 **Ví dụ:**\n"
            "`/keyh Trial 72` - Key dùng thử 72 giờ",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    product = args[1]
    try:
        hours = int(args[2])
    except ValueError:
        await update.message.reply_text("⚠️ Số giờ phải là số nguyên.")
        return
    
    license_key = license_manager.generate_license_hours(
        product=product,
        hours=hours,
        features=['trial'],
        quantity=1
    )
    
    expiry_dt = datetime.datetime.now() + datetime.timedelta(hours=hours)
    expiry_str = expiry_dt.strftime('%d/%m/%Y %H:%M')
    
    license_manager.save_generated_key(
        license_key=license_key,
        product=product,
        key_type='trial_hours',
        expiry=expiry_str,
        duration_days=0,
        duration_hours=hours,
        quantity=1,
        features=['trial'],
        created_by=update.effective_user.id,
        created_by_username=update.effective_user.username or update.effective_user.first_name
    )
    
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='KEY_GENERATED_HOURS',
        details=f"Product: {product}, Hours: {hours}"
    )
    
    await update.message.reply_text(
        f"✅ **KEY THEO GIỜ ĐÃ TẠO**\n\n"
        f"📦 **Sản phẩm:** `{product}`\n"
        f"⏰ **Hết hạn:** `{expiry_str}` ({hours} giờ)\n"
        f"📱 **Giới hạn:** 1 thiết bị\n"
        f"🏷 **Prefix:** `{crypto.prefix}`\n\n"
        f"🔑 **LICENSE KEY:**\n"
        f"`{license_key}`",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /keyvip (Key VIP)
# =====================================================================

@admin_only
async def cmd_keyvip(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/keyvip <tên> <ngày> <sl> <tính_năng> - Key VIP đầy đủ."""
    args = update.message.text.split(maxsplit=4)
    
    if len(args) < 5:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n"
            "`/keyvip <tên> <ngày> <số_lượng> <tính_năng>`\n\n"
            "📌 **Ví dụ:**\n"
            "`/keyvip Ultra 365 10 premium,api,cloud,nocrack`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    product = args[1]
    try:
        days = int(args[2])
        quantity = int(args[3])
    except ValueError:
        await update.message.reply_text("⚠️ Ngày và số lượng phải là số.")
        return
    
    features = [f.strip() for f in args[4].split(',')]
    
    license_key = license_manager.generate_license(
        product=product,
        days=days,
        features=features,
        quantity=quantity
    )
    
    expiry_date = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    
    license_manager.save_generated_key(
        license_key=license_key,
        product=product,
        key_type='vip',
        expiry=expiry_date,
        duration_days=days,
        duration_hours=0,
        quantity=quantity,
        features=features,
        created_by=update.effective_user.id,
        created_by_username=update.effective_user.username or update.effective_user.first_name
    )
    
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='KEY_GENERATED_VIP',
        details=f"Product: {product}, Days: {days}, Qty: {quantity}, Features: {features}"
    )
    
    await update.message.reply_text(
        f"💎 **KEY VIP ĐÃ TẠO**\n\n"
        f"📦 **Sản phẩm:** `{product}`\n"
        f"⏰ **Hết hạn:** `{expiry_date}` ({days} ngày)\n"
        f"📱 **Giới hạn:** `{quantity}` thiết bị\n"
        f"🛠 **Tính năng:** `{', '.join(features)}`\n"
        f"🏷 **Prefix:** `{crypto.prefix}`\n\n"
        f"🔑 **LICENSE KEY:**\n"
        f"`{license_key}`",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /token (Admin quản lý API token)
# =====================================================================

@admin_only
async def cmd_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/token <user_id> [limit] - Tạo API token."""
    args = update.message.text.split()
    
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n"
            "`/token <user_id> [device_limit]`\n\n"
            "📌 **Ví dụ:**\n"
            "`/token 5736655322 10` - Token 10 máy",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    try:
        user_id = int(args[1])
        device_limit = int(args[2]) if len(args) > 2 else 5
    except ValueError:
        await update.message.reply_text("⚠️ User ID và limit phải là số.")
        return
    
    # Lấy thông tin user
    try:
        chat = await context.bot.get_chat(user_id)
        username = chat.username or ''
        first_name = chat.first_name or ''
    except:
        username = f"user_{user_id}"
        first_name = ''
    
    token, token_hash = token_manager.generate_token(
        user_id=user_id,
        username=username,
        first_name=first_name,
        device_limit=device_limit
    )
    
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='TOKEN_CREATED',
        details=f"For user: {user_id}, Device limit: {device_limit}"
    )
    
    await update.message.reply_text(
        f"✅ **API TOKEN ĐÃ TẠO**\n\n"
        f"👤 **User:** {first_name} ({user_id})\n"
        f"📱 **Device limit:** {device_limit}\n"
        f"🌐 **Server:** `{SERVER_URL}`\n\n"
        f"🔑 **TOKEN:**\n"
        f"`{token}`\n\n"
        f"📋 **iOS CLIENT:**\n"
        f"```objc\n"
        f"#define API_TOKEN @\"{token}\"\n"
        f"#define API_URL @\"{SERVER_URL}\"\n"
        f"```\n\n"
        f"📋 **CURL:**\n"
        f"```bash\n"
        f"curl -X POST {SERVER_URL}/api/activate \\\n"
        f"  -H \"X-API-Token: {token}\" \\\n"
        f"  -d '{{\"license_key\":\"...\",\"udid\":\"...\"}}'\n"
        f"```",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /status (Admin xem thống kê)
# =====================================================================

@admin_only
async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/status - Xem thống kê server."""
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    total_keys = cursor.execute("SELECT COUNT(*) as cnt FROM license_keys").fetchone()['cnt']
    activated = cursor.execute("SELECT COUNT(*) as cnt FROM activated_keys WHERE is_active = 1").fetchone()['cnt']
    revoked = cursor.execute("SELECT COUNT(*) as cnt FROM revoked_keys").fetchone()['cnt']
    devices = cursor.execute("SELECT COUNT(*) as cnt FROM registered_devices WHERE is_active = 1").fetchone()['cnt']
    tokens = cursor.execute("SELECT COUNT(*) as cnt FROM api_tokens WHERE is_active = 1").fetchone()['cnt']
    heartbeats = cursor.execute("SELECT COUNT(*) as cnt FROM heartbeats").fetchone()['cnt']
    users = cursor.execute("SELECT COUNT(*) as cnt FROM telegram_users").fetchone()['cnt']
    api_calls = cursor.execute(
        "SELECT COUNT(*) as cnt FROM api_logs WHERE date(created_at) = date('now')"
    ).fetchone()['cnt']
    
    conn.close()
    
    text = f"""
📊 **THỐNG KÊ HỆ THỐNG**

🌐 **Server:** `{SERVER_URL}`
🏷 **Prefix:** `{crypto.prefix}`
🔐 **Fingerprint:** `{crypto.public_key_fingerprint}`

📈 **SỐ LIỆU:**
🔑 Keys đã tạo: **{total_keys}**
✅ Đã kích hoạt: **{activated}**
🚫 Đã thu hồi: **{revoked}**
📱 Thiết bị active: **{devices}**
🔗 API tokens: **{tokens}**
💓 Heartbeats: **{heartbeats}**
👥 Người dùng: **{users}**
📞 API calls hôm nay: **{api_calls}**

⏰ **Server time:** `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`
🟢 **Trạng thái:** Đang hoạt động
"""
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /revoke (Admin thu hồi key)
# =====================================================================

@admin_only
async def cmd_revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/revoke <key> - Thu hồi license key."""
    args = update.message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await update.message.reply_text(
            "⚠️ **CÁCH DÙNG:**\n`/revoke <license_key>`",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    license_key = args[1].strip()
    key_short = license_key[:30]
    key_hash = hashlib.sha256(license_key.encode()).hexdigest()
    
    try:
        # Thêm vào bảng revoked
        db_manager.execute(
            """INSERT INTO revoked_keys (key_short, key_hash, reason, revoked_by, revoked_by_username)
            VALUES (?, ?, ?, ?, ?)""",
            (key_short, key_hash, 'Manual revoke via Telegram',
             update.effective_user.id,
             update.effective_user.username or update.effective_user.first_name)
        )
        
        # Vô hiệu hóa key đã kích hoạt
        db_manager.execute(
            "UPDATE activated_keys SET is_active = 0 WHERE key_hash = ?",
            (key_hash,)
        )
        
        # Vô hiệu hóa trong license_keys
        db_manager.execute(
            "UPDATE license_keys SET is_active = 0 WHERE key_short = ?",
            (key_short,)
        )
        
        audit_logger.log_action(
            user_id=update.effective_user.id,
            username=update.effective_user.username or update.effective_user.first_name,
            action='KEY_REVOKED',
            details=f"Key: {key_short}..."
        )
        
        await update.message.reply_text(
            f"🚫 **KEY ĐÃ BỊ THU HỒI**\n\n"
            f"🔑 Key: `{key_short}...`\n"
            f"👤 Người thu hồi: {update.effective_user.first_name}",
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception as e:
        await update.message.reply_text(f"⚠️ Lỗi: {str(e)}")

# =====================================================================
# TELEGRAM COMMAND: /help
# =====================================================================

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help - Hướng dẫn chi tiết."""
    text = f"""
📖 **HƯỚNG DẪN SỬ DỤNG**

🌐 **Server:** `{SERVER_URL}`

**LỆNH CƠ BẢN:**
/start - Menu chính
/activate <key> - Kích hoạt license
/mykeys - Xem key đã kích hoạt
/info - Thông tin server
/contact - Liên hệ hỗ trợ

**KÍCH HOẠT KEY:**
1. Nhận license key từ admin
2. Dùng lệnh `/activate <key>`
3. Hoặc gửi trực tiếp key cho bot

**API SỬ DỤNG:**
Header: `X-API-Token`
Endpoint: `POST /api/activate`

**LIÊN HỆ:**
Telegram: @huy_93ob
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /info
# =====================================================================

async def cmd_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/info - Thông tin server."""
    text = f"""
ℹ️ **THÔNG TIN SERVER**

🌐 **URL:** `{SERVER_URL}`
🏷 **Prefix:** `{crypto.prefix}`
🔐 **Fingerprint:** `{crypto.public_key_fingerprint}`
📦 **Version:** 4.0.0
🟢 **Status:** Running

📡 **ENDPOINTS:**
• `POST /api/activate`
• `POST /api/verify`
• `POST /api/heartbeat`
• `GET /api/ios/config`
• `GET /api/status`
• `GET /api/health`

👤 **Admin:** @huy_93ob
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /contact
# =====================================================================

async def cmd_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/contact - Thông tin liên hệ."""
    await update.message.reply_text(
        "📞 **LIÊN HỆ HỖ TRỢ**\n\n"
        "👤 **Admin:** @huy_93ob\n"
        "🌐 **Server:** huy-93ob.onrender.com\n\n"
        "💬 Gửi tin nhắn trực tiếp cho admin để được hỗ trợ.",
        parse_mode=ParseMode.MARKDOWN
    )

# =====================================================================
# TELEGRAM COMMAND: /admin (Menu admin)
# =====================================================================

@admin_only
async def cmd_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/admin - Menu quản trị."""
    text = f"""
👑 **MENU QUẢN TRỊ**

📋 **TẠO KEY:**
/key <tên> <ngày> - Key cơ bản
/keyd <tên> <ngày> <sl> - Key giới hạn
/keyh <tên> <giờ> - Key theo giờ
/keyvip <tên> <ngày> <sl> <feat> - Key VIP

🔑 **QUẢN LÝ:**
/token <uid> [limit] - Tạo API token
/revoke <key> - Thu hồi key
/status - Thống kê
/keys - Danh sách key gần đây
/tokens - Danh sách token
/devices - Danh sách thiết bị
/logs - Xem log gần đây
/backup - Backup database

⚙️ **HỆ THỐNG:**
/broadcast <msg> - Gửi TB tất cả
/blacklist <ip> - Chặn IP
/maintenance - Bật/tắt bảo trì

🌐 **Server:** `{SERVER_URL}`
"""
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /keys (Admin xem danh sách key)
# =====================================================================

@admin_only
async def cmd_keys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/keys - Danh sách key đã tạo gần đây."""
    rows = db_manager.fetchall(
        "SELECT * FROM license_keys ORDER BY created_at DESC LIMIT 20"
    )
    
    if not rows:
        await update.message.reply_text("📭 Chưa có key nào được tạo.")
        return
    
    text = "📋 **DANH SÁCH KEY GẦN ĐÂY:**\n\n"
    for row in rows:
        status = "🟢" if row['is_active'] else "🔴"
        text += f"{status} **#{row['id']}** | 📦 `{row['product']}`\n"
        text += f"   ⏰ `{row['expiry']}` | 📱 {row['quantity'] or '∞'} máy\n"
        text += f"   🏷 `{row['key_short']}...`\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /tokens (Admin xem danh sách token)
# =====================================================================

@admin_only
async def cmd_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/tokens - Danh sách API tokens."""
    tokens = token_manager.list_tokens()
    
    if not tokens:
        await update.message.reply_text("📭 Chưa có token nào.")
        return
    
    text = "🔑 **DANH SÁCH API TOKENS:**\n\n"
    for tok in tokens[:20]:
        status = "🟢" if tok['is_active'] else "🔴"
        text += f"{status} **ID:{tok['id']}** | {tok['token_name']}\n"
        text += f"   👤 {tok['username']} ({tok['user_id']})\n"
        text += f"   📱 Limit: {tok['device_limit']} | 📞 Used: {tok['requests_used']}/{tok['request_limit']}\n"
        text += f"   📅 {tok['created_at'][:10]}\n\n"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# =====================================================================
# TELEGRAM COMMAND: /broadcast (Admin gửi thông báo)
# =====================================================================

@admin_only
async def cmd_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/broadcast <message> - Gửi thông báo đến tất cả users."""
    args = update.message.text.split(maxsplit=1)
    
    if len(args) < 2:
        await update.message.reply_text("⚠️ `/broadcast <nội_dung>`", parse_mode=ParseMode.MARKDOWN)
        return
    
    message = args[1]
    users = db_manager.fetchall("SELECT DISTINCT user_id FROM telegram_users")
    
    success = 0
    failed = 0
    
    status_msg = await update.message.reply_text(f"📤 Đang gửi đến {len(users)} người dùng...")
    
    for user in users:
        try:
            await context.bot.send_message(
                chat_id=user['user_id'],
                text=f"📢 **THÔNG BÁO TỪ ADMIN:**\n\n{message}",
                parse_mode=ParseMode.MARKDOWN
            )
            success += 1
        except Exception:
            failed += 1
    
    await status_msg.edit_text(
        f"✅ **GỬI XONG**\n\n"
        f"✅ Thành công: {success}\n"
        f"❌ Thất bại: {failed}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    audit_logger.log_action(
        user_id=update.effective_user.id,
        username=update.effective_user.username or update.effective_user.first_name,
        action='BROADCAST',
        details=f"Success: {success}, Failed: {failed}, Message: {message[:100]}"
    )

# =====================================================================
# TELEGRAM MESSAGE HANDLER
# =====================================================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn thường."""
    text = update.message.text.strip()
    
    # Nếu là license key (dài > 50 ký tự)
    if len(text) > 50 and not text.startswith('/'):
        await cmd_activate(update, context)
        return
    
    # Cập nhật last_interaction
    db_manager.execute(
        "UPDATE telegram_users SET last_interaction = CURRENT_TIMESTAMP WHERE user_id = ?",
        (update.effective_user.id,)
    )

# =====================================================================
# MAIN FUNCTION
# =====================================================================

async def setup_bot_commands():
    """Thiết lập commands cho bot."""
    bot_commands = [
        BotCommand("start", "Menu chính"),
        BotCommand("activate", "Kích hoạt license key"),
        BotCommand("mykeys", "Xem key đã kích hoạt"),
        BotCommand("help", "Hướng dẫn chi tiết"),
        BotCommand("info", "Thông tin server"),
        BotCommand("contact", "Liên hệ hỗ trợ"),
        BotCommand("admin", "Menu quản trị (admin)"),
        BotCommand("key", "Tạo key nhanh (admin)"),
        BotCommand("keyd", "Tạo key giới hạn (admin)"),
        BotCommand("keyh", "Tạo key theo giờ (admin)"),
        BotCommand("keyvip", "Tạo key VIP (admin)"),
        BotCommand("token", "Tạo API token (admin)"),
        BotCommand("status", "Thống kê (admin)"),
        BotCommand("revoke", "Thu hồi key (admin)"),
    ]
    return bot_commands

def run_bot():
    """Khởi động Telegram Bot."""
    # Tạo application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Đăng ký handlers
    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("activate", cmd_activate))
    application.add_handler(CommandHandler("mykeys", cmd_mykeys))
    application.add_handler(CommandHandler("info", cmd_info))
    application.add_handler(CommandHandler("contact", cmd_contact))
    
    # Admin commands
    application.add_handler(CommandHandler("admin", cmd_admin))
    application.add_handler(CommandHandler("key", cmd_key))
    application.add_handler(CommandHandler("keyd", cmd_keyd))
    application.add_handler(CommandHandler("keyh", cmd_keyh))
    application.add_handler(CommandHandler("keyvip", cmd_keyvip))
    application.add_handler(CommandHandler("token", cmd_token))
    application.add_handler(CommandHandler("status", cmd_status))
    application.add_handler(CommandHandler("revoke", cmd_revoke))
    application.add_handler(CommandHandler("keys", cmd_keys))
    application.add_handler(CommandHandler("tokens", cmd_tokens))
    application.add_handler(CommandHandler("broadcast", cmd_broadcast))
    
    # Message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log.info(f"🤖 Telegram Bot started. Server: {SERVER_URL}")
    
    # Chạy polling
    application.run_polling(all_updates=True, drop_pending_updates=True)

def main():
    """Hàm chính."""
    log.info("=" * 60)
    log.info("🔐 iOS LICENSE SYSTEM v4.0 - STARTING")
    log.info("=" * 60)
    
    # Khởi tạo database
    log.info("Initializing database...")
    init_database()
    
    # Tạo backup tự động nếu bật
    if FEATURES.get('ENABLE_AUTO_BACKUP', True):
        try:
            db_manager.backup()
        except Exception as e:
            log.warning(f"Auto backup failed: {e}")
    
    # Hiển thị thông tin server
    log.info(f"🌐 Server URL: {SERVER_URL}")
    log.info(f"🏷 Key Prefix: {crypto.prefix}")
    log.info(f"🔐 Public Key Fingerprint: {crypto.public_key_fingerprint}")
    log.info(f"📡 API Port: {API_PORT}")
    
    # Khởi động Telegram Bot trong thread riêng
    bot_thread = threading.Thread(target=run_bot, daemon=True, name="TelegramBot")
    bot_thread.start()
    log.info("🤖 Telegram Bot thread started")
    
    # Khởi động Flask API server
    log.info(f"🌐 Flask API server starting on 0.0.0.0:{API_PORT}")
    app.run(
        host="0.0.0.0",
        port=API_PORT,
        debug=False,
        use_reloader=False,
        threaded=True
    )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.info("Server shutting down...")
    except Exception as e:
        log.critical(f"Fatal error: {e}")
        sys.exit(1)
