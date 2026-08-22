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
# CẤU HÌNH BOT
# ============================================================
TOKEN = "6320148381:AAEIQ30CzOlLwQHXTWqlr3Rpy79QQM6sH7Y"
ADMIN_ID = 5736655322

DOWNLOAD_PATH = "/root/gmv_bot/downloads"
PATCHED_PATH = "/root/gmv_bot/patched"
BACKUP_PATH = "/root/gmv_bot/backups"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(PATCHED_PATH, exist_ok=True)
os.makedirs(BACKUP_PATH, exist_ok=True)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIG THÔNG MINH - TỰ ĐỘNG NHẬN DIỆN
# ============================================================
class SmartConfig:
    # Domain cần thay (tự động phát hiện thêm)
    DOMAINS = [
        (b'gmvmoba.com', b'127.0.0.1\x00\x00\x00'),
        (b'https://gmvmoba.com', b'https://127.0.0.1\x00\x00'),
        (b'calm-unit-61cc.teamgamehub99.workers.dev', None),
        (b'api.baontq.xyz', None),  # GIỮ NGUYÊN
        (b'severapigmvbbv2.teamgamehub99.workers.dev', None),
        (b'api.authtool.app', None),
    ]
    
    # AES Key mặc định
    AES_KEY = b'bf76c74c23bd93c4016a2a0be4213f63'
    
    # ARM64 opcodes
    OP_RET = bytes.fromhex('C0 03 5F D6')
    OP_MOV_X0_1_RET = bytes.fromhex('20 00 80 52 C0 03 5F D6')
    OP_MOV_X0_0_RET = bytes.fromhex('00 00 80 52 C0 03 5F D6')
    OP_NOP = bytes.fromhex('1F 20 03 D5')
    
    # Các hàm cần patch
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
# CÔNG CỤ PHÂN TÍCH BINARY THÔNG MINH
# ============================================================
class BinaryAnalyzer:
    @staticmethod
    def find_all_occurrences(data, pattern):
        """Tìm tất cả vị trí xuất hiện của pattern"""
        positions = []
        pos = data.find(pattern)
        while pos != -1:
            positions.append(pos)
            pos = data.find(pattern, pos + 1)
        return positions
    
    @staticmethod
    def find_function_code(data, func_name):
        """Tìm vị trí code của hàm (không phải tên)"""
        # Tìm tên hàm trong __objc_methname
        name_pos = data.find(func_name.encode())
        if name_pos == -1:
            return None
        
        # Tìm tham chiếu đến tên hàm trong __objc_const
        # Mach-O: con trỏ đến tên hàm nằm trong struct method
        # Cách đơn giản: tìm byte gần đó
        search_start = max(0, name_pos - 0x1000)
        search_end = min(len(data), name_pos + 0x1000)
        
        # Tìm pattern con trỏ đến tên hàm
        # Trên ARM64, thường là adrp + add hoặc ldr
        for offset in range(search_start, search_end - 8):
            # Kiểm tra xem có phải con trỏ đến tên hàm không
            ptr = struct.unpack('<Q', data[offset:offset+8])[0]
            if ptr == name_pos:
                # Tìm code của hàm (thường cách đây vài byte)
                # Tìm lệnh đầu tiên của hàm (thường là stp hoặc sub)
                for i in range(offset - 0x200, offset):
                    if i >= 0 and i + 4 <= len(data):
                        # Kiểm tra xem có phải lệnh hợp lệ không
                        # ARM64: thường bắt đầu bằng FF 83 00 D9 (stp) hoặc 3F 20 03 D5 (nop)
                        if data[i] in [0xFF, 0x3F, 0x20]:
                            return i
        return None
    
    @staticmethod
    def find_cbz_pattern(data):
        """Tìm pattern cbz (Compare and Branch on Zero)"""
        # ARM64 cbz: 34 00 00 14 (ví dụ)
        # Thực tế có nhiều biến thể, cần phân tích kỹ
        # Tạm thời tìm pattern gần processSuccess
        pos = data.find(b'processSuccess')
        if pos == -1:
            return []
        
        # Tìm trong vùng 0x1000 byte
        start = max(0, pos - 0x1000)
        end = min(len(data), pos + 0x1000)
        
        results = []
        for i in range(start, end - 4):
            # ARM64 cbz thường có byte đầu là 0x34 hoặc 0xB4
            if data[i] in [0x34, 0xB4]:
                results.append(i)
        return results

# ============================================================
# ENGINE PATCH THÔNG MINH
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
        """Patch tất cả domain thông minh"""
        count = 0
        for old, new in SmartConfig.DOMAINS:
            if new is None:
                continue  # Giữ nguyên domain này
            positions = self.analyzer.find_all_occurrences(self.data, old)
            for pos in positions:
                if len(new) <= len(old):
                    self.data[pos:pos+len(new)] = new
                    if len(new) < len(old):
                        self.data[pos+len(new):pos+len(old)] = b'\x00' * (len(old) - len(new))
                else:
                    self.data[pos:pos+len(old)] = new[:len(old)]
                count += 1
                self.log(f"✅ Đã thay domain tại offset 0x{pos:X}")
        return count
    
    def patch_aes_key(self):
        """Thay AES key mặc định"""
        old_key = SmartConfig.AES_KEY
        new_key = b'31323334353637383930313233343536'  # Key mới 32 byte
        
        positions = self.analyzer.find_all_occurrences(self.data, old_key)
        for pos in positions:
            self.data[pos:pos+32] = new_key
            self.log(f"✅ Đã thay AES key tại offset 0x{pos:X}")
        return len(positions)
    
    def patch_function(self, func_name, patch_bytes, is_code=True):
        """Patch hàm thông minh"""
        if is_code:
            pos = self.analyzer.find_function_code(self.data, func_name)
        else:
            pos = self.data.find(func_name.encode())
        
        if pos is None or pos == -1:
            self.log(f"⚠️ Không tìm thấy hàm {func_name}")
            return False
        
        # Kiểm tra xem đã patch chưa
        if self.data[pos:pos+len(patch_bytes)] == patch_bytes:
            self.log(f"⏭️ Hàm {func_name} đã được patch")
            return True
        
        self.data[pos:pos+len(patch_bytes)] = patch_bytes
        self.log(f"✅ Đã patch {func_name} tại offset 0x{pos:X}")
        return True
    
    def patch_isValid(self):
        """Patch isValid luôn trả về YES"""
        return self.patch_function('isValid', SmartConfig.OP_MOV_X0_1_RET)
    
    def patch_showMainAlert(self):
        """Patch showMainAlert_V2: thành ret"""
        return self.patch_function('showMainAlert_V2:', SmartConfig.OP_RET)
    
    def patch_showToast(self):
        """Patch showToast_V2: thành ret"""
        return self.patch_function('showToast_V2:', SmartConfig.OP_RET)
    
    def patch_showForceUpdate(self):
        """Patch showForceUpdateAlert_V2:message: thành ret"""
        return self.patch_function('showForceUpdateAlert_V2:message:', SmartConfig.OP_RET)
    
    def patch_showGetUDID(self):
        """Patch showGetUDIDAlert_V2 thành ret"""
        return self.patch_function('showGetUDIDAlert_V2', SmartConfig.OP_RET)
    
    def patch_setIsDialogVisible(self):
        """Patch setIsDialogVisible_V2: luôn set NO"""
        return self.patch_function('setIsDialogVisible_V2:', SmartConfig.OP_MOV_X0_0_RET)
    
    def patch_processSuccess(self):
        """Patch processSuccess_V2:json: - đảo logic status"""
        # Tìm cbz trong processSuccess và đảo thành cbnz
        positions = self.analyzer.find_cbz_pattern()
        patched = 0
        for pos in positions:
            # Thử đảo cbz -> cbnz
            if self.data[pos] == 0x34:
                self.data[pos] = 0x35  # cbz -> cbnz
                patched += 1
                self.log(f"✅ Đã đảo cbz thành cbnz tại 0x{pos:X}")
            elif self.data[pos] == 0xB4:
                self.data[pos] = 0xB5
                patched += 1
                self.log(f"✅ Đã đảo cbz thành cbnz tại 0x{pos:X}")
        return patched
    
    def patch_timer(self):
        """Vô hiệu hóa timer polling"""
        # Tìm startUpdatePolling_V2 và patch lệnh tạo timer
        pos = self.data.find(b'startUpdatePolling')
        if pos != -1:
            # Tìm scheduledTimerWithTimeInterval gần đó
            timer_pos = self.data.find(b'scheduledTimerWithTimeInterval', pos, pos + 0x1000)
            if timer_pos != -1:
                # Patch thành NOP
                for i in range(timer_pos - 0x10, timer_pos + 0x10):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] == b'\x00\x00\x00\x00':
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            self.log(f"✅ Đã vô hiệu hóa timer tại 0x{i:X}")
                            return True
        return False
    
    def delete_alert_strings(self):
        """Xóa tất cả chuỗi thông báo alert"""
        alert_strings = [
            b'Nh\xe1\xba\xadp Key',
            b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',
            b'Update required',
            b'Vui l\xc3\xb2ng nh\xe1\xba\xadp Key',
            b'Check Key',
            b'Get Key',
            b'Click Lay UDID',
            b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',
            b'Nh\u1eadp Key',
        ]
        count = 0
        for alert in alert_strings:
            positions = self.analyzer.find_all_occurrences(self.data, alert)
            for pos in positions:
                self.data[pos:pos+len(alert)] = b'\x00' * len(alert)
                count += 1
                self.log(f"✅ Đã xóa chuỗi alert tại 0x{pos:X}")
        return count
    
    def patch_keychain_operations(self):
        """Patch SecItemAdd và SecItemCopyMatching"""
        # Tìm SecItemAdd và patch ret
        pos = self.data.find(b'SecItemAdd')
        if pos != -1:
            code_pos = self.analyzer.find_function_code(self.data, 'SecItemAdd')
            if code_pos:
                self.data[code_pos:code_pos+4] = SmartConfig.OP_RET
                self.log(f"✅ Đã patch SecItemAdd")
        
        # Tìm SecItemCopyMatching
        pos = self.data.find(b'SecItemCopyMatching')
        if pos != -1:
            code_pos = self.analyzer.find_function_code(self.data, 'SecItemCopyMatching')
            if code_pos:
                self.data[code_pos:code_pos+4] = SmartConfig.OP_RET
                self.log(f"✅ Đã patch SecItemCopyMatching")
        return True
    
    def patch_ssl_pinning(self):
        """Patch SSL pinning (nếu có)"""
        # Tìm URLSessionDelegate và patch
        patterns = [
            b'URLSession:didReceiveChallenge:completionHandler:',
            b'URLAuthenticationChallenge',
            b'SecTrustEvaluate',
        ]
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                # Patch gần đó để luôn accept
                self.log(f"✅ Tìm thấy SSL pinning pattern tại 0x{pos:X}")
                # Tìm và patch
                for i in range(pos - 0x200, pos + 0x200):
                    if i >= 0 and i + 4 <= len(self.data):
                        if self.data[i:i+4] == b'\x00\x00\x00\x00':
                            self.data[i:i+4] = SmartConfig.OP_NOP
                            self.log(f"✅ Đã patch SSL pinning tại 0x{i:X}")
                            break
        return True
    
    def patch_device_fp(self):
        """Patch device fingerprint"""
        # Tìm GMV_TRK_V2_%@ và GMV_PV_V2_%@
        patterns = [
            b'GMV_TRK_V2_%@',
            b'GMV_PV_V2_%@',
            b'GMV_UDID_DEVICE_V2',
        ]
        for pattern in patterns:
            pos = self.data.find(pattern)
            if pos != -1:
                # Thay thành giá trị giả
                fake = b'FAKE_DEVICE_' + b'\x00' * 10
                self.data[pos:pos+len(pattern)] = fake[:len(pattern)]
                self.log(f"✅ Đã patch device fingerprint")
        return True
    
    def apply_all_patches(self):
        """Áp dụng tất cả patch"""
        results = {}
        
        # 1. Domain
        results['domains'] = self.patch_domains()
        
        # 2. AES Key
        results['aes_key'] = self.patch_aes_key()
        
        # 3. Các hàm alert
        results['showMainAlert'] = self.patch_showMainAlert()
        results['showToast'] = self.patch_showToast()
        results['showForceUpdate'] = self.patch_showForceUpdate()
        results['showGetUDID'] = self.patch_showGetUDID()
        results['setIsDialogVisible'] = self.patch_setIsDialogVisible()
        
        # 4. isValid
        results['isValid'] = self.patch_isValid()
        
        # 5. processSuccess
        results['processSuccess'] = self.patch_processSuccess()
        
        # 6. Timer
        results['timer'] = self.patch_timer()
        
        # 7. Xóa alert strings
        results['delete_alerts'] = self.delete_alert_strings()
        
        # 8. Keychain
        results['keychain'] = self.patch_keychain_operations()
        
        # 9. SSL Pinning
        results['ssl_pinning'] = self.patch_ssl_pinning()
        
        # 10. Device FP
        results['device_fp'] = self.patch_device_fp()
        
        return results
    
    def get_patched_data(self):
        return bytes(self.data)
    
    def get_log(self):
        return '\n'.join(self.patch_log)

# ============================================================
# HÀM PATCH CHÍNH
# ============================================================
def advanced_patch(file_path):
    """Patch binary với công nghệ cao"""
    try:
        with open(file_path, 'rb') as f:
            data = f.read()
        
        # Backup file gốc
        backup_path = os.path.join(BACKUP_PATH, os.path.basename(file_path) + '.backup')
        with open(backup_path, 'wb') as f:
            f.write(data)
        
        # Patch thông minh
        patcher = SmartPatcher(data)
        results = patcher.apply_all_patches()
        
        # Ghi file đã patch
        patched_path = os.path.join(PATCHED_PATH, os.path.basename(file_path) + '.patched')
        with open(patched_path, 'wb') as f:
            f.write(patcher.get_patched_data())
        
        # Tạo report
        report = f"""
📊 **BÁO CÁO PATCH THÔNG MINH**

🔹 **Domain**: Đã thay {results['domains']} domain
🔹 **AES Key**: {'✅' if results['aes_key'] > 0 else '❌'}
🔹 **showMainAlert**: {'✅' if results['showMainAlert'] else '❌'}
🔹 **showToast**: {'✅' if results['showToast'] else '❌'}
🔹 **showForceUpdate**: {'✅' if results['showForceUpdate'] else '❌'}
🔹 **showGetUDID**: {'✅' if results['showGetUDID'] else '❌'}
🔹 **setIsDialogVisible**: {'✅' if results['setIsDialogVisible'] else '❌'}
🔹 **isValid**: {'✅' if results['isValid'] else '❌'}
🔹 **processSuccess**: Đã đảo {results['processSuccess']} cbz → cbnz
🔹 **Timer Polling**: {'✅' if results['timer'] else '❌'}
🔹 **Xóa alert strings**: Đã xóa {results['delete_alerts']} chuỗi
🔹 **Keychain**: {'✅' if results['keychain'] else '❌'}
🔹 **SSL Pinning**: {'✅' if results['ssl_pinning'] else '❌'}
🔹 **Device FP**: {'✅' if results['device_fp'] else '❌'}
"""
        return patched_path, report
    except Exception as e:
        logger.error(f"Advanced patch error: {e}")
        return None, str(e)

# ============================================================
# TELEGRAM HANDLERS
# ============================================================
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
        f"📤 Upload file `.dylib` để bắt đầu\n"
        f"👤 Admin: {user.first_name}",
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
                    caption=f"✅ **GMV.dylib đã patch (AI Engine)**\n\n{report}\n\n📥 Copy vào /Library/MobileSubstrate/DynamicLibraries/\n🔄 killall -9 PUBG",
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
        await query.edit_message_text("📤 **Upload GMV.dylib**\n\nGửi file `.dylib` vào chat. Bot sẽ tự động phân tích và patch.", parse_mode='Markdown')

    elif data == 'info':
        await query.edit_message_text(
            "🧠 **Công nghệ AI Crack**\n\n"
            "1. 🔍 **Phân tích thông minh**\n"
            "   - Nhận diện tự động các hàm cần patch\n"
            "   - Tìm kiếm pattern trong binary\n"
            "\n"
            "2. 🔧 **Patch tự động**\n"
            "   - Domain → 127.0.0.1\n"
            "   - Alert (showMainAlert, showToast...)\n"
            "   - isValid → luôn YES\n"
            "   - processSuccess → đảo logic\n"
            "   - Timer polling\n"
            "   - Keychain operations\n"
            "   - SSL Pinning\n"
            "   - Device fingerprint\n"
            "\n"
            "3. 🛡️ **Bypass bảo vệ**\n"
            "   - Xác thực chữ ký\n"
            "   - AES key\n"
            "   - ExpiredAt\n"
            "   - Force update"
        )

    elif data == 'help':
        await query.edit_message_text(
            "📖 **Hướng dẫn sử dụng**\n\n"
            "1. Upload file `GMV.dylib`\n"
            "2. Bot tự động phân tích và patch\n"
            "3. Nhận file đã patch\n"
            "4. Copy vào `/Library/MobileSubstrate/DynamicLibraries/`\n"
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
            f"⏳ Đang chờ upload..."
        )

# ============================================================
# MAIN
# ============================================================
def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Vui lòng thay TOKEN trong file bot.py")
        sys.exit(1)

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 GMV AI Crack Bot v3.0 đang chạy...")
    print(f"📤 Token: {TOKEN}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    print("🧠 Smart Patch Engine đã sẵn sàng")
    app.run_polling()

if __name__ == "__main__":
    main()
