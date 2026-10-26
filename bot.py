# bot.py - Bản cải tiến full: acc chính, chỉ chủ acc dùng lệnh, keepalive, lock, log, stats, tự xóa
# Yêu cầu: pip install telethon aiohttp

import asyncio
import json
import os
import logging
import time
from logging.handlers import RotatingFileHandler
from telethon import TelegramClient, events
from telethon.errors import FloodWaitError

from keepalive import start_keepalive, mark_bot_ready, status

# ===== LOGGING NÂNG CAO =====
log = logging.getLogger("bot")
log.setLevel(logging.INFO)
fmt = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
console = logging.StreamHandler()
console.setFormatter(fmt)
fileh = RotatingFileHandler("bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8")
fileh.setFormatter(fmt)
log.addHandler(console)
log.addHandler(fileh)

# ===== CẤU HÌNH =====
API_ID = 12345678
API_HASH = "your_api_hash_here"
SESSION_NAME = "acc_chinh"

CONFIG_FILE = "config.json"
CAM_FILE = "cam_list.json"
CAMIB_FILE = "camib_list.json"
STATS_FILE = "stats.json"
LOCK_FILE = "acc_chinh.lock"
AUTO_DELETE_AFTER = 1
MAX_QUEUE = 1000

config = {
    "delay": 0.1,
    "delay_soan": 2,
    "auto_delete": True,
    "self_destruct": True,
}
stats = {
    "sent": 0,
    "deleted_box": 0,
    "deleted_inbox": 0,
    "commands": 0,
    "errors": 0,
}
queue = asyncio.Queue(maxsize=MAX_QUEUE)
processed = set()
main_ref = {"client": None, "me": None, "started_at": None}


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


config = load_json(CONFIG_FILE, config)
stats = load_json(STATS_FILE, stats)


def acquire_lock():
    if os.path.exists(LOCK_FILE):
        try:
            with open(LOCK_FILE, "r") as f:
                pid = f.read().strip()
            log.error(f"LOCK tồn tại (pid={pid}). Thoát.")
            return False
        except Exception:
            pass
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        return True
    except Exception as e:
        log.error(f"Không tạo được lock: {e}")
        return False


def release_lock():
    try:
        if os.path.exists(LOCK_FILE):
            os.remove(LOCK_FILE)
    except Exception:
        pass


async def auto_delete(*messages):
    if not config.get("auto_delete", True):
        return
    await asyncio.sleep(AUTO_DELETE_AFTER)
    for msg in messages:
        if msg is None:
            continue
        try:
            await msg.delete()
        except Exception:
            pass


async def reply_clean(event, text):
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
            save_json(STATS_FILE, stats)
            log.info(f"Gửi OK | {target} | fake={fake}")
        except FloodWaitError as e:
            log.error(f"FloodWait {e.seconds}s | {target}")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            stats["errors"] += 1
            save_json(STATS_FILE, stats)
            log.error(f"Gửi lỗi | {target} | {e}")
        await asyncio.sleep(config["delay"])
        queue.task_done()


async def check_status():
    client = main_ref.get("client")
    if client is None:
        return "Client: chưa khởi tạo"
    lines = []
    lines.append(f"Kết nối: {client.is_connected()}")
    try:
        lines.append(f"Ủy quyền: {await client.is_user_authorized()}")
    except Exception as e:
        lines.append(f"Ủy quyền: lỗi ({e})")
    me = main_ref.get("me")
    if me:
        lines.append(f"User: {me.id} | @{getattr(me, 'username', '') or 'không có'}")
    started = main_ref.get("started_at")
    if started:
        lines.append(f"Uptime: {int(time.time() - started)}s")
    lines.append(f"Queue: {queue.qsize()}/{MAX_QUEUE}")
    lines.append(f"Delay: {config['delay']}s | Soạn: {config['delay_soan']}s")
    return "\n".join(lines)


async def attach_handlers(client):
    me = await client.get_me()
    main_ref["client"] = client
    main_ref["me"] = me
    main_ref["started_at"] = time.time()
    log.info(f"Acc chính: {me.id} | @{me.username}")
    mark_bot_ready()

    asyncio.create_task(sender_worker(client))

    @client.on(events.NewMessage(incoming=True))
    async def incoming_handler(event):
        sender = event.sender_id
        if event.is_private and sender in load_json(CAMIB_FILE, []):
            try:
                await event.delete()
                stats["deleted_inbox"] += 1
                save_json(STATS_FILE, stats)
            except Exception:
                pass
            return
        if not event.is_private and sender in load_json(CAM_FILE, []):
            try:
                await event.delete()
                stats["deleted_box"] += 1
                save_json(STATS_FILE, stats)
            except Exception:
                pass

    @client.on(events.NewMessage(outgoing=True))
    async def cmd_handler(event):
        if event.id in processed:
            return
        processed.add(event.id)

        text = event.raw_text.strip()
        if not text.startswith("/"):
            return

        # Chỉ chủ acc
        if event.sender_id != me.id:
            asyncio.create_task(auto_delete(event))
            log.warning(f"Từ chối lệnh id={event.sender_id}")
            return

        stats["commands"] += 1
        save_json(STATS_FILE, stats)

        cmd = text.split()[0].lower()
        try:
            if cmd == "/help":
                await reply_clean(
                    event,
                    "LỆNH CHỦ ACC:\n"
                    "/status /ping /id /info\n"
                    "/delay <s> /delaysoan <s>\n"
                    "/autodel on|off /selfdestruct on|off\n"
                    "/gui <target> <nd>\n"
                    "/fakesoan <target> <nd>\n"
                    "/cam <id> /sua <id>\n"
                    "/camib <id> /suaib <id>\n"
                    "/list /stats /clear /reset"
                )
            elif cmd == "/status":
                await reply_clean(event, await check_status())
            elif cmd == "/ping":
                await reply_clean(event, f"OK | queue={queue.qsize()}")
            elif cmd == "/id":
                await reply_clean(event, f"User: {me.id} | Chat: {event.chat_id}")
            elif cmd == "/info":
                await reply_clean(
                    event,
                    f"API_ID: {API_ID}\n"
                    f"Session: {SESSION_NAME}\n"
                    f"Auto delete: {config['auto_delete']}\n"
                    f"Self destruct: {config['self_destruct']}"
                )
            elif cmd == "/delay":
                config["delay"] = float(text.split()[1])
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Delay: {config['delay']}s")
            elif cmd == "/delaysoan":
                config["delay_soan"] = float(text.split()[1])
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Soạn: {config['delay_soan']}s")
            elif cmd == "/autodel":
                arg = text.split(maxsplit=1)[1].lower()
                config["auto_delete"] = (arg == "on")
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Auto delete: {config['auto_delete']}")
            elif cmd == "/selfdestruct":
                arg = text.split(maxsplit=1)[1].lower()
                config["self_destruct"] = (arg == "on")
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Self destruct: {config['self_destruct']}")
            elif cmd == "/gui":
                if queue.full():
                    await reply_clean(event, "Queue đầy")
                    continue
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], False))
                await reply_clean(event, "Đã vào hàng đợi")
            elif cmd == "/fakesoan":
                if queue.full():
                    await reply_clean(event, "Queue đầy")
                    continue
                parts = text.split(maxsplit=2)
                await queue.put((parts[1], parts[2], True))
                await reply_clean(event, "Đã vào hàng đợi")
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
                await reply_clean(event, f"Đã {action} {target}")
            elif cmd == "/list":
                await reply_clean(
                    event,
                    f"BOX: {load_json(CAM_FILE, [])}\nINBOX: {load_json(CAMIB_FILE, [])}"
                )
            elif cmd == "/stats":
                await reply_clean(
                    event,
                    f"Gửi: {stats['sent']}\n"
                    f"Xóa box: {stats['deleted_box']}\n"
                    f"Xóa Inbox: {stats['deleted_inbox']}\n"
                    f"Lệnh: {stats['commands']}\n"
                    f"Lỗi: {stats['errors']}"
                )
            elif cmd == "/clear":
                save_json(CAM_FILE, [])
                save_json(CAMIB_FILE, [])
                await reply_clean(event, "Đã xóa danh sách cấm")
            elif cmd == "/reset":
                for k in stats:
                    stats[k] = 0
                save_json(STATS_FILE, stats)
                await reply_clean(event, "Đã reset thống kê")
        except (IndexError, ValueError):
            await reply_clean(event, f"Cú pháp {cmd} không hợp lệ")
        except Exception as e:
            stats["errors"] += 1
            save_json(STATS_FILE, stats)
            log.error(f"Lệnh lỗi | {cmd} | {e}")
            await reply_clean(event, f"Lỗi: {e}")


async def run_user_client():
    if not os.path.exists(f"{SESSION_NAME}.session"):
        log.error(f"Không có {SESSION_NAME}.session — chạy login_local.py trước")
        return
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log.error("Session chưa ủy quyền — chạy login_local.py lại")
            return
        await attach_handlers(client)
        log.info("Acc chính sẵn sàng — chỉ chủ acc dùng lệnh")
        await client.run_until_disconnected()
    except Exception as e:
        stats["errors"] += 1
        save_json(STATS_FILE, stats)
        log.error(f"Acc chính crash: {e}")


async def main():
    if not acquire_lock():
        log.error("Không lấy được lock. Thoát.")
        return
    try:
        runner = await start_keepalive()
        try:
            await run_user_client()
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
    finally:
        release_lock()


if __name__ == "__main__":
    asyncio.run(main())
