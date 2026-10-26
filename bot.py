# bot.py - Bổ sung lệnh /status kiểm tra trạng thái login, chỉ admin 5736655322
# Yêu cầu: pip install telethon aiohttp

import asyncio
import json
import os
import logging
import time
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

from keepalive import start_keepalive, mark_bot_ready, status

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

BOT_TOKEN = "6367532329:AAF4F5XEYrdn121tbxmnxdHLDu7WzuePKkA"

ADMIN_IDS = {5736655322}

CONFIG_FILE = "config.json"
CAM_FILE = "cam_list.json"
CAMIB_FILE = "camib_list.json"
STATS_FILE = "stats.json"
AUTO_DELETE_AFTER = 1

config = {"delay": 0.1, "delay_soan": 2}
stats = {"sent": 0, "deleted_box": 0, "deleted_inbox": 0}
queue = asyncio.Queue()
processed = set()

# Trạng thái đăng nhập
login_state = {
    "client": None,
    "phone": None,
    "phone_code_hash": None,
    "awaiting": None,       # None | "otp" | "2fa"
    "last_login_at": None,  # timestamp đăng nhập thành công gần nhất
    "last_error": None,     # lỗi gần nhất
}

# Tham chiếu client chính đang chạy (dùng cho /status)
main_client_ref = {"client": None, "me": None, "started_at": None}


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


def is_admin(event):
    return event.sender_id in ADMIN_IDS


async def auto_delete(*messages):
    await asyncio.sleep(AUTO_DELETE_AFTER)
    for msg in messages:
        if msg is None:
            continue
        try:
            await msg.delete()
        except Exception:
            pass


async def reply_and_clean(event, text):
    reply = await event.reply(text)
    asyncio.create_task(auto_delete(event, reply))


async def check_login_status():
    # Kiểm tra trạng thái client chính: kết nối, ủy quyền, thông tin user
    client = main_client_ref.get("client")
    if client is None:
        return "Client: chưa khởi tạo"
    lines = []
    lines.append(f"Kết nối: {client.is_connected()}")
    try:
        authorized = await client.is_user_authorized()
    except Exception as e:
        authorized = f"lỗi ({e})"
    lines.append(f"Ủy quyền: {authorized}")

    me = main_client_ref.get("me")
    if me:
        lines.append(f"User: {me.id} | @{getattr(me, 'username', '') or 'không có'}")
        lines.append(f"Tên: {getattr(me, 'first_name', '') or ''} {getattr(me, 'last_name', '') or ''}".strip())
    else:
        lines.append("User: chưa có")

    started = main_client_ref.get("started_at")
    if started:
        uptime = int(time.time() - started)
        lines.append(f"Uptime: {uptime}s")

    # Trạng thái phiên login tạm
    lines.append(f"Login tạm: awaiting={login_state['awaiting']} | phone={login_state['phone']}")
    if login_state["last_login_at"]:
        lines.append(f"Login gần nhất: {int(time.time() - login_state['last_login_at'])}s trước")
    if login_state["last_error"]:
        lines.append(f"Lỗi gần nhất: {login_state['last_error']}")
    return "\n".join(lines)


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
        except Exception as e:
            log.error(f"Gửi lỗi: {e}")
        await asyncio.sleep(config["delay"])
        queue.task_done()


async def cmd_login(event, text):
    parts = text.split()
    if len(parts) < 3:
        await reply_and_clean(event, "Cú pháp: /login <sdt> <otp> [matkhau2fa]")
        return
    phone = parts[1]
    otp = parts[2]
    password_2fa = parts[3] if len(parts) > 3 else None
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        login_state["client"] = client
        login_state["phone"] = phone
        login_state["phone_code_hash"] = sent.phone_code_hash
        login_state["awaiting"] = "otp"
        try:
            await client.sign_in(phone=phone, code=otp, phone_code_hash=sent.phone_code_hash)
            login_state["awaiting"] = None
            login_state["last_login_at"] = time.time()
            login_state["last_error"] = None
            me = await client.get_me()
            await reply_and_clean(event, f"Đăng nhập OK: {me.id}")
        except SessionPasswordNeededError:
            if not password_2fa:
                login_state["awaiting"] = "2fa"
                await reply_and_clean(event, "Cần 2FA. Gửi: /login2fa <matkhau>")
                return
            await client.sign_in(password=password_2fa)
            login_state["awaiting"] = None
            login_state["last_login_at"] = time.time()
            login_state["last_error"] = None
            me = await client.get_me()
            await reply_and_clean(event, f"Đăng nhập 2FA OK: {me.id}")
        except PhoneCodeInvalidError:
            login_state["last_error"] = "OTP sai"
            await reply_and_clean(event, "OTP sai")
        except PhoneCodeExpiredError:
            login_state["last_error"] = "OTP hết hạn"
            await reply_and_clean(event, "OTP hết hạn")
    except Exception as e:
        login_state["last_error"] = str(e)
        log.error(f"Login lỗi: {e}")
        await reply_and_clean(event, f"Lỗi: {e}")


async def cmd_login2fa(event, text):
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await reply_and_clean(event, "Cú pháp: /login2fa <matkhau>")
        return
    client = login_state.get("client")
    if client is None or login_state.get("awaiting") != "2fa":
        await reply_and_clean(event, "Không có phiên chờ 2FA")
        return
    try:
        await client.sign_in(password=parts[1].strip())
        login_state["awaiting"] = None
        login_state["last_login_at"] = time.time()
        login_state["last_error"] = None
        me = await client.get_me()
        await reply_and_clean(event, f"2FA OK: {me.id}")
    except Exception as e:
        login_state["last_error"] = str(e)
        await reply_and_clean(event, f"Lỗi 2FA: {e}")


async def run_bot():
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.start(phone=PHONE)
        me = await client.get_me()
        main_client_ref["client"] = client
        main_client_ref["me"] = me
        main_client_ref["started_at"] = time.time()
        login_state["last_login_at"] = time.time()
        log.info(f"Đăng nhập: {me.id} | @{me.username}")
        mark_bot_ready()

        asyncio.create_task(sender_worker(client))

        @client.on(events.NewMessage(incoming=True))
        async def incoming_handler(event):
            sender = event.sender_id
            if event.is_private and sender in load_json(CAMIB_FILE, []):
                try:
                    await event.delete()
                except Exception:
                    pass
                return
            if not event.is_private and sender in load_json(CAM_FILE, []):
                try:
                    await event.delete()
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

            if not is_admin(event):
                log.warning(f"Từ chối lệnh từ id={event.sender_id}")
                asyncio.create_task(auto_delete(event))
                return

            cmd = text.split()[0].lower()
            try:
                if cmd == "/help":
                    await reply_and_clean(
                        event,
                        "LỆNH ADMIN:\n"
                        "/status - Trạng thái login hiện tại\n"
                        "/login <sdt> <otp> [2fa]\n"
                        "/login2fa <matkhau>\n"
                        "/id /delay /delaysoan /gui /fakesoan\n"
                        "/cam /sua /camib /suaib /list /stats /clear /ping"
                    )
                elif cmd == "/status":
                    await reply_and_clean(event, await check_login_status())
                elif cmd == "/login":
                    await cmd_login(event, text)
                elif cmd == "/login2fa":
                    await cmd_login2fa(event, text)
                elif cmd == "/ping":
                    await reply_and_clean(event, f"Bot: {status['bot_ready']} | Running: {status['running']}")
                elif cmd == "/id":
                    await reply_and_clean(event, f"ID: {me.id} | Admin: {event.sender_id in ADMIN_IDS}")
                elif cmd == "/delay":
                    config["delay"] = float(text.split()[1])
                    save_json(CONFIG_FILE, config)
                    await reply_and_clean(event, f"Delay: {config['delay']}s")
                elif cmd == "/delaysoan":
                    config["delay_soan"] = float(text.split()[1])
                    save_json(CONFIG_FILE, config)
                    await reply_and_clean(event, f"Soạn: {config['delay_soan']}s")
                elif cmd == "/gui":
                    parts = text.split(maxsplit=2)
                    await queue.put((parts[1], parts[2], False))
                    await reply_and_clean(event, "Đã vào hàng đợi")
                elif cmd == "/fakesoan":
                    parts = text.split(maxsplit=2)
                    await queue.put((parts[1], parts[2], True))
                    await reply_and_clean(event, "Đã vào hàng đợi")
                elif cmd in ("/cam", "/sua", "/camib", "/suaib"):
                    target = int(text.split()[1])
                    path = CAMIB_FILE if "ib" in cmd else CAM_FILE
                    data = set(load_json(path, []))
                    if cmd in ("/cam", "/camib"):
                        data.add(target)
                    else:
                        data.discard(target)
                    save_json(path, list(data))
                    await reply_and_clean(event, f"OK {target}")
                elif cmd == "/list":
                    await reply_and_clean(event, f"BOX: {load_json(CAM_FILE, [])} | INBOX: {load_json(CAMIB_FILE, [])}")
                elif cmd == "/stats":
                    await reply_and_clean(event, f"Gửi: {stats['sent']}")
                elif cmd == "/clear":
                    save_json(CAM_FILE, [])
                    save_json(CAMIB_FILE, [])
                    await reply_and_clean(event, "Đã xóa")
            except Exception as e:
                await reply_and_clean(event, f"Lỗi: {e}")

        log.info(f"Bot sẵn sàng | Admin: {ADMIN_IDS}")
        await client.run_until_disconnected()
    except Exception as e:
        login_state["last_error"] = str(e)
        log.error(f"Bot crash: {e}")
        raise


async def main():
    runner = await start_keepalive()
    bot_task = asyncio.create_task(run_bot())
    try:
        await bot_task
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
