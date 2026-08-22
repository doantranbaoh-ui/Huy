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
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

# ============================================================
# CẤU HÌNH
# ============================================================
TOKEN = "6320148381:AAEIQ30CzOlLwQHXTWqlr3Rpy79QQM6sH7Y"
ADMIN_ID = 5736655322

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
PATCHED_PATH = os.path.join(BASE_DIR, "patched")
BACKUP_PATH = os.path.join(BASE_DIR, "backups")

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(PATCHED_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG
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
    
    OP_RET = bytes.fromhex('C0 03 5F D6')
    OP_MOV_X0_1_RET = bytes.fromhex('20 00 80 52 C0 03 5F D6')
    OP_MOV_X0_0_RET = bytes.fromhex('00 00 80 52 C0 03 5F D6')
    OP_NOP = bytes.fromhex('1F 20 03 D5')
    
    FUNCTIONS_TO_PATCH = [
        'showMainAlert_V2:',
        'showToast_V2:',
        'showForceUpdateAlert_V2:message:',
        'showGetUDIDAlert_V2',
        'setIsDialogVisible_V2:',
        'isValid',
        'verifyKey_V2:',
        'silentVerifyKey_V2:',
        'verifyKeyForPolling_V2:',
        'processSuccess_V2:json:',
        'startUpdatePolling_V2',
        'handleTimerCheck_V2',
        'checkUpdateFirstV2',
        'checkUpdateFirst_V2',
    ]

# ============================================================
# BINARY ANALYZER
# ============================================================
class BinaryAnalyzer:
    @staticmethod
    def find_all_occurrences(data, pattern):
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
        search_start = max(0, name_pos - 0x1000)
        search_end = min(len(data), name_pos + 0x1000)
        for offset in range(search_start, search_end - 8):
            if offset + 8 <= len(data):
                ptr = struct.unpack('<Q', data[offset:offset+8])[0]
                if ptr == name_pos:
                    for i in range(offset - 0x200, offset):
                        if i >= 0 and i + 4 <= len(data):
                            if data[i] in [0xFF, 0x3F, 0x20]:
                                return i
        return None
    
    @staticmethod
    def find_cbz_pattern(data):
        pos = data.find(b'processSuccess')
        if pos == -1:
            return []
        start = max(0, pos - 0x1000)
        end = min(len(data), pos + 0x1000)
        results = []
        for i in range(start, end - 4):
            if data[i] in [0x34, 0xB4]:
                results.append(i)
        return results

# ============================================================
# SMART PATCHER
# ============================================================
class SmartPatcher:
    def __init__(self, data):
        self.data = bytearray(data)
        self.analyzer = BinaryAnalyzer()
        self.patch_log = []
    
    def log(self, msg):
        self.patch_log.append(msg)
        logger.info(msg)
    
    def patch_domains(self):
        count = 0
        for old, new in SmartConfig.DOMAINS:
            if new is None:
                continue
            positions = self.analyzer.find_all_occurrences(self.data, old)
            for pos in positions:
                if len(new) <= len(old):
                    self.data[pos:pos+len(new)] = new
                    if len(new) < len(old):
                        self.data[pos+len(new):pos+len(old)] = b'\x00' * (len(old) - len(new))
                else:
                    self.data[pos:pos+len(old)] = new[:len(old)]
                count += 1
                self.log(f"✅ Domain at 0x{pos:X}")
        return count
    
    def patch_aes_key(self):
        old_key = SmartConfig.AES_KEY
        new_key = b'31323334353637383930313233343536'
        positions = self.analyzer.find_all_occurrences(self.data, old_key)
        for pos in positions:
            self.data[pos:pos+32] = new_key
            self.log(f"✅ AES key at 0x{pos:X}")
        return len(positions)
    
    def patch_function(self, func_name, patch_bytes, is_code=True):
        if is_code:
            pos = self.analyzer.find_function_code(self.data, func_name)
        else:
            pos = self.data.find(func_name.encode())
        if pos is None or pos == -1:
            self.log(f"⚠️ Không tìm thấy {func_name}")
            return False
        if self.data[pos:pos+len(patch_bytes)] == patch_bytes:
            self.log(f"⏭️ {func_name} đã patch")
            return True
        self.data[pos:pos+len(patch_bytes)] = patch_bytes
        self.log(f"✅ Patched {func_name} at 0x{pos:X}")
        return True
    
    def patch_isValid(self):
        return self.patch_function('isValid', SmartConfig.OP_MOV_X0_1_RET)
    
    def patch_showMainAlert(self):
        return self.patch_function('showMainAlert_V2:', SmartConfig.OP_RET)
    
    def patch_showToast(self):
        return self.patch_function('showToast_V2:', SmartConfig.OP_RET)
    
    def patch_showForceUpdate(self):
        return self.patch_function('showForceUpdateAlert_V2:message:', SmartConfig.OP_RET)
    
    def patch_showGetUDID(self):
        return self.patch_function('showGetUDIDAlert_V2', SmartConfig.OP_RET)
    
    def patch_setIsDialogVisible(self):
        return self.patch_function('setIsDialogVisible_V2:', SmartConfig.OP_MOV_X0_0_RET)
    
    def patch_processSuccess(self):
        positions = self.analyzer.find_cbz_pattern()
        patched = 0
        for pos in positions:
            if self.data[pos] == 0x34:
                self.data[pos] = 0x35
                patched += 1
                self.log(f"✅ cbz->cbnz at 0x{pos:X}")
            elif self.data[pos] == 0xB4:
                self.data[pos] = 0xB5
                patched += 1
                self.log(f"✅ cbz->cbnz at 0x{pos:X}")
        return patched
    
    def patch_timer(self):
        pos = self.data.find(b'startUpdatePolling')
        if pos != -1:
            timer_pos = self.data.find(b'scheduledTimerWithTimeInterval', pos, pos + 0x1000)
            if timer_pos != -1:
                for i in range(timer_pos - 0x10, timer_pos + 0x10):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] == b'\x00\x00\x00\x00':
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            self.log(f"✅ Timer killed at 0x{i:X}")
                            return True
        return False
    
    def delete_alert_strings(self):
        # ============================================================
        # SỬA LỖI: KHÔNG DÙNG b'...' VỚI UNICODE TRỰC TIẾP
        # ============================================================
        # Cách 1: Dùng chuỗi thường rồi encode
        alert_strings = [
            'Nhập Key'.encode('utf-8'),
            'Key không hợp lệ'.encode('utf-8'),
            'Vui lòng nhập Key'.encode('utf-8'),
            'Update required'.encode('utf-8'),
            'Check Key'.encode('utf-8'),
            'Get Key'.encode('utf-8'),
            'Click Lay UDID'.encode('utf-8'),
        ]
        
        # Cách 2: Dùng hex bytes trực tiếp (an toàn hơn)
        # alert_strings = [
        #     b'Nh\xe1\xba\xadp Key',          # Nhập Key
        #     b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',  # Key không hợp lệ
        #     b'Vui l\xc3\xb2ng nh\xe1\xba\xadp Key',  # Vui lòng nhập Key
        #     b'Update required',
        #     b'Check Key',
        #     b'Get Key',
        #     b'Click Lay UDID',
        # ]
        
        count = 0
        for alert in alert_strings:
            positions = self.analyzer.find_all_occurrences(self.data, alert)
            for pos in positions:
                self.data[pos:pos+len(alert)] = b'\x00' * len(alert)
                count += 1
                self.log(f"✅ Deleted alert at 0x{pos:X}")
        return count
    
    def patch_keychain_operations(self):
        pos = self.data.find(b'SecItemAdd')
        if pos != -1:
            code_pos = self.analyzer.find_function_code(self.data, 'SecItemAdd')
            if code_pos:
                self.data[code_pos:code_pos+4] = SmartConfig.OP_RET
                self.log(f"✅ Patched SecItemAdd")
        pos = self.data.find(b'SecItemCopyMatching')
        if pos != -1:
            code_pos = self.analyzer.find_function_code(self.data, 'SecItemCopyMatching')
            if code_pos:
                self.data[code_pos:code_pos+4] = SmartConfig.OP_RET
                self.log(f"✅ Patched SecItemCopyMatching")
        return True
    
    def patch_ssl_pinning(self):
        patterns = [
            b'URLSession:didReceiveChallenge:completionHandler:',
            b'URLAuthenticationChallenge',
            b'SecTrustEvaluate',
        ]
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                self.log(f"✅ Found SSL pattern at 0x{pos:X}")
                for i in range(pos - 0x200, pos + 0x200):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] == b'\x00\x00\x00\x00':
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            self.log(f"✅ SSL pinning patched at 0x{i:X}")
                            break
        return True
    
    def patch_device_fp(self):
        patterns = [
            b'GMV_TRK_V2_%@',
            b'GMV_PV_V2_%@',
            b'GMV_UDID_DEVICE_V2',
        ]
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                fake = b'FAKE_DEVICE_' + b'\x00' * 10
                self.data[pos:pos+len(pattern)] = fake[:len(pattern)]
                self.log(f"✅ Device FP patched")
        return True
    
    def apply_all_patches(self):
        results = {}
        results['domains'] = self.patch_domains()
        results['aes_key'] = self.patch_aes_key()
        results['showMainAlert'] = self.patch_showMainAlert()
        results['showToast'] = self.patch_showToast()
        results['showForceUpdate'] = self.patch_showForceUpdate()
        results['showGetUDID'] = self.patch_showGetUDID()
        results['setIsDialogVisible'] = self.patch_setIsDialogVisible()
        results['isValid'] = self.patch_isValid()
        results['processSuccess'] = self.patch_processSuccess()
        results['timer'] = self.patch_timer()
        results['delete_alerts'] = self.delete_alert_strings()
        results['keychain'] = self.patch_keychain_operations()
        results['ssl_pinning'] = self.patch_ssl_pinning()
        results['device_fp'] = self.patch_device_fp()
        return results
    
    def get_patched_data(self):
        return bytes(self.data)
    
    def get_log(self):
        return '\n'.join(self.patch_log)

# ============================================================
# ADVANCED PATCH
# ============================================================
def advanced_patch(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        backup_path = os.path.join(BACKUP_PATH, os.path.basename(file_path) + '.backup')
        with open(backup_path, 'wb') as f:
            f.write(data)
        
        patcher = SmartPatcher(data)
        results = patcher.apply_all_patches()
        
        patched_path = os.path.join(PATCHED_PATH, os.path.basename(file_path) + '.patched')
        with open(patched_path, 'wb') as f:
            f.write(patcher.get_patched_data())
        
        report = f"""
📊 **BÁO CÁO PATCH**

🔹 Domain: {results['domains']}
🔹 AES Key: {'✅' if results['aes_key'] > 0 else '❌'}
🔹 showMainAlert: {'✅' if results['showMainAlert'] else '❌'}
🔹 showToast: {'✅' if results['showToast'] else '❌'}
🔹 showForceUpdate: {'✅' if results['showForceUpdate'] else '❌'}
🔹 showGetUDID: {'✅' if results['showGetUDID'] else '❌'}
🔹 setIsDialogVisible: {'✅' if results['setIsDialogVisible'] else '❌'}
🔹 isValid: {'✅' if results['isValid'] else '❌'}
🔹 processSuccess: {results['processSuccess']}
🔹 Timer: {'✅' if results['timer'] else '❌'}
🔹 Xóa alert: {results['delete_alerts']}
🔹 Keychain: {'✅' if results['keychain'] else '❌'}
🔹 SSL Pinning: {'✅' if results['ssl_pinning'] else '❌'}
🔹 Device FP: {'✅' if results['device_fp'] else '❌'}
"""
        return patched_path, report
    except Exception as e:
        logger.error(f"Patch error: {e}")
        return None, str(e)

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
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 **GMV AI Crack Bot v3.0**\n"
        f"🧠 Công nghệ: Smart Patch Engine\n"
        f"🔧 Tự động patch mọi lớp bảo vệ\n\n"
        f"📤 Upload file `.dylib` để bắt đầu",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bạn không có quyền.")
        return

    document = update.message.document
    if not document:
        await update.message.reply_text("❌ Vui lòng gửi file.")
        return

    filename = document.file_name or "unknown.dylib"
    if not filename.endswith('.dylib'):
        await update.message.reply_text("❌ Vui lòng upload file `.dylib`.")
        return

    status_msg = await update.message.reply_text("⏳ Đang tải file...")

    try:
        file = await context.bot.get_file(document.file_id)
        file_path = os.path.join(DOWNLOAD_PATH, filename)
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
                    caption=f"✅ **GMV.dylib đã patch**\n\n{report}\n\n📥 Copy vào /Library/MobileSubstrate/DynamicLibraries/\n🔄 killall -9 PUBG",
                    parse_mode='Markdown'
                )

            os.remove(file_path)
            os.remove(patched_path)
        else:
            await status_msg.edit_text(f"❌ Patch thất bại.\n\nLỗi: {report}")

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
            "🧠 **Công nghệ AI Crack**\n\n"
            "1. 🔍 Phân tích thông minh\n"
            "2. 🔧 Patch tự động\n"
            "3. 🛡️ Bypass bảo vệ"
        )
    elif data == 'help':
        await query.edit_message_text(
            "📖 **Hướng dẫn**\n\n"
            "1. Upload file `GMV.dylib`\n"
            "2. Bot tự động patch\n"
            "3. Tải file đã patch"
        )
    elif data == 'status':
        await query.edit_message_text(
            "📊 **Trạng thái bot**\n\n"
            f"📁 Download: {DOWNLOAD_PATH}\n"
            f"📁 Patched: {PATCHED_PATH}\n"
            f"📦 File đã patch: {len(os.listdir(PATCHED_PATH))}\n"
            f"💾 Backup: {len(os.listdir(BACKUP_PATH))}"
        )

# ============================================================
# MAIN
# ============================================================
def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Vui lòng thay TOKEN")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 GMV AI Crack Bot v3.0 đang chạy...")
    app.run_polling()

if __name__ == "__main__":
    main()
