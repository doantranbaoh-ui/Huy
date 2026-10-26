# bot.py - Bot Telegram full: delay, fakesoan, câm box/Inbox, help, id, stats, keepalive, tự xóa lệnh
# Yêu cầu: pip install telethon aiohttp
# Chạy: python bot.py

import asyncio
import json
import os
import logging
from telethon import TelegramClient, events

from keepalive import start_keepalive, mark_running, status

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("bot")

# ===== CẤU HÌNH TRỰC TIẾP =====
API_ID = 12345678
API_HASH = "your_api_hash_here"
SESSION_NAME = "acc_chinh"
PHONE = "+84123456789"

CONFIG_FILE = "config.json"
CAM_FILE = "cam_list.json"
CAMIB_FILE = "camib_list.json"
STATS_FILE = "stats.json"

AUTO_DELETE_AFTER = 1


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log.error(f"Lỗi đọc {path}: {e}")
    return default


def save_json(path, data):
    try:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    except Exception as e:
        log.error(f"Lỗi ghi {path}: {e}")


config = load_json(CONFIG_FILE, {"delay": 0.1, "delay_soan": 2})
stats = load_json(STATS_FILE, {"sent": 0, "deleted_box": 0, "deleted_inbox": 0})
queue = asyncio.Queue()
processed = set()


def save_config():
    save_json(CONFIG_FILE, config)


def save_stats():
    save_json(STATS_FILE, stats)


async def auto_delete(*messages):
    await asyncio.sleep(AUTO_DELETE_AFTER)
    for msg in messages:
        if msg is None:
            continue
        try:
            await msg.delete()
        except Exception as e:
            log.error(f"Tự xóa lỗi | {e}")


async def reply_and_clean(event, text):
    reply = await event.reply(text)
    asyncio.create_task(auto_delete(event, reply))


async def sender_worker(client):
    while True:
        target, message, fake = await queue.get()
        try:
            if fake:
                entity = await client.get_entity(target)
                async with client.action(entity, "typing"):
                    await asyncio.sleep(config["delay_soan"])
            await client.send_message(target, message)
            stats["sent"] += 1
            save_stats()
            log.info(f"Gửi OK | target={target} | fake={fake}")
        except Exception as e:
            log.error(f"Gửi lỗi | target={target} | {e}")
        await asyncio.sleep(config["delay"])
        queue.task_done()


async def main():
    runner = await start_keepalive()

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.start(phone=PHONE)
    me = await client.get_me()
    log.info(f"Đăng nhập: {me.id} | @{me.username}")
    mark_running()

    asyncio.create_task(sender_worker(client))

    @client.on(events.NewMessage(incoming=True))
    async def incoming_handler(event):
        sender = event.sender_id
        if event.is_private and sender in load_json(CAMIB_FILE, []):
            try:
                await event.delete()
                stats["deleted_inbox"] += 1
                save_stats()
            except Exception as e:
                log.error(f"Xóa Inbox lỗi | id={sender} | {e}")
            return
        if not event.is_private and sender in load_json(CAM_FILE, []):
            try:
                await event.delete()
                stats["deleted_box"] += 1
                save_stats()
            except Exception as e:
                log.error(f"Xóa box lỗi | id={sender} | {e}")

    @client.on(events.NewMessage(outgoing=True))
    async def cmd_handler(event):
        if event.id in processed:
            return
        processed.add(event.id)
        text = event.raw_text.strip()
        if not text.startswith("/"):
            return
        cmd = text.split()[0].lower()
        try:
            if cmd == "/help":
                await reply_and_clean(
                    event,
                    "DANH SÁCH LỆNH:\n"
                    "/help /id /delay /delaysoan /gui /fakesoan\n"
                    "/cam /sua /camib /suaib /list /stats /clear /ping"
                )
            elif cmd == "/ping":
                await reply_and_clean(
                    event,
                    f"Running: {status['running']} | Last ping: {status['last_ping']}"
                )
            elif cmd == "/id":
                parts = text.split(maxsplit=1)
                if len(parts) == 1:
                    await reply_and_clean(event, f"ID của bạn: {me.id}")
                    return
                if event.is_reply:
                    replied = await event.get_reply_message()
                    s = await replied.get_sender()
                else:
                    s = await client.get_entity(parts[1].strip())
                await reply_and_clean(
                    event,
                    f"ID: {s.id} | @{getattr(s, 'username', '') or 'không có'}"
                )
            elif cmd == "/delay":
                config["delay"] = float(text.split()[1])
                save_config()
                await reply_and_clean(event, f"Delay: {config['delay']}s")
            elif cmd == "/delaysoan":
                config["delay_soan"] = float(text.split()[1])
                save_config()
                await reply_and_clean(event, f"Delay soạn: {config['delay_soan']}s")
            elif cmd == "/gui":
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], False))
                await reply_and_clean(event, "Đã vào hàng đợi")
            elif cmd == "/fakesoan":
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], True))
                await reply_and_clean(event, "Đã vào hàng đợi (fakesoan)")
            elif cmd in ("/cam", "/sua", "/camib", "/suaib"):
                target = int(text.split()[1])
                path = CAMIB_FILE if "ib" in cmd else CAM_FILE
                data = set(load_json(path, []))
                if cmd in ("/cam", "/camib"):
                    data.add(target)
                    action = "câm"
                else:
                    data.discard(target)
                    action = "tháo câm"
                save_json(path, list(data))
                await reply_and_clean(event, f"Đã {action} {target}")
            elif cmd == "/list":
                await reply_and_clean(
                    event,
                    f"BOX: {load_json(CAM_FILE, []) or 'trống'}\n"
                    f"INBOX: {load_json(CAMIB_FILE, []) or 'trống'}"
                )
            elif cmd == "/stats":
                await reply_and_clean(
                    event,
                    f"Gửi: {stats['sent']} | Xóa box: {stats['deleted_box']} | Xóa Inbox: {stats['deleted_inbox']}"
                )
            elif cmd == "/clear":
                save_json(CAM_FILE, [])
                save_json(CAMIB_FILE, [])
                await reply_and_clean(event, "Đã xóa danh sách cấm")
        except (IndexError, ValueError):
            await reply_and_clean(event, f"Cú pháp {cmd} không hợp lệ")
        except Exception as e:
            log.error(f"Lệnh lỗi | {cmd} | {e}")
            await reply_and_clean(event, f"Lỗi: {e}")

    log.info("Bot sẵn sàng")
    await client.run_until_disconnected()
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
