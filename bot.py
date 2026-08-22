#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tempfile
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

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
# HÀM PATCH ĐƠN GIẢN
# ============================================================
def patch_gmv(file_path):
    """Patch binary: thay domain, xóa alert"""
    try:
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())

        total_count = 0

        # 1. Thay gmvmoba.com → 127.0.0.1
        old = b'gmvmoba.com'
        new = b'127.0.0.1\x00\x00\x00'
        pos = data.find(old)
        while pos != -1:
            data[pos:pos+len(old)] = new
            total_count += 1
            pos = data.find(old, pos + len(new))

        # 2. Thay https://gmvmoba.com
        old2 = b'https://gmvmoba.com'
        new2 = b'https://127.0.0.1\x00\x00'
        pos = data.find(old2)
        while pos != -1:
            data[pos:pos+len(old2)] = new2
            total_count += 1
            pos = data.find(old2, pos + len(new2))

        # 3. Xóa chuỗi alert tiếng Việt (dùng hex bytes)
        alert_strings = [
            b'Nh\xe1\xba\xadp Key',  # Nhập Key
            b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',  # Key không hợp lệ
            b'Vui l\xc3\xb2ng nh\xe1\xba\xadp Key',
            b'Update required',
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
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 **GMV Crack Bot**\n"
        f"📦 Upload file .dylib để tự động patch.\n"
        f"🔧 Thay gmvmoba.com → 127.0.0.1\n"
        f"🔧 Xóa alert\n\n"
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
                    caption=f"✅ **GMV.dylib đã patch**\n"
                           f"🔹 Đã thay {count} domain → 127.0.0.1\n"
                           "🔹 Đã xóa alert\n"
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
            "2. Bot tự động patch\n"
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

# ============================================================
# MAIN - SỬA LỖI TƯƠNG THÍCH
# ============================================================
def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Vui lòng thay TOKEN trong file bot.py")
        sys.exit(1)

    # Cách 1: Dùng Application.builder() (cách mới)
    try:
        app = Application.builder().token(TOKEN).build()
    except AttributeError:
        # Cách 2: Dùng Updater (cách cũ, tương thích hơn)
        from telegram.ext import Updater
        updater = Updater(TOKEN)
        app = updater.application

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("🤖 GMV Crack Bot đang chạy...")
    print(f"📤 Token: {TOKEN}")
    print(f"👤 Admin ID: {ADMIN_ID}")
    app.run_polling()

if __name__ == "__main__":
    main()
