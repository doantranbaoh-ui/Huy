# --- telegram_bot/bot.py ---
"""
Telegram Bot Worker
"""

import os
import sys
import asyncio
import logging
import json
from datetime import datetime
from typing import List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Local imports — from proxy_manager directory
from proxy_manager.redis_client import RedisManager
from proxy_manager.manager import ProxyManager

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

# --- Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Config ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_USERS = [int(id) for id in os.getenv("ALLOWED_USERS", "").split(",")]

# --- Redis Manager ---
redis_manager = RedisManager()

# --- Bot Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="stats")],
        [InlineKeyboardButton("✅ Validate Proxies", callback_data="validate")],
        [InlineKeyboardButton("📤 Export Alive", callback_data="export")],
        [InlineKeyboardButton("🧹 Clean Dead", callback_data="clean")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🤖 **Nexus Proxy Manager Bot**\n"
        f"📡 Status: Online\n"
        f"🕒 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def send_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send current statistics"""
    stats = await redis_manager.get_stats()
    
    if not stats:
        await update.message.reply_text("⚠️ No data available")
        return
        
    msg = (
        f"📊 **Proxy Statistics**\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📦 Total: {stats.get('total', 0)}\n"
        f"✅ Alive: {stats.get('alive', 0)}\n"
        f"❌ Dead: {stats.get('dead', 0)}\n"
        f"🔄 Last Update: {stats.get('last_update', 'Never')}\n"
        f"📈 Success Rate: "
        f"{'%.1f' % (stats.get('alive', 0) / max(stats.get('total', 1), 1) * 100)}%"
    )
    
    await update.message.reply_text(msg, parse_mode="Markdown")

async def validate_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Validate all proxies"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    await update.message.reply_text("🔄 Validating proxies...")
    
    manager = ProxyManager()
    await manager.initialize()
    result = await manager.validate_all()
    
    await update.message.reply_text(
        f"✅ **Validation Complete**\n"
        f"Total: {result['total']}\n"
        f"Validated: {result['validated']}",
        parse_mode="Markdown"
    )

async def handle_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle uploaded proxy file"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    document = update.message.document
    if not document or not document.file_name.endswith('.txt'):
        await update.message.reply_text("⚠️ Please send a .txt file")
        return
        
    await update.message.reply_text("📤 Loading proxies...")
    
    file = await context.bot.get_file(document.file_id)
    content = await file.download_as_bytearray()
    text = content.decode('utf-8')
    
    manager = ProxyManager()
    await manager.initialize()
    count = await manager.load_from_file(text)
    
    await update.message.reply_text(
        f"✅ Loaded {count} proxies from {document.file_name}"
    )

async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Export alive proxies"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    alive = await redis_manager.get_alive_proxies()
    if not alive:
        await update.message.reply_text("⚠️ No alive proxies")
        return
        
    content = "\n".join([f"{p['ip']}:{p['port']}" for p in alive])
    filename = f"alive_proxies_{datetime.now().strftime('%Y%m%d')}.txt"
    
    await update.message.reply_document(
        document=content.encode('utf-8'),
        filename=filename
    )

async def clean_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clean dead proxies"""
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await update.message.reply_text("❌ Unauthorized")
        return
        
    # Get all proxies
    proxies = await redis_manager.get_all_proxies()
    dead = [p for p in proxies if not p.get('is_alive', False)]
    
    for p in dead:
        await redis_manager.remove_proxy(f"{p['ip']}:{p['port']}")
    
    await update.message.reply_text(
        f"🧹 **Cleaned**\n"
        f"Removed {len(dead)} dead proxies\n"
        f"Remaining: {len(proxies) - len(dead)}"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    if user_id not in ALLOWED_USERS:
        await query.edit_message_text("❌ Unauthorized")
        return
        
    if query.data == "stats":
        await send_stats(update, context)
    elif query.data == "validate":
        await validate_command(update, context)
    elif query.data == "export":
        await export_command(update, context)
    elif query.data == "clean":
        await clean_command(update, context)

async def main():
    """Run the bot"""
    if not TOKEN:
        logger.error("❌ TELEGRAM_BOT_TOKEN not set")
        return
        
    await redis_manager.connect()
    
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", send_stats))
    app.add_handler(CommandHandler("validate", validate_command))
    app.add_handler(CommandHandler("export", export_command))
    app.add_handler(CommandHandler("clean", clean_command))
    app.add_handler(MessageHandler(filters.Document.TXT, handle_file))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    logger.info("🚀 Bot started")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
