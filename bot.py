# bot.py - Auto Crack GMV Telegram Bot (Full Version)
# Chạy: python3 bot.py

import os
import re
import logging
import tempfile
import shutil
import json
import sqlite3
import hashlib
import binascii
from datetime import datetime
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes
)

# ============================================
# CẤU HÌNH - THAY TOKEN CỦA BẠN VÀO ĐÂY
# ============================================

TOKEN = "6320148381:AAFSxnyeQePiFVf1qqaqK7h_XRLMMSlD8kw"  # <--- THAY TOKEN CỦA BẠN
ADMIN_ID = 5736655322  # <--- THAY ID ADMIN CỦA BẠN

MAX_FILE_SIZE = 100 * 1024 * 1024
ALLOWED_EXTENSIONS = ['.dylib', '.ipa', '.deb', '.framework']

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# DATABASE
# ============================================

class Database:
    def __init__(self, db_path="crack_data.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (user_id INTEGER PRIMARY KEY, username TEXT, 
                      first_seen TEXT, last_active TEXT, total_cracks INTEGER DEFAULT 0)''')
        c.execute('''CREATE TABLE IF NOT EXISTS cracks
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      user_id INTEGER, filename TEXT, 
                      original_hash TEXT, patched_hash TEXT,
                      crack_time TEXT, status TEXT, patch_count INTEGER)''')
        conn.commit()
        conn.close()
    
    def add_user(self, user_id, username):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''INSERT OR IGNORE INTO users (user_id, username, first_seen, last_active)
                     VALUES (?, ?, ?, ?)''', (user_id, username, now, now))
        c.execute('''UPDATE users SET last_active=?, username=? WHERE user_id=?''', 
                  (now, username, user_id))
        conn.commit()
        conn.close()
    
    def add_crack(self, user_id, filename, original_hash, patched_hash, patch_count):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.now().isoformat()
        c.execute('''INSERT INTO cracks (user_id, filename, original_hash, patched_hash, crack_time, status, patch_count)
                     VALUES (?, ?, ?, ?, ?, ?, ?)''', 
                  (user_id, filename, original_hash, patched_hash, now, "success", patch_count))
        c.execute('''UPDATE users SET total_cracks = total_cracks + 1 WHERE user_id = ?''', (user_id,))
        conn.commit()
        conn.close()
    
    def get_stats(self, user_id=None):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if user_id:
            c.execute('SELECT total_cracks FROM users WHERE user_id = ?', (user_id,))
            result = c.fetchone()
            conn.close()
            return result[0] if result else 0
        else:
            c.execute('SELECT COUNT(*) FROM users')
            users = c.fetchone()[0]
            c.execute('SELECT COUNT(*) FROM cracks')
            cracks = c.fetchone()[0]
            conn.close()
            return users, cracks

db = Database()

# ============================================
# PATCH DEFINITIONS - TỪ FILE libloaber.txt
# ============================================

@dataclass
class CrackPatch:
    name: str
    find_hex: str
    replace_hex: str
    description: str
    category: str = "security"
    enabled: bool = True

CRACK_PATCHES = [
    # ===== SECURITY - Bỏ qua key =====
    CrackPatch("verifyKey", "FF8300D1FD7B01A9", "20008052C0035FD6", 
               "🚫 Bỏ qua kiểm tra Key", "security"),
    CrackPatch("verifySignature", "94000000", "20008052C0035FD6", 
               "✅ Luôn trả về TRUE", "security"),
    
    # ===== UI - Vô hiệu hóa alert =====
    CrackPatch("showMainAlert", "1F2003D5", "20008052C0035FD6", 
               "🚫 Vô hiệu hóa Alert chính", "ui"),
    CrackPatch("showToast", "1F2003D5", "20008052C0035FD6", 
               "🚫 Vô hiệu hóa Toast", "ui"),
    
    # ===== NETWORK - Bỏ qua kiểm tra =====
    CrackPatch("require_key", "726571756972655F6B6579", "00000000000000000000000000", 
               "🚫 Bỏ qua require_key", "network"),
    CrackPatch("force_update", "666F7263655F757064617465", "0000000000000000000000000000", 
               "🚫 Bỏ qua force_update", "network"),
    CrackPatch("unix_time", "756E6978", "000000000000", 
               "⏰ Vô hiệu hóa Unix Time", "network"),
    CrackPatch("expiredAt", "657870697265644174", "00000000000000000000", 
               "⏰ Bỏ qua expiredAt", "network"),
    
    # ===== SYSTEM - Thay ID =====
    CrackPatch("bundle_id", "636F6D2E676D766D6F62612E7632", "636F6D2E6578616D706C652E617070", 
               "🔄 Thay Bundle ID", "system"),
    CrackPatch("gmvmoba_url", "676D766D6F62612E636F6D", "3132372E302E302E31", 
               "🏠 Chuyển URL về localhost", "system"),
    CrackPatch("gmvmoba_url2", "676D766D6F62612E636F6D2F636F6E6E6563747632", "3132372E302E302E312F636F6E6E656374", 
               "🏠 Chuyển connectv2", "system"),
]

# ============================================
# CORE CRACK ENGINE
# ============================================

class CrackEngine:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def crack_file(self, file_path: str) -> Tuple[List[str], int, str, str]:
        """Crack file với danh sách patch"""
        try:
            with open(file_path, 'rb') as f:
                data = bytearray(f.read())
            
            original_data = bytes(data)
            results = []
            total_changes = 0
            patches_applied = 0
            
            for patch in CRACK_PATCHES:
                if not patch.enabled:
                    continue
                
                try:
                    find_bytes = bytes.fromhex(patch.find_hex)
                    replace_bytes = bytes.fromhex(patch.replace_hex)
                except ValueError as e:
                    results.append(f"❌ {patch.name}: Hex không hợp lệ")
                    continue
                
                count = 0
                pos = data.find(find_bytes)
                while pos != -1:
                    if len(replace_bytes) <= len(data) - pos:
                        data[pos:pos+len(find_bytes)] = replace_bytes
                        count += 1
                        total_changes += len(find_bytes)
                    pos = data.find(find_bytes, pos + len(replace_bytes))
                
                if count > 0:
                    results.append(f"✅ {patch.name}: {patch.description} ({count} lần)")
                    patches_applied += 1
                else:
                    results.append(f"⚠️ {patch.name}: Không tìm thấy")
            
            # Lưu file
            with open(file_path, 'wb') as f:
                f.write(data)
            
            original_hash = hashlib.sha256(original_data).hexdigest()[:8]
            patched_hash = hashlib.sha256(data).hexdigest()[:8]
            
            return results, total_changes, original_hash, patched_hash, patches_applied
            
        except Exception as e:
            self.logger.error(f"Crack error: {str(e)}")
            return [f"❌ Lỗi crack: {str(e)}"], 0, "", "", 0
    
    def analyze_file(self, file_path: str) -> Dict:
        """Phân tích file GMV.dylib"""
        info = {
            "size": os.path.getsize(file_path),
            "urls": [],
            "bundle_ids": [],
            "is_encrypted": False,
            "patches_found": [],
            "version": "Unknown"
        }
        
        try:
            with open(file_path, 'rb') as f:
                data = f.read()
            
            # Tìm URL
            url_pattern = rb'https?://[a-zA-Z0-9.-]+'
            urls = re.findall(url_pattern, data)
            info["urls"] = [u.decode('utf-8', errors='ignore') for u in urls[:10]]
            
            # Tìm bundle ID
            bundle_pattern = rb'com\.[a-zA-Z0-9.-]+'
            bundles = re.findall(bundle_pattern, data)
            info["bundle_ids"] = [b.decode('utf-8', errors='ignore') for b in bundles[:5]]
            
            # Kiểm tra mã hóa
            if b'encrypt' in data.lower() or b'cipher' in data.lower():
                info["is_encrypted"] = True
                
        except Exception as e:
            self.logger.error(f"Analyze error: {str(e)}")
        
        return info

cracker = CrackEngine()

# ============================================
# BOT HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.add_user(user.id, user.username or "Unknown")
    
    keyboard = [
        [InlineKeyboardButton("🔓 Crack File", callback_data="crack")],
        [InlineKeyboardButton("🔍 Phân tích", callback_data="analyze")],
        [InlineKeyboardButton("📋 Patch List", callback_data="list")],
        [InlineKeyboardButton("📊 Thống kê", callback_data="stats")],
        [InlineKeyboardButton("ℹ️ Hướng dẫn", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🔓 **GMV Auto Crack Bot v3.0**\n\n"
        f"👋 Chào {user.first_name}!\n"
        f"📦 Bot tự động crack file GMV.dylib\n\n"
        f"📤 **Upload file** lên để crack\n"
        f"📋 Áp dụng {len([p for p in CRACK_PATCHES if p.enabled])} patch\n\n"
        f"⚠️ *Chỉ dùng cho mục đích nghiên cứu!*",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    document = update.message.document
    
    if not document:
        await update.message.reply_text("❌ Vui lòng gửi file .dylib")
        return
    
    filename = document.file_name or ""
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        await update.message.reply_text(f"❌ Chỉ hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}")
        return
    
    if document.file_size and document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(f"❌ File quá lớn ({document.file_size // 1024 // 1024}MB)")
        return
    
    status_msg = await update.message.reply_text(
        f"🔓 Đang crack: `{filename}`\n⏳ Vui lòng chờ...",
        parse_mode="Markdown"
    )
    
    try:
        file = await document.get_file()
        
        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, filename)
            await file.download_to_drive(input_path)
            
            # Phân tích
            analysis = cracker.analyze_file(input_path)
            
            # Crack
            results, changes, orig_hash, patch_hash, applied = cracker.crack_file(input_path)
            
            # Lưu DB
            db.add_crack(user.id, filename, orig_hash, patch_hash, applied)
            
            # Output
            output_path = os.path.join(tmpdir, f"cracked_{filename}")
            shutil.copy2(input_path, output_path)
            
            # Kết quả
            result_text = f"✅ **CRACK HOÀN TẤT!**\n\n"
            result_text += f"📁 File: `{filename}`\n"
            result_text += f"🔢 Hash: `{orig_hash}` → `{patch_hash}`\n"
            result_text += f"📝 Patch áp dụng: {applied}/{len([p for p in CRACK_PATCHES if p.enabled])}\n"
            result_text += f"🔧 Bytes thay đổi: {changes}\n\n"
            result_text += "\n".join(results)
            
            if not results:
                result_text += "\n\n⚠️ Không có patch nào được áp dụng!"
            
            await status_msg.edit_text(result_text, parse_mode="Markdown")
            
            # Gửi file
            with open(output_path, 'rb') as f:
                await update.message.reply_document(
                    document=f,
                    filename=f"cracked_{filename}",
                    caption=f"🔓 File đã crack!\n🔢 Hash: {patch_hash}"
                )
            
            # Gửi thông tin
            if analysis["urls"]:
                url_text = "🌐 **URL tìm thấy:**\n" + "\n".join(f"• {u}" for u in analysis["urls"][:5])
                await update.message.reply_text(url_text, parse_mode="Markdown")
                
    except Exception as e:
        await status_msg.edit_text(f"❌ Lỗi: {str(e)}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "crack":
        await query.edit_message_text(
            "🔓 **Crack File**\n\n"
            "Gửi file GMV.dylib hoặc IPA lên đây.\n"
            f"📦 Hỗ trợ: {', '.join(ALLOWED_EXTENSIONS)}\n"
            f"📊 Áp dụng {len([p for p in CRACK_PATCHES if p.enabled])} patch\n\n"
            "Bot sẽ tự động crack tất cả các mục cần thiết.",
            parse_mode="Markdown"
        )
    
    elif data == "analyze":
        await query.edit_message_text(
            "🔍 **Phân tích File**\n\n"
            "Gửi file lên để phân tích.\n"
            "Bot sẽ hiển thị:\n"
            "• Bundle ID\n"
            "• URLs\n"
            "• Trạng thái mã hóa",
            parse_mode="Markdown"
        )
    
    elif data == "list":
        text = "📋 **DANH SÁCH PATCH**\n\n"
        for i, patch in enumerate(CRACK_PATCHES, 1):
            status = "✅" if patch.enabled else "❌"
            text += f"{i}. {status} **{patch.name}**\n"
            text += f"   Tìm: `{patch.find_hex}`\n"
            text += f"   Thay: `{patch.replace_hex}`\n"
            text += f"   → {patch.description}\n\n"
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "stats":
        users, cracks = db.get_stats()
        user_cracks = db.get_stats(query.from_user.id)
        
        text = f"📊 **THỐNG KÊ**\n\n"
        text += f"👥 Tổng users: {users}\n"
        text += f"📦 Tổng cracks: {cracks}\n"
        text += f"👤 Bạn đã crack: {user_cracks} lần\n\n"
        text += f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "help":
        text = """
📖 **HƯỚNG DẪN CRACK GMV**

**1️⃣ Upload file**
Gửi file GMV.dylib lên bot

**2️⃣ Crack tự động**
Bot sẽ patch tất cả các mục cần thiết

**3️⃣ Tải xuống**
Nhận file đã crack về máy

**📋 Patch áp dụng:**
• Bỏ qua Key ✅
• Vô hiệu hóa Alert ✅
• Bỏ qua require_key ✅
• Chuyển URL localhost ✅
• Thay Bundle ID ✅

**⚠️ Lưu ý:**
• Backup file gốc
• Chỉ dùng nghiên cứu
"""
        keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=reply_markup)
    
    elif data == "back":
        await start(update, context)

# ============================================
# MAIN
# ============================================

def main():
    if not TOKEN or TOKEN == "6320148381:AAFSxnyeQePiFVf1qqaqK7h_XRLMMSlD8kw":
        print("❌ Vui lòng set TOKEN!")
        return
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    print("🔓 GMV Auto Crack Bot v3.0 đang chạy...")
    print(f"📦 Số patch: {len([p for p in CRACK_PATCHES if p.enabled])}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    
    app.run_polling()

if __name__ == "__main__":
    main()
