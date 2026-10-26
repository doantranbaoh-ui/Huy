# bot_full.py - Bản tích hợp keepalive
# Yêu cầu: pip install telethon aiohttp

import asyncio
import json
import os
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession

# Import module keepalive
from keepalive import start_keepalive, mark_running, status

# ===== LOGGING =====
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("bot")

# ===== BIẾN MÔI TRƯỜNG =====
API_ID = int(os.environ.get("API_ID", "0"))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

if not API_ID or not API_HASH or not SESSION_STRING:
    log.error("Thiếu API_ID, API_HASH hoặc SESSION_STRING")
    raise SystemExit(1)

CONFIG_FILE = "config.json"
CAM_FILE = "cam_list.json"
CAMIB_FILE = "camib_list.json"
STATS_FILE = "stats.json"


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
    # Khởi động keepalive TRƯỚC để Render không timeout healthcheck
    runner = await start_keepalive()

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.start()
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
                await event.reply(
                    "DANH SÁCH LỆNH:\n"
                    "/help /id /delay /delaysoan /gui /fakesoan\n"
                    "/cam /sua /camib /suaib /list /stats /clear /ping"
                )
            elif cmd == "/ping":
                # Trả về trạng thái keepalive
                await event.reply(
                    f"Running: {status['running']}\n"
                    f"Last ping: {status['last_ping']}"
                )
            elif cmd == "/id":
                parts = text.split(maxsplit=1)
                if len(parts) == 1:
                    await event.reply(f"ID của bạn: {me.id}")
                    return
                if event.is_reply:
                    replied = await event.get_reply_message()
                    s = await replied.get_sender()
                else:
                    s = await client.get_entity(parts[1].strip())
                await event.reply(f"ID: {s.id} | @{getattr(s, 'username', '') or 'không có'}")
            elif cmd == "/delay":
                config["delay"] = float(text.split()[1])
                save_config()
                await event.reply(f"Delay: {config['delay']}s")
            elif cmd == "/delaysoan":
                config["delay_soan"] = float(text.split()[1])
                save_config()
                await event.reply(f"Delay soạn: {config['delay_soan']}s")
            elif cmd == "/gui":
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], False))
                await event.reply("Đã vào hàng đợi")
            elif cmd == "/fakesoan":
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], True))
                await event.reply("Đã vào hàng đợi (fakesoan)")
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
                await event.reply(f"Đã {action} {target}")
            elif cmd == "/list":
                await event.reply(
                    f"BOX: {load_json(CAM_FILE, []) or 'trống'}\n"
                    f"INBOX: {load_json(CAMIB_FILE, []) or 'trống'}"
                )
            elif cmd == "/stats":
                await event.reply(
                    f"Gửi: {stats['sent']} | Xóa box: {stats['deleted_box']} | Xóa Inbox: {stats['deleted_inbox']}"
                )
            elif cmd == "/clear":
                save_json(CAM_FILE, [])
                save_json(CAMIB_FILE, [])
                await event.reply("Đã xóa danh sách cấm")
        except (IndexError, ValueError):
            await event.reply(f"Cú pháp {cmd} không hợp lệ")
        except Exception as e:
            log.error(f"Lệnh lỗi | {cmd} | {e}")
            await event.reply(f"Lỗi: {e}")

    log.info("Bot sẵn sàng")
    await client.run_until_disconnected()
    # Dừng keepalive khi bot ngắt
    await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
