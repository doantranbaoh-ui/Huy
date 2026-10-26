# bot.py - Bot API login acc chính, sau đó lệnh chạy trên acc chính qua Telethon
# Yêu cầu: pip install telethon aiohttp
# Luồng: admin nhắn bot /login sdt -> /otp mã -> /pass 2fa -> bot gắn acc chính và chạy lệnh

import asyncio
import json
import os
import logging
import time
import aiohttp
from telethon import TelegramClient, events
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    PasswordHashInvalidError,
    FloodWaitError,
)

from keepalive import start_keepalive, mark_bot_ready, status

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.StreamHandler()],
)
log = logging.getLogger("bot")

# ===== CẤU HÌNH =====
API_ID = 27657608
API_HASH = "3b6e52a3713b44ad5adaa2bcf579de66"
SESSION_NAME = "acc_chinh"

BOT_TOKEN = "6367532329:AAF4F5XEYrdn121tbxmnxdHLDu7WzuePKkA"
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

ADMIN_IDS = {5736655322}

CONFIG_FILE = "config.json"
CAM_FILE = "cam_list.json"
CAMIB_FILE = "camib_list.json"
STATS_FILE = "stats.json"
LOCK_FILE = "acc_chinh.lock"
AUTO_DELETE_AFTER = 1

config = {"delay": 0.1, "delay_soan": 2}
stats = {"sent": 0, "deleted_box": 0, "deleted_inbox": 0}
queue = asyncio.Queue()
processed = set()
main_ref = {"client": None, "me": None, "started_at": None}

login_state = {
    "client": None,
    "phone": None,
    "phone_code_hash": None,
    "awaiting": None,  # None | "otp" | "2fa"
    "last_error": None,
}


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


# ===== BOT API =====
async def bot_send(chat_id, text):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": text}) as r:
                return await r.json()
    except Exception as e:
        log.error(f"bot_send lỗi: {e}")


async def bot_delete(chat_id, message_id):
    try:
        async with aiohttp.ClientSession() as s:
            await s.post(f"{BOT_API}/deleteMessage", json={"chat_id": chat_id, "message_id": message_id})
    except Exception as e:
        log.error(f"bot_delete lỗi: {e}")


async def bot_get_updates(offset=None, timeout=25):
    params = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(f"{BOT_API}/getUpdates", params=params, timeout=timeout + 10) as r:
                data = await r.json()
                return data.get("result", [])
    except Exception as e:
        log.error(f"getUpdates lỗi: {e}")
        return []


async def bot_reply_clean(chat_id, msg_id, text):
    resp = await bot_send(chat_id, text)
    reply_id = resp["result"]["message_id"] if resp and resp.get("ok") else None
    await asyncio.sleep(AUTO_DELETE_AFTER)
    await bot_delete(chat_id, msg_id)
    if reply_id:
        await bot_delete(chat_id, reply_id)


# ===== SENDER + HANDLERS ACC CHÍNH =====
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
        except FloodWaitError as e:
            log.error(f"FloodWait {e.seconds}s | {target}")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            log.error(f"Gửi lỗi | {target} | {e}")
        await asyncio.sleep(config["delay"])
        queue.task_done()


async def attach_user_client(client, via_bot=False):
    # Gắn acc chính vào bot, đăng ký handler, khởi động sender
    me = await client.get_me()
    main_ref["client"] = client
    main_ref["me"] = me
    main_ref["started_at"] = time.time()
    log.info(f"Acc chính: {me.id} | @{me.username} | via_bot={via_bot}")
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

    # Lệnh chạy trên acc chính, chỉ chủ acc
    @client.on(events.NewMessage(outgoing=True))
    async def cmd_handler(event):
        if event.id in processed:
            return
        processed.add(event.id)

        text = event.raw_text.strip()
        if not text.startswith("/"):
            return
        if event.sender_id != me.id:
            return

        cmd = text.split()[0].lower()
        try:
            if cmd == "/help":
                await event.reply(
                    "LỆNH ACC CHÍNH:\n"
                    "/status /id /delay <s>\n"
                    "/gui <target> <nd> /fakesoan <target> <nd>\n"
                    "/cam <id> /sua <id> /camib <id> /suaib <id>\n"
                    "/list /stats"
                )
            elif cmd == "/status":
                await event.reply(
                    f"Kết nối: {client.is_connected()}\n"
                    f"Ủy quyền: {await client.is_user_authorized()}\n"
                    f"User: {me.id} | @{getattr(me, 'username', '') or 'không có'}"
                )
            elif cmd == "/id":
                await event.reply(f"User: {me.id} | Chat: {event.chat_id}")
            elif cmd == "/delay":
                config["delay"] = float(text.split()[1])
                save_json(CONFIG_FILE, config)
                await event.reply(f"Delay: {config['delay']}s")
            elif cmd == "/gui":
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    await event.reply("Cú pháp: /gui <target> <nội dung>")
                    return
                await queue.put((parts[1], parts[2], False))
                await event.reply("Đã vào hàng đợi")
            elif cmd == "/fakesoan":
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    await event.reply("Cú pháp: /fakesoan <target> <nội dung>")
                    return
                await queue.put((parts[1], parts[2], True))
                await event.reply("Đã vào hàng đợi")
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
                    f"BOX: {load_json(CAM_FILE, [])}\nINBOX: {load_json(CAMIB_FILE, [])}"
                )
            elif cmd == "/stats":
                await event.reply(f"Gửi: {stats['sent']}")
        except Exception as e:
            log.error(f"Lệnh acc chính lỗi | {cmd} | {e}")

    log.info(f"Acc chính đã gắn, lệnh chạy trên acc chính | Admin bot: {ADMIN_IDS}")


# ===== LOGIN QUA BOT =====
async def do_login_start(chat_id, phone):
    try:
        # Dùng đúng SESSION_NAME để login xong là session chính
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        login_state["client"] = client
        login_state["phone"] = phone
        login_state["phone_code_hash"] = sent.phone_code_hash
        login_state["awaiting"] = "otp"
        login_state["last_error"] = None
        await bot_send(
            chat_id,
            f"Đã gửi OTP tới {phone}.\n"
            f"Gửi: /otp <mã> (có khoảng trắng: /otp 1 2 3 4 5)"
        )
        log.info(f"Gửi OTP tới {phone} | session={SESSION_NAME}")
    except FloodWaitError as e:
        login_state["last_error"] = f"FloodWait {e.seconds}s"
        await bot_send(chat_id, f"FloodWait: chờ {e.seconds} giây")
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi gửi OTP: {e}")


async def do_login_otp(chat_id, code):
    client = login_state.get("client")
    phone = login_state.get("phone")
    if not client or login_state.get("awaiting") != "otp":
        await bot_send(chat_id, "Không có phiên OTP. Gửi /login <sdt> trước")
        return
    code = code.replace(" ", "").replace("-", "").replace(".", "")
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=login_state["phone_code_hash"])
        login_state["awaiting"] = None
        me = await client.get_me()
        await bot_send(chat_id, f"Đăng nhập OK: {me.id} | @{me.username}\nAcc chính đã gắn, dùng lệnh trên acc chính.")
        log.info(f"Login OK: {me.id}")
        await attach_user_client(client, via_bot=True)
    except SessionPasswordNeededError:
        login_state["awaiting"] = "2fa"
        await bot_send(chat_id, "Cần 2FA. Gửi: /pass <matkhau>")
    except PhoneCodeInvalidError:
        login_state["last_error"] = "OTP sai"
        await bot_send(chat_id, "OTP sai")
    except PhoneCodeExpiredError:
        login_state["last_error"] = "OTP hết hạn"
        await bot_send(chat_id, "OTP hết hạn. Chờ 5-10 phút, chạy /login lại.")
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi OTP: {e}")


async def do_login_pass(chat_id, password):
    client = login_state.get("client")
    if not client or login_state.get("awaiting") != "2fa":
        await bot_send(chat_id, "Không có phiên 2FA")
        return
    try:
        await client.sign_in(password=password)
        login_state["awaiting"] = None
        me = await client.get_me()
        await bot_send(chat_id, f"2FA OK: {me.id} | @{me.username}\nAcc chính đã gắn.")
        log.info(f"Login 2FA OK: {me.id}")
        await attach_user_client(client, via_bot=True)
    except PasswordHashInvalidError:
        login_state["last_error"] = "2FA sai"
        await bot_send(chat_id, "Mật khẩu 2FA SAI. Thử lại /pass <matkhau>")
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi 2FA: {e}")


# ===== BOT POLLING =====
async def bot_polling():
    offset = None
    while True:
        updates = await bot_get_updates(offset=offset)
        for upd in updates:
            offset = upd["update_id"] + 1
            msg = upd.get("message")
            if not msg:
                continue
            chat_id = msg["chat"]["id"]
            from_id = msg["from"]["id"]
            msg_id = msg["message_id"]
            text = (msg.get("text") or "").strip()

            if from_id not in ADMIN_IDS:
                await bot_delete(chat_id, msg_id)
                continue

            if text.startswith("/login"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await bot_reply_clean(chat_id, msg_id, "Cú pháp: /login <sdt>")
                    continue
                await do_login_start(chat_id, parts[1].strip())
            elif text.startswith("/otp"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await bot_reply_clean(chat_id, msg_id, "Cú pháp: /otp <mã>")
                    continue
                await do_login_otp(chat_id, parts[1].strip())
            elif text.startswith("/pass"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await bot_reply_clean(chat_id, msg_id, "Cú pháp: /pass <matkhau>")
                    continue
                await do_login_pass(chat_id, parts[1].strip())
            elif text.startswith("/status"):
                client = main_ref.get("client")
                if client:
                    authorized = await client.is_user_authorized()
                    me = main_ref.get("me")
                    await bot_reply_clean(
                        chat_id, msg_id,
                        f"Acc chính: {me.id if me else 'chưa có'}\n"
                        f"Ủy quyền: {authorized}\n"
                        f"Login bot: awaiting={login_state['awaiting']}"
                    )
                else:
                    await bot_reply_clean(
                        chat_id, msg_id,
                        f"Chưa gắn acc chính. Login bot: awaiting={login_state['awaiting']}"
                    )
            elif text.startswith("/ping"):
                await bot_reply_clean(chat_id, msg_id, f"OK | ready={status['bot_ready']}")
            elif text.startswith("/help"):
                await bot_reply_clean(
                    chat_id, msg_id,
                    "LỆNH BOT:\n"
                    "/login <sdt> - Gửi OTP\n"
                    "/otp <mã> - Xác nhận OTP\n"
                    "/pass <2fa> - Xác nhận 2FA\n"
                    "/status /ping\n"
                    "Sau khi login: lệnh chạy trên acc chính."
                )
        await asyncio.sleep(0.5)


# ===== KHỞI ĐỘNG =====
async def run_user_client():
    # Nếu đã có session sẵn, gắn acc chính ngay
    if not os.path.exists(f"{SESSION_NAME}.session"):
        log.warning(f"Không có {SESSION_NAME}.session — chờ /login qua bot")
        return
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log.warning("Session chưa ủy quyền — chờ /login qua bot")
            return
        await attach_user_client(client, via_bot=False)
        await client.run_until_disconnected()
    except Exception as e:
        log.error(f"Acc chính crash: {e}")


async def main():
    if not acquire_lock():
        log.error("Không lấy được lock. Thoát.")
        return
    try:
        runner = await start_keepalive()
        tasks = [
            asyncio.create_task(run_user_client()),
            asyncio.create_task(bot_polling()),
        ]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            pass
        finally:
            await runner.cleanup()
    finally:
        release_lock()


if __name__ == "__main__":
    asyncio.run(main())
