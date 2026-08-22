#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import logging
import tempfile

# ============================================================
# KIỂM TRA VÀ CÀI ĐẶT THƯ VIỆN TỰ ĐỘNG
# ============================================================
def install_package(package):
    """Tự động cài đặt package nếu chưa có"""
    try:
        __import__(package)
    except ImportError:
        print(f"📦 Đang cài {package}...")
        os.system(f"pip install {package}")

# Cài đặt telegram nếu chưa có
try:
    import telegram
except ImportError:
    print("📦 Đang cài python-telegram-bot...")
    os.system("pip install python-telegram-bot==20.7")
    import telegram

# ============================================================
# IMPORT THƯ VIỆN
# ============================================================
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
# PATCH ENGINE
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

        # 3. Thay calm-unit-61cc.teamgamehub99.workers.dev
        old3 = b'calm-unit-61cc.teamgamehub99.workers.dev'
        new3 = b'127.0.0.1' + b'\x00' * (len(old3) - 9)
        pos = data.find(old3)
        while pos != -1:
            data[pos:pos+len(old3)] = new3
            total_count += 1
            pos = data.find(old3, pos + len(new3))

        # 4. Thay severapigmvbbv2.teamgamehub99.workers.dev
        old4 = b'severapigmvbbv2.teamgamehub99.workers.dev'
        new4 = b'127.0.0.1' + b'\x00' * (len(old4) - 9)
        pos = data.find(old4)
        while pos != -1:
            data[pos:pos+len(old4)] = new4
            total_count += 1
            pos = data.find(old4, pos + len(new4))

        # 5. Thay api.authtool.app
        old5 = b'api.authtool.app'
        new5 = b'127.0.0.1' + b'\x00' * (len(old5) - 9)
        pos = data.find(old5)
        while pos != -1:
            data[pos:pos+len(old5)] = new5
            total_count += 1
            pos = data.find(old5, pos + len(new5))

        # 6. Xóa chuỗi alert
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
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🤖 **GMV Crack Bot**\n"
        f"📦 Upload file .dylib để tự động patch.\n"
        f"🔧 Thay tất cả domain → 127.0.0.1\n"
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
                           "🔹 Giữ nguyên api.baontq.xyz\n"
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
# MAIN - TƯƠNG THÍCH NHIỀU PHIÊN BẢN
# ============================================================
def create_app():
    """Tạo Application với fallback cho nhiều phiên bản"""
    try:
        # Cách 1: Application.builder() (python-telegram-bot >= 20.0)
        return Application.builder().token(TOKEN).build()
    except (AttributeError, TypeError) as e:
        logger.warning(f"Application.builder() failed: {e}")
        try:
            # Cách 2: Dùng Updater (phiên bản cũ)
            from telegram.ext import Updater
            updater = Updater(token=TOKEN, use_context=True)
            return updater.dispatcher
        except Exception as e2:
            logger.warning(f"Updater failed: {e2}")
            try:
                # Cách 3: Updater không có use_context
                from telegram.ext import Updater
                updater = Updater(TOKEN)
                return updater.dispatcher
            except Exception as e3:
                logger.error(f"All methods failed: {e3}")
                raise

def main():
    if not TOKEN or TOKEN == "YOUR_BOT_TOKEN":
        print("❌ Vui lòng thay TOKEN trong file bot.py")
        sys.exit(1)

    try:
        app = create_app()
    except Exception as e:
        print(f"❌ Không thể tạo app: {e}")
        print("📦 Thử cài lại: pip install python-telegram-bot==20.7")
        sys.exit(1)

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("=" * 50)
    print("🤖 GMV Crack Bot")
    print("📤 Token:", TOKEN)
    print("👤 Admin ID:", ADMIN_ID)
    print("=" * 50)
    print("🟢 Bot đang chạy...")
    
    app.run_polling()

if __name__ == "__main__":
    main()
