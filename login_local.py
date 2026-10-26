# login_local.py - Sửa: nhập OTP có khoảng trắng để tránh Telegram phát hiện chia sẻ
# Yêu cầu: pip install telethon
# Chạy: python login_local.py

import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

API_ID = 39057925
API_HASH = "cbd2d21fce9a70d33f2baaf26cb5c12a"
SESSION_NAME = "acc_chinh"
PHONE = "+84123456789"


async def main():
    print(f"[LOGIN] session={SESSION_NAME} | phone={PHONE}")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"[LOGIN] Session đã ủy quyền: {me.id} | @{me.username}")
        await client.disconnect()
        return

    # Xóa session cũ nếu có để tránh xung đột
    old_session = f"{SESSION_NAME}.session"
    if os.path.exists(old_session):
        try:
            os.remove(old_session)
            print(f"[LOGIN] Đã xóa session cũ: {old_session}")
        except Exception as e:
            print(f"[LOGIN] Không xóa được session cũ: {e}")

    # Gửi OTP mới
    try:
        sent = await client.send_code_request(PHONE)
        print(f"[LOGIN] Đã gửi OTP tới {PHONE}")
    except Exception as e:
        print(f"[LOGIN] Lỗi gửi OTP: {e}")
        await client.disconnect()
        return

    # QUAN TRỌNG: nhập OTP có khoảng trắng giữa các số
    # Ví dụ: 1 2 3 4 5 thay vì 12345
    print("[LOGIN] Nhập OTP có khoảng trắng giữa các số (vd: 1 2 3 4 5)")
    raw = input("[LOGIN] OTP: ").strip()
    # Loại bỏ khoảng trắng, gạch ngang, dấu chấm trước khi gửi
    otp = raw.replace(" ", "").replace("-", "").replace(".", "")

    try:
        await client.sign_in(phone=PHONE, code=otp, phone_code_hash=sent.phone_code_hash)
        me = await client.get_me()
        print(f"[LOGIN] Đăng nhập OK: {me.id} | @{me.username}")
    except SessionPasswordNeededError:
        pwd = input("[LOGIN] Nhập mật khẩu 2FA: ").strip()
        try:
            await client.sign_in(password=pwd)
            me = await client.get_me()
            print(f"[LOGIN] 2FA OK: {me.id} | @{me.username}")
        except Exception as e:
            print(f"[LOGIN] Lỗi 2FA: {e}")
            await client.disconnect()
            return
    except PhoneCodeInvalidError:
        print("[LOGIN] OTP sai")
        await client.disconnect()
        return
    except PhoneCodeExpiredError:
        print("[LOGIN] OTP hết hạn — chờ 5-10 phút rồi chạy lại")
        await client.disconnect()
        return
    except Exception as e:
        print(f"[LOGIN] Lỗi: {e}")
        await client.disconnect()
        return

    await client.disconnect()
    print(f"[LOGIN] Session đã lưu: {SESSION_NAME}.session")


if __name__ == "__main__":
    asyncio.run(main())
