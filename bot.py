# bot.py - Bản full: login acc chính qua bot, lệnh chạy trên acc chính, mute/câm tự động, keepalive
# Yêu cầu: pip install telethon aiohttp

import asyncio
import json
import os
import logging
import time
import aiohttp
from telethon import TelegramClient, events
from telethon.sessions import MemorySession
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
API_ID = 39057925
API_HASH = "cbd2d21fce9a70d33f2baaf26cb5c12a"
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

config = {
    "delay": 0.1,
    "delay_soan": 2,
    "auto_delete": True,
    "cam_auto_delete": True,
}
stats = {
    "sent": 0,
    "deleted_box": 0,
    "deleted_inbox": 0,
    "commands": 0,
    "errors": 0,
}
queue = asyncio.Queue()
processed = set()
main_ref = {"client": None, "me": None, "started_at": None}

login_state = {
    "client": None,
    "phone": None,
    "phone_code_hash": None,
    "awaiting": None,
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


# ===== TỰ XÓA =====
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


async def delete_violation(event):
    if not config.get("cam_auto_delete", True):
        return
    try:
        await event.delete()
        log.info(f"Xóa vi phạm | id={event.sender_id} | msg={event.id}")
    except Exception as e:
        log.error(f"Xóa vi phạm lỗi: {e}")


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
    if not config.get("auto_delete", True):
        return
    await asyncio.sleep(AUTO_DELETE_AFTER)
    await bot_delete(chat_id, msg_id)
    if reply_id:
        await bot_delete(chat_id, reply_id)


# ===== SENDER =====
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
            stats["errors"] += 1
            save_json(STATS_FILE, stats)
            log.error(f"Gửi lỗi | {target} | {e}")
        await asyncio.sleep(config["delay"])
        queue.task_done()


# ===== XỬ LÝ MUTE/CÂM =====
async def cmd_mute(event, me, text):
    cmd = text.split()[0].lower()
    parts = text.split()
    if len(parts) < 2:
        await reply_clean(event, f"Cú pháp: {cmd} <id>")
        return
    try:
        target = int(parts[1])
    except ValueError:
        await reply_clean(event, f"ID không hợp lệ: {parts[1]}")
        return

    if cmd in ("/cam", "/camib"):
        path = CAMIB_FILE if cmd == "/camib" else CAM_FILE
        data = set(load_json(path, []))
        data.add(target)
        save_json(path, list(data))
        scope = "Inbox" if cmd == "/camib" else "Box"
        await reply_clean(event, f"Đã câm {scope}: {target}")
        log.info(f"CÂM {scope} | id={target}")
    else:
        path = CAMIB_FILE if cmd == "/suaib" else CAM_FILE
        data = set(load_json(path, []))
        if target in data:
            data.discard(target)
            save_json(path, list(data))
            scope = "Inbox" if cmd == "/suaib" else "Box"
            await reply_clean(event, f"Đã tháo câm {scope}: {target}")
        else:
            scope = "Inbox" if cmd == "/suaib" else "Box"
            await reply_clean(event, f"ID {target} không trong danh sách câm {scope}")


async def cmd_list(event):
    cam = load_json(CAM_FILE, [])
    camib = load_json(CAMIB_FILE, [])
    await reply_clean(
        event,
        f"DANH SÁCH CÂM:\n"
        f"BOX ({len(cam)}): {cam or 'trống'}\n"
        f"INBOX ({len(camib)}): {camib or 'trống'}"
    )


# ===== ATTACH HANDLERS =====
async def attach_user_client(client, via_bot=False):
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
            await delete_violation(event)
            stats["deleted_inbox"] += 1
            save_json(STATS_FILE, stats)
            return
        if not event.is_private and sender in load_json(CAM_FILE, []):
            await delete_violation(event)
            stats["deleted_box"] += 1
            save_json(STATS_FILE, stats)

    @client.on(events.NewMessage(outgoing=True))
    async def cmd_handler(event):
        if event.id in processed:
            return
        processed.add(event.id)
        text = event.raw_text.strip()
        if not text.startswith("/"):
            return
        if event.sender_id != me.id:
            asyncio.create_task(auto_delete(event))
            return

        stats["commands"] += 1
        save_json(STATS_FILE, stats)
        cmd = text.split()[0].lower()
        try:
            if cmd in ("/cam", "/sua", "/camib", "/suaib"):
                await cmd_mute(event, me, text)
            elif cmd == "/list":
                await cmd_list(event)
            elif cmd == "/help":
                await reply_clean(
                    event,
                    "LỆNH CHỦ ACC:\n"
                    "/cam <id>    - Câm box, tự xóa tin\n"
                    "/sua <id>    - Tháo câm box\n"
                    "/camib <id>  - Câm Inbox, tự xóa tin\n"
                    "/suaib <id>  - Tháo câm Inbox\n"
                    "/list        - Danh sách câm\n"
                    "/status /id /delay /autodel /camauto\n"
                    "/gui <target> <nd> /fakesoan <target> <nd>\n"
                    "/stats /reset"
                )
            elif cmd == "/status":
                await reply_clean(
                    event,
                    f"Kết nối: {client.is_connected()}\n"
                    f"Ủy quyền: {await client.is_user_authorized()}\n"
                    f"User: {me.id}\n"
                    f"Auto delete: {config['auto_delete']}\n"
                    f"Cam auto delete: {config['cam_auto_delete']}"
                )
            elif cmd == "/id":
                await reply_clean(event, f"User: {me.id} | Chat: {event.chat_id}")
            elif cmd == "/delay":
                config["delay"] = float(text.split()[1])
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Delay: {config['delay']}s")
            elif cmd == "/autodel":
                arg = text.split(maxsplit=1)[1].lower()
                config["auto_delete"] = (arg == "on")
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Auto delete: {config['auto_delete']}")
            elif cmd == "/camauto":
                arg = text.split(maxsplit=1)[1].lower()
                config["cam_auto_delete"] = (arg == "on")
                save_json(CONFIG_FILE, config)
                await reply_clean(event, f"Cam auto delete: {config['cam_auto_delete']}")
            elif cmd == "/gui":
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    await reply_clean(event, "Cú pháp: /gui <target> <nội dung>")
                    return
                await queue.put((parts[1], parts[2], False))
                await reply_clean(event, "Đã vào hàng đợi")
            elif cmd == "/fakesoan":
                parts = text.split(maxsplit=2)
                if len(parts) < 3:
                    await reply_clean(event, "Cú pháp: /fakesoan <target> <nội dung>")
                    return
                await queue.put((parts[1], parts[2], True))
                await reply_clean(event, "Đã vào hàng đợi")
            elif cmd == "/stats":
                await reply_clean(
                    event,
                    f"Gửi: {stats['sent']}\n"
                    f"Xóa box: {stats['deleted_box']}\n"
                    f"Xóa Inbox: {stats['deleted_inbox']}\n"
                    f"Lệnh: {stats['commands']}\n"
                    f"Lỗi: {stats['errors']}"
                )
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


# ===== LOGIN QUA BOT =====
async def do_login_start(chat_id, phone):
    old = login_state.get("client")
    if old:
        try:
            await old.disconnect()
        except Exception:
            pass
        login_state["client"] = None
    try:
        client = TelegramClient(MemorySession(), API_ID, API_HASH)
        await client.connect()
        sent = await client.send_code_request(phone)
        login_state["client"] = client
        login_state["phone"] = phone
        login_state["phone_code_hash"] = sent.phone_code_hash
        login_state["awaiting"] = "otp"
        login_state["last_error"] = None
        await bot_send(chat_id, f"Đã gửi OTP tới {phone}.\nGửi: /otp <mã> (có khoảng trắng)")
        log.info(f"Gửi OTP tới {phone}")
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
        await bot_send(chat_id, f"Đăng nhập OK: {me.id} | @{me.username}")
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
        await bot_send(chat_id, f"2FA OK: {me.id} | @{me.username}")
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
                    await bot_reply_clean(chat_id, msg_id, "Chưa gắn acc chính.")
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
