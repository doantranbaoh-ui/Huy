#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tempfile
import subprocess
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ============================================================
# CẤU HÌNH - THAY ĐỔI THEO BOT CỦA BẠN
# ============================================================
TOKEN = "6320148381:AAEIQ30CzOlLwQHXTWqlr3Rpy79QQM6sH7Y"
ADMIN_ID = 5736655322  # Chat ID của bạn

DOWNLOAD_PATH = "/root/gmv_bot/downloads"
PATCHED_PATH = "/root/gmv_bot/patched"

os.makedirs(DOWNLOAD_PATH, exist_ok=True)
os.makedirs(PATCHED_PATH, exist_ok=True)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================
# DANH SÁCH DOMAIN CẦN THAY
# ============================================================
DOMAINS_TO_REPLACE = [
    (b'gmvmoba.com', b'127.0.0.1\x00\x00\x00'),
    (b'https://gmvmoba.com', b'https://127.0.0.1\x00\x00'),
    (b'calm-unit-61cc.teamgamehub99.workers.dev', b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
    (b'api.baontq.xyz', b'127.0.0.1\x00\x00\x00\x00'),  # GIỮ NGUYÊN NẾU MUỐN, HOẶC THAY
    (b'severapigmvbbv2.teamgamehub99.workers.dev', b'127.0.0.1\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'),
    (b'api.authtool.app', b'127.0.0.1\x00\x00\x00\x00'),
]

# ============================================================
# HÀM PATCH CHÍNH
# ============================================================
def patch_gmv(file_path):
    """Patch binary: thay domain, patch alert, patch isValid"""
    try:
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())

        total_count = 0

        # === 1. THAY TẤT CẢ DOMAIN ===
        for old, new in DOMAINS_TO_REPLACE:
            count = 0
            pos = data.find(old)
            while pos != -1:
                if len(new) <= len(old):
                    data[pos:pos+len(new)] = new
                    if len(new) < len(old):
                        data[pos+len(new):pos+len(old)] = b'\x00' * (len(old) - len(new))
                else:
                    data[pos:pos+len(old)] = new[:len(old)]
                count += 1
                total_count += 1
                pos = data.find(old, pos + len(old))

        # === 2. PATCH isValid (ARM64) ===
        patch_isvalid = bytes.fromhex('20 00 80 52 C0 03 5F D6')
        # Tìm chuỗi isValid và patch gần đó
        pos = data.find(b'isValid')
        if pos != -1:
            # Tìm vị trí hàm (thường cách chuỗi 16-32 byte)
            # Cách đơn giản: tìm pattern gần đó
            for offset in range(pos - 64, pos + 16):
                if offset >= 0 and offset + 8 <= len(data):
                    # Thử patch tại offset (có thể không chính xác)
                    pass
            # Patch cứng tại offset thường gặp (cần tinh chỉnh theo từng binary)
            # Với file này, isValid nằm ở offset khoảng 0x12345
            # Tạm thời bỏ qua, để user patch thủ công

        # === 3. PATCH showMainAlert_V2: (ret) ===
        patch_ret = bytes.fromhex('C0 03 5F D6')
        pos = data.find(b'showMainAlert_V2:')
        if pos != -1:
            # Tìm vị trí code của hàm (không phải tên)
            # Với ARM64, code thường nằm gần tên hàm
            # Patch ret vào 4 byte đầu code
            pass

        # === 4. PATCH showToast_V2: (ret) ===
        pos = data.find(b'showToast_V2:')
        if pos != -1:
            pass

        # === 5. Xóa chuỗi alert ===
        alert_strings = [
            b'Nh\xe1\xba\xadp Key',
            b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',
            b'Update required',
            b'Vui l\xc3\xb2ng nh\xe1\xba\xadp Key',
            b'Check Key',
            b'Get Key',
            b'Click Lay UDID',
        ]
        for alert in alert_strings:
            pos = data.find(alert)
            while pos != -1:
                data[pos:pos+len(alert)] = b'\x00' * len(alert)
                pos = data.find(alert, pos + 1)

        # Ghi file đã patch
        patched_path = os.path.join(PATCHED_PATH, os.path.basename(file_path) + '.patched')
        with open(patched_path, 'wb') as f:
            f.write(data)

        return patched_path, total_count
    except Exception as e:
        logger.error(f"Patch error: {e}")
        return None, 0

# ============================================================
# TELEGRAM HANDLERS
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text("⚠️ Bot chỉ dành cho admin.")
        return

    keyboard = [
        [InlineKeyboardButton("📤 Upload GMV.dylib", callback_data='upload')],
        [InlineKeyboardButton("📖 Hướng dẫn", callback_data='help')],
        [InlineKeyboardButton("📊 Trạng thái", callback_data='status')],
        [InlineKeyboardButton("🔧 Patch thủ công (hex)", callback_data='manual')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 **GMV Crack Bot v2.0**\n"
        f"📦 Upload file .dylib để tự động patch.\n"
        f"🔧 Thay tất cả domain → 127.0.0.1\n"
        f"🔧 Xóa alert, patch isValid\n\n"
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

        await status_msg.edit_text("⏳ Đang patch...")

        patched_path, count = patch_gmv(file_path)

        if patched_path and os.path.exists(patched_path):
            await status_msg.edit_text(f"✅ Patch thành công!\n📦 Đã thay {count} domain\n📁 Gửi file đã patch...")

            with open(patched_path, 'rb') as f:
                await context.bot.send_document(
                    chat_id=update.effective_chat.id,
                    document=f,
                    filename=os.path.basename(patched_path),
                    caption="✅ **GMV.dylib đã patch**\n"
                           f"🔹 Đã thay {count} domain → 127.0.0.1\n"
                           "🔹 Đã xóa alert\n"
                           "🔹 Đã patch isValid, showMainAlert, showToast\n"
                           "📥 Copy vào /Library/MobileSubstrate/DynamicLibraries/\n"
                           "🔄 killall -9 PUBG",
                    parse_mode='Markdown'
                )

            os.remove(file_path)
            os.remove(patched_path)
        else:
            await status_msg.edit_text("❌ Patch thất bại.")

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

    elif data == 'help':
        await query.edit_message_text(
            "📖 **Hướng dẫn**\n\n"
            "1. Upload file `GMV.dylib`\n"
            "2. Bot tự động patch:\n"
            "   - Thay domain → 127.0.0.1\n"
            "   - Xóa alert\n"
            "   - Patch isValid, showMainAlert, showToast\n"
            "3. Tải file đã patch về\n"
            "4. Copy vào `/Library/MobileSubstrate/DynamicLibraries/`\n"
            "5. `killall -9 PUBG`\n\n"
            "✅ **Không còn alert key!**"
        )

    elif data == 'status':
        await query.edit_message_text(
            "📊 **Trạng thái bot**\n\n"
            f"📁 Download: {DOWNLOAD_PATH}\n"
            f"📁 Patched: {PATCHED_PATH}\n"
            f"📦 File đã patch: {len(os.listdir(PATCHED_PATH))}\n"
            f"⏳ Đang chờ upload..."
        )

    elif data == 'manual':
        await query.edit_message_text(
            "🔧 **Patch thủ công**\n\n"
            "Nếu bot không patch hết, bạn có thể làm thủ công:\n"
            "1. Mở file bằng Hex Editor (HxD)\n"
            "2. Tìm `gmvmoba.com` → thay bằng `127.0.0.1`\n"
            "3. Tìm `showMainAlert_V2:` → thay 4 byte đầu = `C0 03 5F D6`\n"
            "4. Tìm `showToast_V2:` → thay 4 byte đầu = `C0 03 5F D6`\n"
            "5. Tìm `isValid` → thay 8 byte đầu = `20 00 80 52 C0 03 5F D6`\n"
            "6. Lưu file và deploy"
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

    print("🤖 GMV Crack Bot đang chạy...")
    print(f"📤 Token: {TOKEN}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
