# --- bot/telegram_bot.py ---
"""
Telegram Bot Worker
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.redis_client import RedisManager
from app.proxy_manager import ProxyManager

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(id) for id in os.getenv("ALLOWED_USERS", "").split(",")]

redis_manager = RedisManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("✅ Validate", callback_data="validate")],
        [InlineKeyboardButton("📤 Export", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean", callback_data="clean")]
    ]
    
    await update.message.reply_text(
        f"🤖 **Nexus Proxy Manager**\n"
        f"Status: 🟢 Online\n"
        f"Time: {datetime.now().strftime('%H:%M:%S')}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats = await redis_manager.get_stats()
    if not stats:
        await update.message.reply_text("⚠️ No data")
        return
        
    msg = (
        f"📊 **Proxy Stats**\n"
        f"━━━━━━━━━━━━━\n"
        f"Total: {stats.get('total', 0)}\n"
        f"Alive: {stats.get('alive', 0)}\n"
        f"Dead: {stats.get('dead', 0)}\n"
        f"Rate: {stats.get('alive', 0) / max(stats.get('total', 1), 1) * 100:.1f}%"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    await update.message.reply_text("🔄 Validating...")
    
    manager = ProxyManager()
    await manager.initialize()
    result = await manager.validate_all()
    
    await update.message.reply_text(
        f"✅ Done\nTotal: {result['total']}\nValid: {result['validated']}"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    doc = update.message.document
    if not doc or not doc.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Need .txt file")
        return
        
    await update.message.reply_text("📤 Loading...")
    
    file = await context.bot.get_file(doc.file_id)
    content = await file.download_as_bytearray()
    
    manager = ProxyManager()
    await manager.initialize()
    count = await manager.load_from_file(content.decode('utf-8'))
    
    await update.message.reply_text(f"✅ Loaded {count} proxies")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        await send_stats(update, context)
    elif query.data == "validate":
        await validate_command(update, context)
    elif query.data == "export":
        alive = await redis_manager.get_alive_proxies()
        if alive:
            content = "\n".join([f"{p['ip']}:{p['port']}" for p in alive])
            await query.message.reply_document(
                document=content.encode('utf-8'),
                filename=f"proxies_{datetime.now().strftime('%Y%m%d')}.txt"
            )
    elif query.data == "clean":
        proxies = await redis_manager.get_all_proxies()
        dead = [p for p in proxies if not p.get('is_alive', False)]
        for p in dead:
            await redis_manager.remove_proxy(f"{p['ip']}:{p['port']}")
        await query.edit_message_text(f"🧹 Removed {len(dead)} dead proxies")

async def main():
    await redis_manager.connect()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", send_stats))
    app.add_handler(CommandHandler("validate", validate_command))
    app.add_handler(MessageHandler(filters.Document.TXT, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Bot started")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
