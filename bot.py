#!/usr/bin/env python3
# =====================================================================
# bot.py - RENDER READY - ĐÃ CẤU HÌNH BOT TOKEN & ADMIN
# =====================================================================
import os, sqlite3, json, base64, datetime, hashlib, secrets, logging
import threading, time, uuid, string, random
from functools import wraps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

# ==================== CẤU HÌNH ====================
BOT_TOKEN = "8515267798:AAEUWB-9qZFcW2ZcDwbaLg8Vi0CtrrUO4gE"
ADMIN_IDS = [5736655322, 8782842024]
API_PORT  = int(os.environ.get("PORT", 10000))
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")

if RENDER_EXTERNAL_URL:
    SERVER_URL = RENDER_EXTERNAL_URL
else:
    import socket, urllib.request
    try:
        ip = urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
        SERVER_URL = f"http://{ip}:{API_PORT}"
    except:
        SERVER_URL = f"http://localhost:{API_PORT}"

DB_PATH   = "/opt/render/project/data/license.db" if os.path.exists("/opt/render/project") else "license.db"
PRIV_PATH = "private_key.pem"
PUB_PATH  = "public_key.pem"
FER_PATH  = "fernet.key"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("RENDER")

# ==================== DATABASE ====================
def db(): conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row; return conn
def init_db():
    c = db()
    c.executescript('''
        CREATE TABLE IF NOT EXISTS keys(id INTEGER PRIMARY KEY AUTOINCREMENT, key_full TEXT, key_short TEXT, product TEXT, type TEXT, expiry TEXT, quantity INTEGER, features TEXT, created_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS activated(id INTEGER PRIMARY KEY AUTOINCREMENT, key_hash TEXT UNIQUE, key_short TEXT, user_id INTEGER, username TEXT, udid TEXT, product TEXT, expiry TEXT, features TEXT, source TEXT, ip TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS revoked(id INTEGER PRIMARY KEY AUTOINCREMENT, key_short TEXT UNIQUE, key_hash TEXT, revoked_by INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS tokens(id INTEGER PRIMARY KEY AUTOINCREMENT, token TEXT UNIQUE, token_hash TEXT UNIQUE, user_id INTEGER, username TEXT, is_active INTEGER DEFAULT 1, device_limit INTEGER DEFAULT 5, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS devices(id INTEGER PRIMARY KEY AUTOINCREMENT, token_id INTEGER, udid TEXT UNIQUE, name TEXT, model TEXT, ios TEXT, app TEXT, key_short TEXT, is_active INTEGER DEFAULT 1, last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    ''')
    c.commit(); c.close()

# ==================== RSA + FERNET ====================
def load_keys():
    if not os.path.exists(PRIV_PATH):
        priv = rsa.generate_private_key(65537, 2048, default_backend())
        pub  = priv.public_key()
        with open(PRIV_PATH, "wb") as f: f.write(priv.private_bytes(encoding=serialization.Encoding.PEM, format=serialization.PrivateFormat.PKCS8, encryption_algorithm=serialization.NoEncryption()))
        with open(PUB_PATH, "wb") as f: f.write(pub.public_bytes(encoding=serialization.Encoding.PEM, format=serialization.PublicFormat.SubjectPublicKeyInfo))
    with open(PRIV_PATH, "rb") as f: priv = serialization.load_pem_private_key(f.read(), password=None, backend=default_backend())
    with open(PUB_PATH, "rb") as f: pub = serialization.load_pem_public_key(f.read(), backend=default_backend())
    return priv, pub
PRIV, PUB = load_keys()

def load_fernet():
    if not os.path.exists(FER_PATH):
        with open(FER_PATH, "wb") as f: f.write(Fernet.generate_key())
    with open(FER_PATH, "rb") as f: return Fernet(f.read())
FER = load_fernet()

def random_prefix():
    der = PUB.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    fp = hashlib.sha256(der).hexdigest()
    chars = string.ascii_uppercase + string.digits
    random.seed(int(fp[:8], 16))
    return ''.join(random.choice(chars) for _ in range(6))
PREFIX = random_prefix()

# ==================== KEYGEN ====================
def gen_license(product, days, features, quantity=0):
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    payload = {'product': product, 'expiry': exp, 'duration_days': days, 'features': features,
               'quantity': quantity if quantity > 0 else None, 'prefix': PREFIX,
               'generated_at': datetime.datetime.now().isoformat(), 'key_id': str(uuid.uuid4())[:8]}
    data = json.dumps(payload).encode()
    sig = PRIV.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    packed = len(data).to_bytes(4, 'big') + data + sig
    return base64.urlsafe_b64encode(packed).decode().rstrip('=')

def gen_license_hours(product, hours, features, quantity=0):
    exp = (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime('%Y-%m-%d %H:%M:%S')
    payload = {'product': product, 'expiry': exp, 'duration_hours': hours, 'features': features,
               'quantity': quantity if quantity > 0 else None, 'prefix': PREFIX,
               'generated_at': datetime.datetime.now().isoformat(), 'key_id': str(uuid.uuid4())[:8]}
    data = json.dumps(payload).encode()
    sig = PRIV.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    packed = len(data).to_bytes(4, 'big') + data + sig
    return base64.urlsafe_b64encode(packed).decode().rstrip('=')

def verify_license(key, user_id=None, udid=None):
    try:
        key += '=' * (4 - len(key) % 4) if len(key) % 4 else ''
        decoded = base64.urlsafe_b64decode(key)
        plen = int.from_bytes(decoded[:4], 'big')
        pdata, sig = decoded[4:4+plen], decoded[4+plen:]
        PUB.verify(sig, pdata, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
        payload = json.loads(pdata)
        try: exp_dt = datetime.datetime.strptime(payload['expiry'], '%Y-%m-%d %H:%M:%S')
        except:
            exp_dt = datetime.datetime.strptime(payload['expiry'], '%Y-%m-%d')
            exp_dt = datetime.datetime.combine(exp_dt, datetime.time.max)
        if datetime.datetime.now() > exp_dt: return False, "⏰ KEY HẾT HẠN", None, None
        khash = hashlib.sha256(key.encode()).hexdigest(); kshort = key[:30]
        c = db()
        if c.execute("SELECT 1 FROM activated WHERE key_hash=?", (khash,)).fetchone(): c.close(); return False, "⚠️ KEY ĐÃ KÍCH HOẠT", None, None
        qty = payload.get('quantity')
        if qty:
            cnt = c.execute("SELECT COUNT(*) FROM activated WHERE key_hash=?", (khash,)).fetchone()[0]
            if cnt >= qty: c.close(); return False, f"📱 ĐÃ ĐỦ {qty} THIẾT BỊ", None, None
        if c.execute("SELECT 1 FROM revoked WHERE key_short=?", (kshort,)).fetchone(): c.close(); return False, "🚫 KEY ĐÃ BỊ THU HỒI", None, None
        c.close()
        return True, f"✅ HỢP LỆ: {payload['product']}", payload, payload.get('key_id')
    except Exception as e: return False, f"❌ LỖI: {str(e)[:60]}", None, None

# ==================== FLASK ====================
app = Flask(__name__)

@app.route('/')
def root():
    return jsonify({'status':'running','server':SERVER_URL,'prefix':PREFIX,'endpoints':['/api/activate','/api/verify','/api/heartbeat','/api/ios/config','/api/health','/api/status']})

@app.route('/api/health')
def health(): return jsonify({'status':'ok','server':SERVER_URL,'prefix':PREFIX})

@app.route('/api/status')
def status():
    c = db()
    ak = c.execute("SELECT COUNT(*) FROM activated").fetchone()[0]
    gk = c.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
    dev = c.execute("SELECT COUNT(*) FROM devices WHERE is_active=1").fetchone()[0]
    c.close()
    return jsonify({'status':'running','server':SERVER_URL,'prefix':PREFIX,'generated':gk,'activated':ak,'devices':dev})

@app.route('/api/activate', methods=['POST'])
def activate():
    token = request.headers.get('X-API-Token','')
    if not token: return jsonify({'status':'error','message':'Thiếu token'}), 401
    c = db()
    row = c.execute("SELECT * FROM tokens WHERE token_hash=? AND is_active=1", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row: c.close(); return jsonify({'status':'error','message':'Token sai'}), 401
    data = request.get_json(silent=True) or {}
    key, udid = data.get('license_key',''), data.get('udid','')
    if not key or not udid: c.close(); return jsonify({'status':'error','message':'Thiếu key/udid'}), 400
    if c.execute("SELECT COUNT(*) FROM devices WHERE token_id=? AND is_active=1 AND udid!=?", (row['id'], udid)).fetchone()[0] >= row['device_limit']:
        c.close(); return jsonify({'status':'error','message':f'Giới hạn {row["device_limit"]} máy'}), 403
    ok, msg, payload, kid = verify_license(key, row['user_id'], udid)
    if ok and payload:
        khash, kshort = hashlib.sha256(key.encode()).hexdigest(), key[:30]
        c.execute("INSERT OR IGNORE INTO activated(key_hash,key_short,user_id,username,udid,product,expiry,features,source,ip) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (khash,kshort,row['user_id'],row['username'],udid,payload['product'],payload['expiry'],json.dumps(payload.get('features',[])),'ios',request.remote_addr))
        c.execute("INSERT OR REPLACE INTO devices(token_id,udid,name,model,ios,app,key_short,last_seen) VALUES (?,?,?,?,?,?,?,CURRENT_TIMESTAMP)",
            (row['id'],udid,data.get('device_name',''),data.get('device_model',''),data.get('ios_version',''),data.get('app_version','1.0'),kshort))
        c.commit(); c.close()
        return jsonify({'status':'success','message':msg,'data':{'product':payload['product'],'expiry':payload['expiry'],'features':payload.get('features',[]),'key_id':kid,'server':SERVER_URL}})
    c.close(); return jsonify({'status':'error','message':msg}), 403

@app.route('/api/verify', methods=['POST'])
def verify():
    token = request.headers.get('X-API-Token','')
    if not token: return jsonify({'status':'error'}), 401
    c = db()
    if not c.execute("SELECT 1 FROM tokens WHERE token_hash=? AND is_active=1", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone(): c.close(); return jsonify({'status':'error'}), 401
    c.close()
    data = request.get_json(silent=True) or {}
    ok, msg, payload, kid = verify_license(data.get('license_key',''))
    r = {'status':'valid' if ok else 'invalid','message':msg,'server':SERVER_URL}
    if payload: r['data'] = {'product':payload['product'],'expiry':payload['expiry'],'features':payload.get('features',[]),'key_id':kid}
    return jsonify(r)

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    token = request.headers.get('X-API-Token','')
    if not token: return jsonify({'status':'error'}), 401
    c = db()
    row = c.execute("SELECT id FROM tokens WHERE token_hash=? AND is_active=1", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row: c.close(); return jsonify({'status':'error'}), 401
    data = request.get_json(silent=True) or {}
    if data.get('udid'): c.execute("UPDATE devices SET last_seen=CURRENT_TIMESTAMP WHERE udid=? AND token_id=?", (data['udid'], row[0])); c.commit()
    c.close()
    return jsonify({'status':'ok','server':SERVER_URL})

@app.route('/api/ios/config')
def ios_config():
    token = request.headers.get('X-API-Token','')
    if not token: return jsonify({'status':'error'}), 401
    c = db()
    row = c.execute("SELECT * FROM tokens WHERE token_hash=? AND is_active=1", (hashlib.sha256(token.encode()).hexdigest(),)).fetchone()
    if not row: c.close(); return jsonify({'status':'error'}), 401
    c.close()
    cfg = {'server_url':SERVER_URL,'prefix':PREFIX,'endpoints':{'activate':f"{SERVER_URL}/api/activate",'verify':f"{SERVER_URL}/api/verify",'heartbeat':f"{SERVER_URL}/api/heartbeat"}}
    return jsonify({'encrypted_config': base64.b64encode(FER.encrypt(json.dumps(cfg).encode())).decode()})

# ==================== TELEGRAM BOT ====================
def admin_only(f):
    @wraps(f)
    async def w(update, context, *a, **kw):
        if update.effective_user.id not in ADMIN_IDS: await update.message.reply_text("⛔ Admin only"); return
        return await f(update, context, *a, **kw)
    return w

async def start(update, context):
    await update.message.reply_text(f"🔐 LICENSE BOT\n🌐 {SERVER_URL}\n🏷 Prefix: `{PREFIX}`\n\n/key <tên> <ngày>\n/keyd <tên> <ngày> <sl>\n/keyh <tên> <giờ>\n/keyvip <tên> <ngày> <sl> <feat>\n/token <uid> [limit]\n/activate <key>\n/mykeys\n/status", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_key(update, context):
    a = update.message.text.split()
    if len(a) < 3: await update.message.reply_text("⚠️ `/key <tên> <ngày>`", parse_mode=ParseMode.MARKDOWN); return
    prod, days = a[1], int(a[2])
    key = gen_license(prod, days, ['basic'], 0)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'days', exp, 0, '["basic"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(f"✅ KEY\n📦 `{prod}`\n⏰ `{exp}` ({days}d)\n📱 Ko giới hạn\n\n🔑 `{key}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyd(update, context):
    a = update.message.text.split()
    if len(a) < 4: await update.message.reply_text("⚠️ `/keyd <tên> <ngày> <sl>`", parse_mode=ParseMode.MARKDOWN); return
    prod, days, qty = a[1], int(a[2]), int(a[3])
    key = gen_license(prod, days, ['basic'], qty)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'days_qty', exp, qty, '["basic"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(f"✅ KEY\n📦 `{prod}`\n⏰ `{exp}` ({days}d)\n📱 `{qty}` máy\n\n🔑 `{key}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyh(update, context):
    a = update.message.text.split()
    if len(a) < 3: await update.message.reply_text("⚠️ `/keyh <tên> <giờ>`", parse_mode=ParseMode.MARKDOWN); return
    prod, hours = a[1], int(a[2])
    key = gen_license_hours(prod, hours, ['trial'], 1)
    exp = (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime('%d/%m/%Y %H:%M')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'hours', exp, 1, '["trial"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(f"✅ KEY GIỜ\n📦 `{prod}`\n⏰ `{exp}` ({hours}h)\n📱 1 máy\n\n🔑 `{key}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyvip(update, context):
    a = update.message.text.split(maxsplit=4)
    if len(a) < 5: await update.message.reply_text("⚠️ `/keyvip <tên> <ngày> <sl> <feat>`", parse_mode=ParseMode.MARKDOWN); return
    prod, days, qty = a[1], int(a[2]), int(a[3])
    feats = [x.strip() for x in a[4].split(',')]
    key = gen_license(prod, days, feats, qty)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'vip', exp, qty, json.dumps(feats), update.effective_user.id)).connection.commit()
    await update.message.reply_text(f"💎 VIP KEY\n📦 `{prod}`\n⏰ `{exp}` ({days}d)\n📱 `{qty}` máy\n🛠 `{', '.join(feats)}`\n\n🔑 `{key}`", parse_mode=ParseMode.MARKDOWN)

async def cmd_activate(update, context):
    u = update.effective_user; t = update.message.text.strip()
    if t.startswith('/activate'):
        p = t.split(maxsplit=1)
        if len(p) < 2: await update.message.reply_text("⚠️ `/activate <key>`", parse_mode=ParseMode.MARKDOWN); return
        key = p[1].strip()
    else:
        if len(t) < 50: return
        key = t
    m = await update.message.reply_text("⏳ Đang kiểm tra...")
    ok, msg, payload, kid = verify_license(key, u.id)
    if ok and payload:
        kh = hashlib.sha256(key.encode()).hexdigest()
        c = db()
        c.execute("INSERT OR IGNORE INTO activated(key_hash,key_short,user_id,username,product,expiry,features,source) VALUES (?,?,?,?,?,?,?,?)",
            (kh, key[:30], u.id, u.username or u.full_name, payload['product'], payload['expiry'], json.dumps(payload.get('features',[])), 'telegram'))
        c.commit(); c.close()
    await m.edit_text(f"{'✅' if ok else '❌'} {msg}")

async def cmd_mykeys(update, context):
    rows = db().execute("SELECT product,expiry,features,created_at FROM activated WHERE user_id=? ORDER BY created_at DESC", (update.effective_user.id,)).fetchall()
    if not rows: await update.message.reply_text("📭 Chưa có key"); return
    t = "🔑 KEY CỦA BẠN:\n\n"
    for r in rows:
        f = json.loads(r['features']) if r['features'] else []
        t += f"📦 `{r['product']}` ⏰ `{r['expiry']}` 🛠 {', '.join(f)}\n"
    await update.message.reply_text(t, parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_token(update, context):
    a = update.message.text.split()
    if len(a) < 2: await update.message.reply_text("⚠️ `/token <user_id> [limit]`", parse_mode=ParseMode.MARKDOWN); return
    uid, lim = int(a[1]), int(a[2]) if len(a) > 2 else 5
    try: ch = await context.bot.get_chat(uid); un = ch.username or ch.full_name
    except: un = f"user_{uid}"
    tok = secrets.token_hex(32); th = hashlib.sha256(tok.encode()).hexdigest()
    db().execute("INSERT INTO tokens(token,token_hash,user_id,username,device_limit) VALUES (?,?,?,?,?)", (tok, th, uid, un, lim)).connection.commit()
    await update.message.reply_text(f"✅ Token\n👤 {un}\n📱 {lim} máy\n🌐 {SERVER_URL}\n\n🔑 `{tok}`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_status(update, context):
    c = db()
    ak = c.execute("SELECT COUNT(*) FROM activated").fetchone()[0]
    gk = c.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
    dev = c.execute("SELECT COUNT(*) FROM devices WHERE is_active=1").fetchone()[0]
    c.close()
    await update.message.reply_text(f"📊 {SERVER_URL}\n🏷 `{PREFIX}`\n🔑 Gen:{gk} | ✅ Act:{ak} | 📱 Dev:{dev}", parse_mode=ParseMode.MARKDOWN)

async def handle_msg(update, context):
    t = update.message.text.strip()
    if len(t) > 50 and not t.startswith('/'): await cmd_activate(update, context)

# ==================== MAIN ====================
def run_bot():
    bot = Application.builder().token(BOT_TOKEN).build()
    for cmd, fn in [
        ("start", start), ("activate", cmd_activate), ("mykeys", cmd_mykeys),
        ("key", cmd_key), ("keyd", cmd_keyd), ("keyh", cmd_keyh), ("keyvip", cmd_keyvip),
        ("token", cmd_token), ("status", cmd_status)
    ]: bot.add_handler(CommandHandler(cmd, fn))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    log.info(f"🤖 Bot polling... Server: {SERVER_URL}")
    bot.run_polling(all_updates=True)

if __name__ == "__main__":
    init_db()
    threading.Thread(target=run_bot, daemon=True).start()
    log.info(f"🌐 API: {SERVER_URL} | 🏷 Prefix: {PREFIX}")
    app.run(host="0.0.0.0", port=API_PORT, debug=False)
