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
from datetime import datetime

# ============================================================
# CỐ GẮNG IMPORT TELEGRAM – NẾU LỖI THÌ THÔNG BÁO
# ============================================================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, Updater
except ImportError as e:
    print(f"❌ Lỗi import telegram: {e}")
    print("📦 Chạy lệnh: pip install python-telegram-bot==20.7")
    sys.exit(1)

# ============================================================
# CẤU HÌNH
# ============================================================
TOKEN = "6320148381:AAEIQ30CzOlLwQHXTWqlr3Rpy79QQM6sH7Y"
ADMIN_ID = 5736655322

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOAD_PATH = os.path.join(BASE_DIR, "downloads")
PATCHED_PATH = os.path.join(BASE_DIR, "patched")
BACKUP_PATH = os.path.join(BASE_DIR, "backups")
LOG_PATH = os.path.join(BASE_DIR, "logs")

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
# CONFIG PATCH
# ============================================================
class PatchConfig:
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

# ============================================================
# HÀM PATCH ĐƠN GIẢN
# ============================================================
def patch_gmv(file_path):
    try:
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())

        total_count = 0

        # 1. Thay domain
        for old, new in PatchConfig.DOMAINS:
            if new is None:
                continue
            pos = data.find(old)
            while pos != -1:
                if len(new) <= len(old):
                    data[pos:pos+len(new)] = new
                    if len(new) < len(old):
                        data[pos+len(new):pos+len(old)] = b'\x00' * (len(old) - len(new))
                else:
                    data[pos:pos+len(old)] = new[:len(old)]
                total_count += 1
                pos = data.find(old, pos + len(old))

        # 2. Xóa alert strings
        alert_strings = [
            'Nhập Key'.encode('utf-8'),
            'Key không hợp lệ'.encode('utf-8'),
            'Vui lòng nhập Key'.encode('utf-8'),
            'Update required'.encode('utf-8'),
            'Check Key'.encode('utf-8'),
            'Get Key'.encode('utf-8'),
            'Click Lay UDID'.encode('utf-8'),
            b'Nh\xe1\xba\xadp Key',
            b'Key kh\xc3\xb4ng h\xe1\xbb\xa3p l\xe1\xbb\x87',
            b'Vui l\xc3\xb2ng nh\xe1\xba\xadp Key',
        ]
        for alert in alert_strings:
            pos = data.find(alert)
            while pos != -1:
                data[pos:pos+len(alert)] = b'\x00' * len(alert)
                pos = data.find(alert, pos + 1)

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
            await status_msg.edit_text(f"✅ Patch thành công! 📦 Đã thay {count} domain")

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
# MAIN – TƯƠNG THÍCH NHIỀU PHIÊN BẢN
# ============================================================
def create_app():
    """Tạo Application với fallback cho nhiều phiên bản"""
    try:
        # Cách 1: Application.builder() (python-telegram-bot >= 20.0)
        return Application.builder().token(TOKEN).build()
    except (AttributeError, TypeError) as e:
        logger.warning(f"Application.builder() failed: {e}, trying Updater...")
        try:
            # Cách 2: Updater (phiên bản cũ)
            from telegram.ext import Updater
            updater = Updater(TOKEN, use_context=True)
            return updater.application
        except TypeError:
            # Cách 3: Updater không có use_context
            updater = Updater(TOKEN)
            return updater.application

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
