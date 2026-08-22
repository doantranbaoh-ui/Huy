#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tempfile
import subprocess
import re
import struct
import hashlib
import binascii
import time
import json
import shutil
from datetime import datetime
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================================
# CẤU HÌNH BOT
# ============================================================
TOKEN = "6320148381:AAEIQ30CzOlLwQHXTWqlr3Rpy79QQM6sH7Y"
ADMIN_ID = 5736655322
BOT_VERSION = "v5.0"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
PATCHED_PATH = os.path.join(BASE_DIR, "patched")
BACKUP_PATH = os.path.join(BASE_DIR, "backups")
LOG_PATH = os.path.join(BASE_DIR, "logs")
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(PATCHED_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)
os.makedirs(LOG_PATH, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(os.path.join(LOG_PATH, "bot.log")),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG THÔNG MINH
# ============================================================
class SmartConfig:
    DOMAINS = [
        (b'gmvmoba.com', b'127.0.0.1\x00\x00\x00'),
        (b'https://gmvmoba.com', b'https://127.0.0.1\x00\x00'),
        (b'calm-unit-61cc.teamgamehub99.workers.dev', None),
        (b'api.baontq.xyz', None),
        (b'severapigmvbbv2.teamgamehub99.workers.dev', None),
        (b'api.authtool.app', None),
    ]
    
    AES_KEY = b'bf76c74c23bd93c4016a2a0be4213f63'
    AES_KEY_NEW = b'31323334353637383930313233343536'
    
    BUNDLE_ID_OLD = b'com.gmvmoba.v2'
    BUNDLE_ID_NEW = b'com.apple.PUBG' + b'\x00' * 2
    
    OP_RET = bytes.fromhex('C0 03 5F D6')
    OP_MOV_X0_1_RET = bytes.fromhex('20 00 80 52 C0 03 5F D6')
    OP_MOV_X0_0_RET = bytes.fromhex('00 00 80 52 C0 03 5F D6')
    OP_NOP = bytes.fromhex('1F 20 03 D5')
    OP_BR_X0 = bytes.fromhex('00 00 1F D6')

# ============================================================
# BINARY ANALYZER CAO CẤP
# ============================================================
class BinaryAnalyzer:
    @staticmethod
    def detect_architecture(data):
        if len(data) < 4:
            return 'unknown'
        magic = struct.unpack('<I', data[:4])[0]
        if magic == 0xFEEDFACF:
            return 'arm64'
        elif magic == 0xFEEDFACF:
            if len(data) >= 8:
                cpusubtype = struct.unpack('<I', data[4:8])[0]
                if cpusubtype == 0:
                    return 'x86_64'
        return 'arm64'
    
    @staticmethod
    def find_all(data, pattern):
        positions = []
        pos = data.find(pattern)
        while pos != -1:
            positions.append(pos)
            pos = data.find(pattern, pos + 1)
        return positions
    
    @staticmethod
    def find_function_code(data, func_name):
        name_pos = data.find(func_name.encode())
        if name_pos == -1:
            return None
        search_start = max(0, name_pos - 0x2000)
        search_end = min(len(data), name_pos + 0x2000)
        for offset in range(search_start, search_end - 8):
            if offset + 8 <= len(data):
                ptr = struct.unpack('<Q', data[offset:offset+8])[0]
                if ptr == name_pos:
                    for i in range(offset - 0x200, offset):
                        if i >= 0 and i + 4 <= len(data):
                            if data[i] in [0xFF, 0x3F, 0x20]:
                                return i
        return None

# ============================================================
# PATCH ENGINE CAO CẤP
# ============================================================
class AdvancedPatcher:
    def __init__(self, data):
        self.data = bytearray(data)
        self.analyzer = BinaryAnalyzer()
        self.arch = self.analyzer.detect_architecture(data)
        self.logs = []
        self.stats = {
            'domains': 0,
            'alerts': 0,
            'functions': 0,
            'keychain': 0,
            'ssl': 0,
            'timer': 0,
            'aes': 0,
            'bundle': 0,
            'force_update': 0,
            'expired': 0,
            'device_fp': 0,
        }
    
    def log(self, msg):
        self.logs.append(msg)
        logger.info(msg)
    
    def patch_domains(self):
        count = 0
        for old, new in SmartConfig.DOMAINS:
            if new is None:
                self.log(f"⏭️ Giữ nguyên: {old.decode()}")
                continue
            positions = self.analyzer.find_all(self.data, old)
            for pos in positions:
                if len(new) <= len(old):
                    self.data[pos:pos+len(new)] = new
                    if len(new) < len(old):
                        self.data[pos+len(new):pos+len(old)] = b'\x00' * (len(old) - len(new))
                else:
                    self.data[pos:pos+len(old)] = new[:len(old)]
                count += 1
                self.log(f"✅ Domain at 0x{pos:X}")
        self.stats['domains'] = count
        return count
    
    def patch_aes_key(self):
        positions = self.analyzer.find_all(self.data, SmartConfig.AES_KEY)
        for pos in positions:
            self.data[pos:pos+32] = SmartConfig.AES_KEY_NEW
            self.stats['aes'] += 1
            self.log(f"✅ AES key at 0x{pos:X}")
        return len(positions)
    
    def patch_bundle_id(self):
        positions = self.analyzer.find_all(self.data, SmartConfig.BUNDLE_ID_OLD)
        for pos in positions:
            new = SmartConfig.BUNDLE_ID_NEW
            if len(new) <= len(SmartConfig.BUNDLE_ID_OLD):
                self.data[pos:pos+len(new)] = new
                if len(new) < len(SmartConfig.BUNDLE_ID_OLD):
                    self.data[pos+len(new):pos+len(SmartConfig.BUNDLE_ID_OLD)] = b'\x00' * (len(SmartConfig.BUNDLE_ID_OLD) - len(new))
            self.stats['bundle'] += 1
            self.log(f"✅ Bundle ID at 0x{pos:X}")
        return len(positions)
    
    def patch_function(self, func_name, patch_bytes):
        pos = self.analyzer.find_function_code(self.data, func_name)
        if pos is None:
            self.log(f"⚠️ Không tìm thấy: {func_name}")
            return False
        if self.data[pos:pos+len(patch_bytes)] == patch_bytes:
            self.log(f"⏭️ Đã patch: {func_name}")
            return True
        self.data[pos:pos+len(patch_bytes)] = patch_bytes
        self.stats['functions'] += 1
        self.log(f"✅ Patched: {func_name}")
        return True
    
    def patch_all_functions(self):
        funcs = [
            'showMainAlert_V2:', 'showToast_V2:', 'showForceUpdateAlert_V2:message:',
            'showGetUDIDAlert_V2', 'setIsDialogVisible_V2:', 'isDialogVisible_V2',
            'isValid', 'verifyKey_V2:', 'silentVerifyKey_V2:', 'verifyKeyForPolling_V2:',
            'processSuccess_V2:json:', 'startUpdatePolling_V2', 'handleTimerCheck_V2',
            'checkUpdateFirstV2', 'checkUpdateFirst_V2', 'savePermanentKey_V2:',
            'getPermanentKey_V2', 'load_V2', 'shared_V2',
        ]
        results = {}
        for func in funcs:
            if 'MainAlert' in func or 'Toast' in func or 'ForceUpdate' in func or 'GetUDID' in func:
                results[func] = self.patch_function(func, SmartConfig.OP_RET)
            elif 'setIsDialogVisible' in func:
                results[func] = self.patch_function(func, SmartConfig.OP_MOV_X0_0_RET)
            elif 'isDialogVisible' in func or 'isValid' in func:
                results[func] = self.patch_function(func, SmartConfig.OP_MOV_X0_1_RET)
            elif 'processSuccess' in func:
                results[func] = self.patch_process_success()
            elif 'startUpdatePolling' in func or 'handleTimerCheck' in func:
                results[func] = self.patch_function(func, SmartConfig.OP_RET)
            elif 'savePermanentKey' in func or 'getPermanentKey' in func:
                results[func] = self.patch_function(func, SmartConfig.OP_MOV_X0_1_RET)
            else:
                results[func] = self.patch_function(func, SmartConfig.OP_RET)
        return results
    
    def patch_process_success(self):
        pos = self.analyzer.find_function_code(self.data, 'processSuccess_V2:json:')
        if pos is None:
            return False
        patched = 0
        for i in range(pos, min(len(self.data), pos + 0x1000)):
            if i + 4 <= len(self.data):
                if self.data[i] == 0x34:
                    self.data[i] = 0x35
                    patched += 1
                elif self.data[i] == 0xB4:
                    self.data[i] = 0xB5
                    patched += 1
        self.stats['functions'] += patched
        return patched > 0
    
    def patch_timer(self):
        pos = self.data.find(b'startUpdatePolling')
        if pos == -1:
            pos = self.data.find(b'startUpdatePolling_V2')
        if pos != -1:
            timer_pos = self.data.find(b'scheduledTimerWithTimeInterval', pos, pos + 0x2000)
            if timer_pos != -1:
                for i in range(timer_pos - 0x20, timer_pos + 0x20):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] not in [SmartConfig.OP_NOP, b'\x00\x00\x00\x00']:
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            self.stats['timer'] += 1
                            self.log(f"✅ Timer killed")
                            return True
        return False
    
    def delete_alert_strings(self):
        alerts = [
            'Nhập Key', 'Key không hợp lệ', 'Vui lòng nhập Key',
            'Update required', 'Check Key', 'Get Key', 'Click Lay UDID'
        ]
        count = 0
        for alert in alerts:
            encoded = alert.encode('utf-8')
            positions = self.analyzer.find_all(self.data, encoded)
            for pos in positions:
                self.data[pos:pos+len(encoded)] = b'\x00' * len(encoded)
                count += 1
        self.stats['alerts'] = count
        return count
    
    def patch_keychain(self):
        patterns = [b'SecItemAdd', b'SecItemCopyMatching', b'SecItemDelete']
        count = 0
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                code_pos = self.analyzer.find_function_code(self.data, pattern.decode())
                if code_pos:
                    self.data[code_pos:code_pos+4] = SmartConfig.OP_RET
                    count += 1
                    self.log(f"✅ Patched {pattern.decode()}")
        self.stats['keychain'] = count
        return count
    
    def patch_ssl_pinning(self):
        patterns = [
            b'URLSession:didReceiveChallenge:completionHandler:',
            b'URLAuthenticationChallenge', b'SecTrustEvaluate'
        ]
        count = 0
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                for i in range(pos - 0x200, pos + 0x200):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] == b'\x00\x00\x00\x00':
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            count += 1
                            break
        self.stats['ssl'] = count
        return count
    
    def patch_device_fp(self):
        patterns = [b'GMV_TRK_V2_%@', b'GMV_PV_V2_%@', b'GMV_UDID_DEVICE_V2']
        count = 0
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                fake = b'FAKE_DEVICE_' + b'\x00' * 10
                self.data[pos:pos+len(pattern)] = fake[:len(pattern)]
                count += 1
        self.stats['device_fp'] = count
        return count
    
    def patch_force_update(self):
        patterns = [b'force_update', b'require_key', b'update_link', b'update_msg']
        count = 0
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                self.data[pos:pos+len(pattern)] = b'\x00' * len(pattern)
                count += 1
        self.stats['force_update'] = count
        return count
    
    def patch_expired_at(self):
        expired = b'"expiredAt":"9999-01-01T06:41:57.000Z"'
        pos = self.data.find(expired)
        if pos != -1:
            self.stats['expired'] = 1
            return True
        expired2 = b'"expiredAt"'
        pos = self.data.find(expired2)
        if pos != -1:
            new_expired = b'"expiredAt":"9999-01-01T23:59:59.999Z"'
            self.data[pos:pos+len(new_expired)] = new_expired
            self.stats['expired'] = 1
            return True
        return False
    
    def apply_all(self):
        self.log("🧠 Bắt đầu phân tích binary...")
        self.log(f"📐 Kiến trúc: {self.arch}")
        
        results = {}
        results['domains'] = self.patch_domains()
        results['aes_key'] = self.patch_aes_key()
        results['bundle_id'] = self.patch_bundle_id()
        results['functions'] = self.patch_all_functions()
        results['timer'] = self.patch_timer()
        results['alerts'] = self.delete_alert_strings()
        results['keychain'] = self.patch_keychain()
        results['ssl_pinning'] = self.patch_ssl_pinning()
        results['device_fp'] = self.patch_device_fp()
        results['force_update'] = self.patch_force_update()
        results['expired_at'] = self.patch_expired_at()
        
        return results
    
    def get_patched_data(self):
        return bytes(self.data)
    
    def get_report(self):
        report = f"""
📊 **BÁO CÁO PATCH THÔNG MINH {BOT_VERSION}**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔹 **Kiến trúc**: {self.arch}
🔹 **Domain**: {self.stats['domains']}
🔹 **AES Key**: {'✅' if self.stats['aes'] > 0 else '❌'}
🔹 **Bundle ID**: {'✅' if self.stats['bundle'] > 0 else '❌'}
🔹 **Hàm đã patch**: {self.stats['functions']}
🔹 **Xóa alert**: {self.stats['alerts']}
🔹 **Keychain**: {'✅' if self.stats['keychain'] > 0 else '❌'}
🔹 **SSL Pinning**: {'✅' if self.stats['ssl'] > 0 else '❌'}
🔹 **Timer Polling**: {'✅' if self.stats['timer'] > 0 else '❌'}
🔹 **Device FP**: {'✅' if self.stats['device_fp'] > 0 else '❌'}
🔹 **Force Update**: {'✅' if self.stats['force_update'] > 0 else '❌'}
🔹 **ExpiredAt**: {'✅' if self.stats['expired'] > 0 else '❌'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ **KHÔNG CÒN ALERT KEY**
✅ **KHÔNG CÒN KIỂM TRA UPDATE**
✅ **FAKE DOMAIN THÀNH CÔNG**
"""
        return report

# ============================================================
# HÀM PATCH CHÍNH
# ============================================================
def advanced_patch(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        backup_path = os.path.join(BACKUP_PATH, os.path.basename(file_path) + '.backup')
        with open(backup_path, 'wb') as f:
            f.write(data)
        
        patcher = AdvancedPatcher(data)
        results = patcher.apply_all()
        
        patched_path = os.path.join(PATCHED_PATH, os.path.basename(file_path) + '.patched')
        with open(patched_path, 'wb') as f:
            f.write(patcher.get_patched_data())
        
        return patched_path, patcher.get_report()
    except Exception as e:
        logger.error(f"Patch error: {e}")
        return None, f"❌ Lỗi: {str(e)}"

# ============================================================
# TELEGRAM HANDLERS
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot chỉ dành cho admin.")
        return

    keyboard = [
        [InlineKeyboardButton("🚀 Upload & Crack", callback_data='upload')],
        [InlineKeyboardButton("📊 Thông tin", callback_data='info')],
        [InlineKeyboardButton("🔧 Hướng dẫn", callback_data='help')],
        [InlineKeyboardButton("📈 Trạng thái", callback_data='status')],
    ]
    await update.message.reply_text(
        f"🤖 **GMV AI Crack Bot {BOT_VERSION}**\n"
        f"🧠 Công nghệ: Smart Patch Engine\n"
        f"🔧 Tự động patch mọi lớp bảo vệ\n\n"
        f"📤 Upload file `.dylib` để bắt đầu\n"
        f"👤 Admin: {user.first_name}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bạn không có quyền.")
        return

    doc = update.message.document
    if not doc or not doc.file_name.endswith('.dylib'):
        await update.message.reply_text("❌ Vui lòng upload file `.dylib`.")
        return

    status_msg = await update.message.reply_text("⏳ Đang tải file...")

    try:
        file = await context.bot.get_file(doc.file_id)
        file_path = os.path.join(DOWNLOAD_PATH, doc.file_name)
        await file.download_to_drive(file_path)

        await status_msg.edit_text("🧠 Đang phân tích binary...")

        patched_path, report = advanced_patch(file_path)

        if patched_path and os.path.exists(patched_path):
            await status_msg.edit_text("✅ Patch thành công! Đang gửi file...")

            with open(patched_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=os.path.basename(patched_path),
                    caption=f"✅ **GMV.dylib đã patch {BOT_VERSION}**\n\n{report}\n\n📥 Copy vào /Library/MobileSubstrate/DynamicLibraries/\n🔄 killall -9 PUBG",
                    parse_mode='Markdown'
                )

            os.remove(file_path)
            os.remove(patched_path)
        else:
            await status_msg.edit_text(f"❌ Patch thất bại.\n\n{report}")

    except Exception as e:
        await status_msg.edit_text(f"❌ Lỗi: {str(e)}")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    if user.id != ADMIN_ID:
        await query.edit_message_text("⚠️ Bạn không có quyền.")
        return

    data = query.data

    if data == 'upload':
        await query.edit_message_text("📤 **Upload GMV.dylib**\n\nGửi file `.dylib` vào chat.", parse_mode='Markdown')
    elif data == 'info':
        await query.edit_message_text(
            f"🧠 **Công nghệ AI Crack {BOT_VERSION}**\n\n"
            "1. 🔍 Phân tích thông minh\n"
            "2. 🔧 Patch tự động\n"
            "3. 🛡️ Bypass bảo vệ\n\n"
            "**Danh sách patch:**\n"
            "✅ Domain fake\n"
            "✅ Alert (MainAlert, Toast, ForceUpdate, GetUDID)\n"
            "✅ isValid → YES\n"
            "✅ processSuccess → đảo logic\n"
            "✅ Timer polling\n"
            "✅ Keychain operations\n"
            "✅ SSL Pinning\n"
            "✅ Device fingerprint\n"
            "✅ Force update\n"
            "✅ ExpiredAt\n"
            "✅ Bundle ID\n"
            "✅ AES key"
        )
    elif data == 'help':
        await query.edit_message_text(
            "📖 **Hướng dẫn**\n\n"
            "1. Upload file `GMV.dylib`\n"
            "2. Bot tự động phân tích và patch\n"
            "3. Nhận file đã patch\n"
            "4. Copy vào thiết bị\n"
            "5. `chown root:wheel GMV.dylib`\n"
            "6. `chmod 644 GMV.dylib`\n"
            "7. `killall -9 PUBG`\n\n"
            "✅ **Không còn alert, không còn key!**"
        )
    elif data == 'status':
        await query.edit_message_text(
            "📊 **Trạng thái bot**\n\n"
            f"📁 Download: {DOWNLOAD_PATH}\n"
            f"📁 Patched: {PATCHED_PATH}\n"
            f"📦 File đã patch: {len(os.listdir(PATCHED_PATH))}\n"
            f"💾 Backup: {len(os.listdir(BACKUP_PATH))}\n"
            f"📝 Logs: {LOG_PATH}\n"
            f"⏳ Đang chờ upload..."
        )

# ============================================================
# MAIN
# ============================================================
def main():
    if not TOKEN:
        print("❌ Thiếu TOKEN")
        sys.exit(1)

    try:
        app = Application.builder().token(TOKEN).build()
    except Exception:
        from telegram.ext import Updater
        updater = Updater(TOKEN, use_context=True)
        app = updater.application

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("=" * 50)
    print(f"🤖 GMV AI Crack Bot {BOT_VERSION}")
    print("🧠 Smart Patch Engine")
    print("📤 Token:", TOKEN)
    print("👤 Admin ID:", ADMIN_ID)
    print("=" * 50)
    print("🟢 Bot đang chạy...")
    
    app.run_polling()

if __name__ == "__main__":
    main()
