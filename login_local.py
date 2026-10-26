# login_local.py - Đăng nhập acc chính trên máy local, tạo session cho bot.py
# Yêu cầu: pip install telethon
# Chạy: python login_local.py
# Sau khi xong: copy acc_chinh.session lên Render

import asyncio
import os
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError, PhoneCodeExpiredError

# ===== CẤU HÌNH =====
API_ID = 12345678
API_HASH = "your_api_hash_here"      # điền hash thật
SESSION_NAME = "acc_chinh"           # tên file session, bot.py dùng cùng tên
PHONE = "+84123456789"               # số điện thoại acc chính


async def main():
    print(f"[LOGIN] Khởi tạo client | session={SESSION_NAME} | phone={PHONE}")
    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
    await client.connect()

    # Nếu session đã tồn tại và ủy quyền, bỏ qua đăng nhập
    if await client.is_user_authorized():
        me = await client.get_me()
        print(f"[LOGIN] Session đã ủy quyền: {me.id} | @{me.username}")
        await client.disconnect()
        return

    # Gửi yêu cầu OTP tới số điện thoại
    try:
        sent = await client.send_code_request(PHONE)
        print(f"[LOGIN] Đã gửi OTP tới {PHONE}")
        print(f"[LOGIN] phone_code_hash: {sent.phone_code_hash}")
    except Exception as e:
        print(f"[LOGIN] Lỗi gửi OTP: {e}")
        await client.disconnect()
        return

    # Nhập OTP từ bàn phím local — KHÔNG qua chat Telegram
    otp = input("[LOGIN] Nhập OTP: ").strip()

    try:
        await client.sign_in(phone=PHONE, code=otp, phone_code_hash=sent.phone_code_hash)
        me = await client.get_me()
        print(f"[LOGIN] Đăng nhập OK: {me.id} | @{me.username}")
    except SessionPasswordNeededError:
        # Tài khoản bật 2FA
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
        print("[LOGIN] OTP hết hạn")
        await client.disconnect()
        return
    except Exception as e:
        print(f"[LOGIN] Lỗi: {e}")
        await client.disconnect()
        return

    await client.disconnect()
    session_file = f"{SESSION_NAME}.session"
    if os.path.exists(session_file):
        size = os.path.getsize(session_file)
        print(f"[LOGIN] Session đã lưu: {session_file} ({size} bytes)")
        print("[LOGIN] Upload file này lên Render qua Persistent Disk hoặc Shell")
    else:
        print("[LOGIN] Cảnh báo: không tìm thấy file session")


if __name__ == "__main__":
    asyncio.run(main())
