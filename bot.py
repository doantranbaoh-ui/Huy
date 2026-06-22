cd ~/baohuy && cat > bot.py << 'EOF'
#!/usr/bin/env python3
"""UnbndSDK Bot - Render Ready"""
import json, os, time, uuid, threading
from flask import Flask, request, jsonify
import telebot

BOT_TOKEN = "6320148381:AAHKLMaGycWIv8sxdBU6sAmgOPn2XlqTIx0"
CHAT_ID = "-1003925717296"
ADMIN_IDS = [5736655322]
DB_FILE = "keys.json"
PORT = int(os.environ.get("PORT", 8080))

# Flask app
app = Flask(__name__)

# Database
if os.path.exists(DB_FILE):
    with open(DB_FILE, 'r') as f: db = json.load(f)
else:
    db = {"keys": {}, "approved": {}, "kicked": {}, "logs": []}

def save():
    with open(DB_FILE, 'w') as f: json.dump(db, f, indent=2)

def log(msg):
    db["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")
    db["logs"] = db["logs"][-100:]
    save()

def is_admin(uid): return uid in ADMIN_IDS

# Telegram Bot
bot = telebot.TeleBot(BOT_TOKEN, threaded=False)

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    text = msg.text.strip()
    uid = str(msg.from_user.id)
    
    if "#KichHoat" in text or "#Start" in text or "#YeuCau" in text:
        device_uid = None
        for part in text.split():
            if part.startswith("UID:") or part.startswith("UDID:"):
                device_uid = part.split(":",1)[1]
        if device_uid:
            db["approved"][device_uid] = {"approved_by": str(uid), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            log(f"AUTO APPROVE: {device_uid}")
            save()
            bot.reply_to(msg, f"✅ Da duyet UID: {device_uid}")
            return
    
    if '-' in text and len(text) > 10 and not text.startswith('/'):
        if text not in db["keys"]:
            db["keys"][text] = {"type": text.split("-")[1] if len(text.split("-"))>1 else "unknown", "prefix": text.split("-")[0], "created": time.strftime("%Y-%m-%d %H:%M:%S"), "used": True, "udid": uid, "device": "Telegram"}
            db["approved"][uid] = {"approved_by": "auto", "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            log(f"KEY ACTIVE: {text}")
            save()
            bot.reply_to(msg, f"✅ Key da kich hoat: {text}")
            return

@bot.message_handler(commands=['id'])
def cmd_id(msg): bot.reply_to(msg, f"Chat ID: {msg.from_user.id}\nGroup: {msg.chat.id}")

@bot.message_handler(commands=['genkey'])
def cmd_genkey(msg):
    if not is_admin(msg.from_user.id): bot.reply_to(msg, "❌ Khong phai admin!"); return
    parts = msg.text.split()
    if len(parts) < 3: bot.reply_to(msg, "/genkey <so> <loai> <prefix>"); return
    num, ktype, prefix = int(parts[1]), parts[2], parts[3] if len(parts)>3 else "hake"
    keys = []
    for _ in range(num):
        code = str(uuid.uuid4()).replace('-', '')[:20]
        k = f"{prefix}-{ktype}-{code}"
        db["keys"][k] = {"type": ktype, "prefix": prefix, "created": time.strftime("%Y-%m-%d %H:%M:%S"), "used": False, "udid": None, "device": None}
        keys.append(k)
    save()
    bot.reply_to(msg, "\n".join([f"`{k}`" for k in keys]), parse_mode="Markdown")

@bot.message_handler(commands=['approve'])
def cmd_approve(msg):
    if not is_admin(msg.from_user.id): bot.reply_to(msg, "❌ Khong phai admin!"); return
    parts = msg.text.split()
    if len(parts) < 2: bot.reply_to(msg, "/approve <UID>"); return
    db["approved"][parts[1]] = {"approved_by": str(msg.from_user.id), "time": time.strftime("%Y-%m-%d %H:%M:%S")}
    save()
    bot.reply_to(msg, f"✅ {parts[1]}")

@bot.message_handler(commands=['kick'])
def cmd_kick(msg):
    if not is_admin(msg.from_user.id): bot.reply_to(msg, "❌ Khong phai admin!"); return
    parts = msg.text.split()
    if len(parts) < 2: bot.reply_to(msg, "/kick <UID>"); return
    db["kicked"][parts[1]] = time.strftime("%Y-%m-%d %H:%M:%S")
    db["approved"].pop(parts[1], None)
    save()
    bot.reply_to(msg, f"❌ {parts[1]}")

@bot.message_handler(commands=['list'])
def cmd_list(msg):
    resp = "✅ Approved:\n" + "\n".join([f"- {u}" for u in list(db["approved"].keys())[-10:]]) or "None"
    resp += "\n🔑 Keys:\n" + "\n".join([f"- {k[:30]}" for k in list(db["keys"].keys())[-10:]]) or "None"
    bot.reply_to(msg, resp)

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    bot.reply_to(msg, "/id /genkey /approve /kick /list /help\nWeb: /api/check?key=xxx&uid=xxx")

# ===== FLASK API =====
@app.route('/')
def home():
    active = sum(1 for v in db["keys"].values() if v["used"])
    return f"""<!DOCTYPE html>
<html><head><title>UnbndSDK</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>body{{font-family:Arial;background:#0d1117;color:#c9d1d9;padding:20px}} .card{{background:#161b22;border-radius:8px;padding:20px;margin:10px 0}} h1{{color:#58a6ff}} .g{{color:#3fb950}} .r{{color:#f85149}}</style></head><body>
<h1>🤖 UnbndSDK Server</h1>
<div class="card"><h2>Stats</h2><p>Keys: {len(db['keys'])} | <span class="g">Active: {active}</span> | Approved: {len(db['approved'])} | <span class="r">Kicked: {len(db['kicked'])}</span></p></div>
<div class="card"><h2>API</h2><p>Check: <code>/api/check?key=xxx&uid=xxx</code></p></div>
<div class="card"><h2>Logs</h2><pre>{''.join(db['logs'][-20:])}</pre></div>
</body></html>"""

@app.route('/api/check')
def api_check():
    key = request.args.get('key', '')
    uid = request.args.get('uid', '')
    if key in db["keys"]:
        kd = db["keys"][key]
        if kd["used"] and kd["udid"] == uid:
            return jsonify({"code": 200, "message": "Success"})
        elif kd["used"]:
            return jsonify({"code": 400, "message": "UDID mismatch"})
        else:
            kd["used"] = True; kd["udid"] = uid; kd["activated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            db["approved"][uid] = {"approved_by": "api", "time": time.strftime("%Y-%m-%d %H:%M:%S")}
            save()
            return jsonify({"code": 200, "message": "Activated"})
    elif uid in db["approved"]:
        code = str(uuid.uuid4()).replace('-', '')[:20]
        new_key = f"auto-{code}"
        db["keys"][new_key] = {"type": "auto", "prefix": "auto", "created": time.strftime("%Y-%m-%d %H:%M:%S"), "used": True, "udid": uid}
        save()
        return jsonify({"code": 200, "message": "Auto approved", "key": new_key})
    return jsonify({"code": 400, "message": "Not found. Yeu cau admin duyet UID: " + uid})

# ===== START =====
def run_bot():
    bot.infinity_polling()

threading.Thread(target=run_bot, daemon=True).start()
print(f"Server: http://0.0.0.0:{PORT}")
app.run(host="0.0.0.0", port=PORT, debug=False)
EOF

echo "pip install flask pyTelegramBotAPI" > requirements.txt
echo "python bot.py" > start.sh
chmod +x start.sh
echo "Ready for Render: bot.py + requirements.txt"
