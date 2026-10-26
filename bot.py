# bot.py - Login acc chính qua Bot API chat, có xử lý OTP hết hạn và chia sẻ mã
# Yêu cầu: pip install telethon aiohttp
# Lưu ý: Telegram sẽ chặn nếu OTP xuất hiện trong chat. Bản này dùng cách nhập OTP dạng có khoảng trắng và cảnh báo rõ.

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
main_client_ref = {"client": None, "me": None, "started_at": None}

# Trạng thái đăng nhập qua bot
login_state = {
    "client": None,
    "phone": None,
    "phone_code_hash": None,
    "awaiting": None,  # None | "otp" | "2fa"
    "last_error": None,
    "last_login_at": None,
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
            log.error(f"LOCK tồn tại (pid={pid}). Instance khác đang chạy. Thoát.")
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


# ===== LOGIN QUA BOT =====
async def do_login_start(chat_id, phone):
    # Gửi OTP tới số điện thoại
    try:
        client = TelegramClient(f"login_{int(time.time())}", API_ID, API_HASH)
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
            f"Gửi: /otp <mã> với khoảng trắng giữa các số (vd: /otp 1 2 3 4 5)\n"
            f"Lưu ý: Telegram có thể chặn nếu mã xuất hiện trong chat."
        )
        log.info(f"Gửi OTP tới {phone}")
    except FloodWaitError as e:
        login_state["last_error"] = f"FloodWait {e.seconds}s"
        await bot_send(chat_id, f"Bị chặn FloodWait: chờ {e.seconds} giây")
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi gửi OTP: {e}")


async def do_login_otp(chat_id, code):
    # Xác nhận OTP
    client = login_state.get("client")
    phone = login_state.get("phone")
    if not client or login_state.get("awaiting") != "otp":
        await bot_send(chat_id, "Không có phiên OTP. Gửi /login <sdt> trước")
        return
    # Xóa khoảng trắng, gạch ngang, dấu chấm
    code = code.replace(" ", "").replace("-", "").replace(".", "")
    try:
        await client.sign_in(phone=phone, code=code, phone_code_hash=login_state["phone_code_hash"])
        login_state["awaiting"] = None
        login_state["last_login_at"] = time.time()
        me = await client.get_me()
        await bot_send(chat_id, f"Đăng nhập OK: {me.id} | @{me.username}")
        log.info(f"Login OK: {me.id}")
    except SessionPasswordNeededError:
        login_state["awaiting"] = "2fa"
        await bot_send(chat_id, "Cần 2FA. Gửi: /pass <matkhau>")
    except PhoneCodeInvalidError:
        login_state["last_error"] = "OTP sai"
        await bot_send(chat_id, "OTP sai")
    except PhoneCodeExpiredError:
        login_state["last_error"] = "OTP hết hạn"
        await bot_send(
            chat_id,
            "OTP hết hạn.\n"
            "Nguyên nhân: mã bị Telegram thu hồi do xuất hiện trong chat Telegram, hoặc nhập quá chậm.\n"
            "Cách xử lý: chờ 5-10 phút, chạy /login lại, nhập /otp có khoảng trắng ngay sau khi nhận."
        )
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi OTP: {e}")


async def do_login_pass(chat_id, password):
    # Xác nhận mật khẩu 2FA
    client = login_state.get("client")
    if not client or login_state.get("awaiting") != "2fa":
        await bot_send(chat_id, "Không có phiên 2FA")
        return
    try:
        await client.sign_in(password=password)
        login_state["awaiting"] = None
        login_state["last_login_at"] = time.time()
        me = await client.get_me()
        await bot_send(chat_id, f"2FA OK: {me.id} | @{me.username}")
        log.info(f"Login 2FA OK: {me.id}")
    except Exception as e:
        login_state["last_error"] = str(e)
        await bot_send(chat_id, f"Lỗi 2FA: {e}")


async def check_login_status():
    client = main_client_ref.get("client")
    lines = []
    if client is None:
        lines.append("Client: chưa khởi tạo")
    else:
        lines.append(f"Kết nối: {client.is_connected()}")
        try:
            lines.append(f"Ủy quyền: {await client.is_user_authorized()}")
        except Exception as e:
            lines.append(f"Ủy quyền: lỗi ({e})")
    me = main_client_ref.get("me")
    if me:
        lines.append(f"User: {me.id} | @{getattr(me, 'username', '') or 'không có'}")
        lines.append(f"Tên: {getattr(me, 'first_name', '') or ''} {getattr(me, 'last_name', '') or ''}".strip())
    started = main_client_ref.get("started_at")
    if started:
        lines.append(f"Uptime: {int(time.time() - started)}s")
    lines.append(f"Login bot: awaiting={login_state['awaiting']} | phone={login_state['phone']}")
    if login_state["last_error"]:
        lines.append(f"Lỗi: {login_state['last_error']}")
    return "\n".join(lines)


# ===== POLLING =====
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
                await bot_reply_clean(chat_id, msg_id, await check_login_status())
            elif text.startswith("/ping"):
                await bot_reply_clean(chat_id, msg_id, f"OK | ready={status['bot_ready']}")
            elif text.startswith("/id"):
                await bot_reply_clean(chat_id, msg_id, f"Chat: {chat_id} | User: {from_id}")
            elif text.startswith("/delay"):
                parts = text.split(maxsplit=1)
                if len(parts) < 2:
                    await bot_reply_clean(chat_id, msg_id, "Cú pháp: /delay <giây>")
                    continue
                try:
                    config["delay"] = float(parts[1])
                    save_json(CONFIG_FILE, config)
                    await bot_reply_clean(chat_id, msg_id, f"Delay: {config['delay']}s")
                except ValueError:
                    await bot_reply_clean(chat_id, msg_id, "Giá trị không hợp lệ")
            elif text.startswith("/stats"):
                await bot_reply_clean(chat_id, msg_id, f"Đã gửi: {stats['sent']}")
            elif text.startswith("/help"):
                await bot_reply_clean(
                    chat_id, msg_id,
                    "LỆNH ADMIN:\n"
                    "/login <sdt> - Gửi OTP\n"
                    "/otp <mã> - Xác nhận OTP (có khoảng trắng)\n"
                    "/pass <2fa> - Xác nhận 2FA\n"
                    "/status /ping /id /delay /stats"
                )
        await asyncio.sleep(0.5)


# ===== ACC CHÍNH TỪ SESSION =====
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


async def run_user_client():
    if not os.path.exists(f"{SESSION_NAME}.session"):
        log.warning(f"Không có {SESSION_NAME}.session — chỉ chạy Bot API, dùng /login để đăng nhập")
        mark_bot_ready()
        return
    try:
        client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
        await client.connect()
        if not await client.is_user_authorized():
            log.warning("Session chưa ủy quyền — chỉ chạy Bot API")
            mark_bot_ready()
            return
        me = await client.get_me()
        main_client_ref["client"] = client
        main_client_ref["me"] = me
        main_client_ref["started_at"] = time.time()
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

        log.info(f"Acc chính sẵn sàng | Admin: {ADMIN_IDS}")
        await client.run_until_disconnected()
    except Exception as e:
        log.error(f"Acc chính crash: {e}")
        mark_bot_ready()


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
