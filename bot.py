#!/usr/bin/env python3
import json, os, time, uuid, hashlib, logging
from datetime import datetime, timedelta
import telebot
from telebot import types

BOT_TOKEN = "6320148381:AAHKLMaGycWIv8sxdBU6sAmgOPn2XlqTIx0"
CHAT_ID = "-1003925717296"
ADMIN_IDS = [5736655322]
DB_FILE = "keys.json"
BAN_FILE = "bans.json"
CONFIG_FILE = "config.json"
LOG_FILE = "bot.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load {path} error: {e}")
    return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save {path} error: {e}")

db = load_json(DB_FILE, {
    "keys": {},
    "approved": {},
    "kicked": {},
    "logs": [],
    "devices": {},
    "stats": {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
})
bans = load_json(BAN_FILE, {"banned_ips": [], "banned_uids": [], "banned_devices": []})
config = load_json(CONFIG_FILE, {
    "auto_approve": True,
    "key_expiry_days": 30,
    "max_devices_per_key": 1,
    "notify_admin": True,
    "maintenance": False
})

def save_db():
    save_json(DB_FILE, db)

def save_bans():
    save_json(BAN_FILE, bans)

def save_config():
    save_json(CONFIG_FILE, config)

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{ts}] {msg}"
    db["logs"].append(entry)
    db["logs"] = db["logs"][-500:]
    logger.info(msg)
    save_db()

def is_admin(uid):
    return uid in ADMIN_IDS

def is_banned(uid, ip=None, device=None):
    banned_uids = [x.get("uid") if isinstance(x, dict) else x for x in bans["banned_uids"]]
    banned_ips = [x.get("ip") if isinstance(x, dict) else x for x in bans["banned_ips"]]
    banned_devices = [x.get("device") if isinstance(x, dict) else x for x in bans["banned_devices"]]
    return uid in banned_uids or (ip and ip in banned_ips) or (device and device in banned_devices)

def gen_key(prefix, ktype, days=30):
    code = hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:24]
    k = f"{prefix}-{ktype}-{code}"
    exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    db["keys"][k] = {
        "type": ktype,
        "prefix": prefix,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expires": exp,
        "used": False,
        "udid": None,
        "device": None,
        "ip": None,
        "activations": 0,
        "max_activations": config["max_devices_per_key"]
    }
    db["stats"]["total_keys"] += 1
    save_db()
    return k

bot = telebot.TeleBot(BOT_TOKEN, threaded=False, skip_pending=True)

@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    bot.reply_to(msg, f"👋 Chào mừng!\n👤 ID của bạn: `{uid}`\nGửi key để kích hoạt hoặc dùng /help để xem lệnh.", parse_mode="Markdown")

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    try:
        uid = str(msg.from_user.id)
        text = msg.text.strip() if msg.text else ""
        
        if is_banned(uid):
            bot.reply_to(msg, "⛔ Bạn đã bị cấm sử dụng bot.")
            return
        
        if config["maintenance"] and not is_admin(msg.from_user.id):
            bot.reply_to(msg, "🔧 Bot đang bảo trì. Vui lòng thử lại sau.")
            return
        
        # Skip commands
        if text.startswith('/'):
            return
        
        # Dylib auto-approve
        if "#KichHoat" in text or "#Start" in text or "#YeuCau" in text:
            device_uid = None
            for part in text.split():
                if part.startswith("UID:") or part.startswith("UDID:"):
                    device_uid = part.split(":", 1)[1]
            if device_uid:
                if not config["auto_approve"]:
                    bot.reply_to(msg, "⏳ Chờ admin duyệt...")
                    if config["notify_admin"]:
                        for admin in ADMIN_IDS:
                            try:
                                bot.send_message(admin, f"📋 Yêu cầu duyệt:\nUID: `{device_uid}`\nUser: {uid}", parse_mode="Markdown")
                            except:
                                pass
                    return
                db["approved"][device_uid] = {
                    "approved_by": "auto",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "telegram_uid": uid
                }
                log(f"AUTO APPROVE: {device_uid}")
                save_db()
                bot.reply_to(msg, f"✅ Đã duyệt UID: `{device_uid}`", parse_mode="Markdown")
                return
        
        # Key activation
        if '-' in text and len(text) > 10:
            if text in db.get("kicked", {}):
                bot.reply_to(msg, "❌ Key đã bị thu hồi.")
                return
            
            if text not in db["keys"]:
                bot.reply_to(msg, "❌ Key không hợp lệ hoặc không tồn tại.")
                return
            
            key = db["keys"][text]
            
            if key["used"]:
                if key["udid"] and key["udid"] != uid:
                    bot.reply_to(msg, "❌ Key đã được kích hoạt trên thiết bị khác.")
                    return
                bot.reply_to(msg, "ℹ️ Key đã kích hoạt trước đó.")
                return
            
            if key["activations"] >= key["max_activations"]:
                bot.reply_to(msg, "❌ Key đã đạt giới hạn thiết bị.")
                return
            
            try:
                exp = datetime.strptime(key["expires"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp:
                    bot.reply_to(msg, "❌ Key đã hết hạn.")
                    return
            except:
                pass
            
            key["used"] = True
            key["udid"] = uid
            key["device"] = "Telegram"
            key["ip"] = msg.from_user.username or "unknown"
            key["activations"] += 1
            key["activated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            db["approved"][uid] = {
                "approved_by": "auto",
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "key": text
            }
            db["stats"]["total_approved"] += 1
            log(f"KEY ACTIVE: {text} by {uid}")
            save_db()
            
            bot.reply_to(
                msg,
                f"✅ Key kích hoạt thành công!\n"
                f"📅 Hết hạn: `{key['expires']}`\n"
                f"🔢 Lượt kích hoạt: {key['activations']}/{key['max_activations']}",
                parse_mode="Markdown"
            )
            return
        
        # Unknown message
        bot.reply_to(msg, "❓ Không hiểu lệnh. Dùng /help để xem hướng dẫn.")
    
    except Exception as e:
        logger.error(f"Handle error: {e}")
        bot.reply_to(msg, "⚠️ Đã xảy ra lỗi. Vui lòng thử lại.")

# ========== ADMIN COMMANDS ==========

@bot.message_handler(commands=['id'])
def cmd_id(msg):
    bot.reply_to(
        msg,
        f"👤 User ID: `{msg.from_user.id}`\n💬 Chat ID: `{msg.chat.id}`",
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['genkey'])
def cmd_genkey(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        bot.reply_to(msg, "📌 Cú pháp: /genkey <số> <loại> [prefix] [ngày]")
        return
    try:
        num = int(parts[1])
        ktype = parts[2]
        prefix = parts[3] if len(parts) > 3 else "hake"
        days = int(parts[4]) if len(parts) > 4 else config["key_expiry_days"]
        keys = [gen_key(prefix, ktype, days) for _ in range(num)]
        log(f"ADMIN {msg.from_user.id} GEN {num} KEY")
        bot.reply_to(msg, "\n".join([f"`{k}`" for k in keys]), parse_mode="Markdown")
    except Exception as e:
        bot.reply_to(msg, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['genkeybulk'])
def cmd_genkeybulk(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 4:
        bot.reply_to(msg, "📌 Cú pháp: /genkeybulk <số> <loại> <prefix> [ngày] [file]")
        return
    try:
        num = int(parts[1])
        ktype = parts[2]
        prefix = parts[3]
        days = int(parts[4]) if len(parts) > 4 else 30
        filename = parts[5] if len(parts) > 5 else f"keys_{int(time.time())}.txt"
        keys = [gen_key(prefix, ktype, days) for _ in range(num)]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(keys))
        log(f"ADMIN BULK GEN {num} KEY -> {filename}")
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f, caption=f"📁 {num} keys")
        os.remove(filename)
    except Exception as e:
        bot.reply_to(msg, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['approve'])
def cmd_approve(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /approve <UID> [ghi chú]")
        return
    note = " ".join(parts[2:]) if len(parts) > 2 else ""
    db["approved"][parts[1]] = {
        "approved_by": str(msg.from_user.id),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": note
    }
    log(f"ADMIN APPROVE: {parts[1]}")
    save_db()
    bot.reply_to(msg, f"✅ Đã duyệt: `{parts[1]}`", parse_mode="Markdown")

@bot.message_handler(commands=['unapprove'])
def cmd_unapprove(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /unapprove <UID>")
        return
    db["approved"].pop(parts[1], None)
    log(f"ADMIN UNAPPROVE: {parts[1]}")
    save_db()
    bot.reply_to(msg, f"🚫 Đã hủy duyệt: `{parts[1]}`", parse_mode="Markdown")

@bot.message_handler(commands=['kick'])
def cmd_kick(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /kick <UID> [lý do]")
        return
    reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
    db["kicked"][parts[1]] = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "by": str(msg.from_user.id),
        "reason": reason
    }
    db["approved"].pop(parts[1], None)
    db["stats"]["total_kicked"] += 1
    log(f"ADMIN KICK: {parts[1]} - {reason}")
    save_db()
    bot.reply_to(msg, f"❌ Đã kick: `{parts[1]}`\n📝 Lý do: {reason}", parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def cmd_ban(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /ban <UID/IP/Device> [lý do]")
        return
    target = parts[1]
    reason = " ".join(parts[2:]) if len(parts) > 2 else "Banned by admin"
    if '.' in target and target.replace('.', '').replace(':', '').isdigit():
        bans["banned_ips"].append({"ip": target, "reason": reason, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    else:
        bans["banned_uids"].append({"uid": target, "reason": reason, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    save_bans()
    log(f"ADMIN BAN: {target}")
    bot.reply_to(msg, f"🔨 Đã ban: `{target}`", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def cmd_unban(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /unban <UID/IP>")
        return
    target = parts[1]
    bans["banned_uids"] = [x for x in bans["banned_uids"] if (x.get("uid") if isinstance(x, dict) else x) != target]
    bans["banned_ips"] = [x for x in bans["banned_ips"] if (x.get("ip") if isinstance(x, dict) else x) != target]
    save_bans()
    log(f"ADMIN UNBAN: {target}")
    bot.reply_to(msg, f"🔓 Đã gỡ ban: `{target}`", parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def cmd_list(msg):
    approved = list(db["approved"].keys())[-20:]
    keys = list(db["keys"].keys())[-20:]
    kicked = list(db["kicked"].keys())[-10:]
    resp = f"📊 Stats: {db['stats']['total_keys']} keys | {db['stats']['total_approved']} approved | {db['stats']['total_kicked']} kicked\n\n"
    resp += "✅ Approved:\n" + ("\n".join([f"- `{u}`" for u in approved]) or "None")
    resp += "\n\n🔑 Keys (gần đây):\n" + ("\n".join([f"- `{k[:40]}...`" for k in keys]) or "None")
    resp += "\n\n❌ Kicked:\n" + ("\n".join([f"- `{u}`" for u in kicked]) or "None")
    bot.reply_to(msg, resp, parse_mode="Markdown")

@bot.message_handler(commands=['listall'])
def cmd_listall(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    keys = "\n".join([f"{k}: used={v['used']}, exp={v.get('expires','N/A')}" for k, v in db["keys"].items()])
    filename = f"all_keys_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(keys)
    with open(filename, 'rb') as f:
        bot.send_document(msg.chat.id, f)
    os.remove(filename)

@bot.message_handler(commands=['info'])
def cmd_info(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /info <UID/Key>")
        return
    target = parts[1]
    if target in db["approved"]:
        info = db["approved"][target]
        bot.reply_to(
            msg,
            f"👤 UID: `{target}`\n"
            f"⏰ Duyệt: {info.get('time')}\n"
            f"👤 Bởi: {info.get('approved_by')}\n"
            f"📝 Ghi chú: {info.get('note','N/A')}",
            parse_mode="Markdown"
        )
    elif target in db["keys"]:
        k = db["keys"][target]
        bot.reply_to(
            msg,
            f"🔑 Key: `{target[:40]}...`\n"
            f"📌 Loại: {k['type']}\n"
            f"✅ Đã dùng: {k['used']}\n"
            f"📅 Hết hạn: {k.get('expires','N/A')}\n"
            f"🔢 Kích hoạt: {k['activations']}/{k['max_activations']}",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(msg, "❌ Không tìm thấy.")

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    total = len(db["keys"])
    used = sum(1 for v in db["keys"].values() if v["used"])
    active = 0
    expired = 0
    for v in db["keys"].values():
        if v["used"]:
            try:
                exp = datetime.strptime(v["expires"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp:
                    expired += 1
                else:
                    active += 1
            except:
                active += 1
    bot.reply_to(
        msg,
        f"📊 Thống kê:\n"
        f"🔑 Tổng: {total}\n"
        f"✅ Đã dùng: {used}\n"
        f"🟢 Còn hạn: {active}\n"
        f"🔴 Hết hạn: {expired}\n"
        f"👤 Approved: {len(db['approved'])}\n"
        f"❌ Kicked: {len(db['kicked'])}"
    )

@bot.message_handler(commands=['logs'])
def cmd_logs(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    n = int(parts[1]) if len(parts) > 1 else 20
    logs = db["logs"][-n:]
    text = "\n".join(logs) or "No logs"
    if len(text) > 4000:
        filename = f"logs_{int(time.time())}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f)
        os.remove(filename)
    else:
        bot.reply_to(msg, f"📜 Logs ({n}):\n```\n{text}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['clearlogs'])
def cmd_clearlogs(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    db["logs"] = []
    save_db()
    bot.reply_to(msg, "🗑️ Đã xóa logs.")

@bot.message_handler(commands=['config'])
def cmd_config(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        bot.reply_to(
            msg,
            f"⚙️ Config hiện tại:\n```\n{json.dumps(config, indent=2, ensure_ascii=False)}\n```\n"
            f"📌 /config <key> <value>",
            parse_mode="Markdown"
        )
        return
    key, val = parts[1], parts[2]
    if key in ["auto_approve", "notify_admin", "maintenance"]:
        config[key] = val.lower() in ["true", "1", "yes", "on"]
    elif key in ["key_expiry_days", "max_devices_per_key"]:
        config[key] = int(val)
    else:
        config[key] = val
    save_config()
    log(f"CONFIG UPDATE: {key}={val}")
    bot.reply_to(msg, f"✅ Cập nhật: `{key} = {val}`", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    text = msg.text[len("/broadcast "):]
    if not text:
        bot.reply_to(msg, "📌 Cú pháp: /broadcast <nội dung>")
        return
    count = 0
    for uid in set(list(db["approved"].keys()) + [str(x) for x in ADMIN_IDS]):
        try:
            bot.send_message(int(uid), f"📢 Thông báo:\n{text}")
            count += 1
        except:
            pass
    bot.reply_to(msg, f"✅ Đã gửi tới {count} người.")

@bot.message_handler(commands=['backup'])
def cmd_backup(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    ts = int(time.time())
    for f in [DB_FILE, BAN_FILE, CONFIG_FILE]:
        if os.path.exists(f):
            os.system(f"cp {f} {f}.{ts}.bak")
    bot.reply_to(msg, f"💾 Backup hoàn tất: `*.{ts}.bak`", parse_mode="Markdown")

@bot.message_handler(commands=['restore'])
def cmd_restore(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /restore <timestamp>")
        return
    ts = parts[1]
    for f in [DB_FILE, BAN_FILE, CONFIG_FILE]:
        bak = f"{f}.{ts}.bak"
        if os.path.exists(bak):
            os.system(f"cp {bak} {f}")
    global db, bans, config
    db = load_json(DB_FILE, db)
    bans = load_json(BAN_FILE, bans)
    config = load_json(CONFIG_FILE, config)
    bot.reply_to(msg, "🔄 Restore hoàn tất.")

@bot.message_handler(commands=['maintenance'])
def cmd_maintenance(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    config["maintenance"] = not config["maintenance"]
    save_config()
    status = "BẬT" if config["maintenance"] else "TẮT"
    log(f"MAINTENANCE {status}")
    bot.reply_to(msg, f"🔧 Maintenance: {status}")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    is_adm = is_admin(msg.from_user.id)
    user_cmds = "👤 Lệnh User:\n/start - Khởi động\n/id - Xem ID\n/help - Trợ giúp"
    admin_cmds = (
        "\n\n🔧 Admin:\n"
        "/genkey <số> <loại> [prefix] [ngày] - Tạo key\n"
        "/genkeybulk <số> <loại> <prefix> [ngày] [file] - Tạo hàng loạt\n"
        "/approve <UID> [ghi chú] - Duyệt UID\n"
        "/unapprove <UID> - Hủy duyệt\n"
        "/kick <UID> [lý do] - Kick\n"
        "/ban <UID/IP> [lý do] - Ban\n"
        "/unban <UID/IP> - Gỡ ban\n"
        "/list - DS gần đây\n"
        "/listall - Xuất file tất cả\n"
        "/info <UID/Key> - Chi tiết\n"
        "/stats - Thống kê\n"
        "/logs [số] - Xem logs\n"
        "/clearlogs - Xóa logs\n"
        "/config <key> <value> - Cấu hình\n"
        "/broadcast <nội dung> - Gửi mass\n"
        "/backup - Backup DB\n"
        "/restore <timestamp> - Restore DB\n"
        "/maintenance - Bật/tắt bảo trì"
    )
    bot.reply_to(msg, user_cmds + (admin_cmds if is_adm else ""), parse_mode="Markdown")

if __name__ == "__main__":
    print("🤖 Bot UnbndSDK Online - Admin: 5736655322")
    log("BOT ONLINE")
    while True:
        try:
            bot.infinity_polling(timeout=60, long_polling_timeout=30)
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)
