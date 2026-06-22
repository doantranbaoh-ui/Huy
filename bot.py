#!/usr/bin/env python3
# =====================================================================
# bot.py — LỆNH DỄ TẠO KEY + KEY HIỂN THỊ RANDOM THEO SERVER
# Sửa BOT_TOKEN, ADMIN_IDS → chạy python3 bot.py
# Lệnh: /key, /keyd, /keyh, /keyvip → tạo key nhanh, hiển thị đẹp
# =====================================================================
import os, sqlite3, json, base64, datetime, hashlib, secrets, logging
import threading, time, uuid, socket, urllib.request, random, string
from functools import wraps
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.constants import ParseMode
from flask import Flask, request, jsonify
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet

# ==================== CHỈ SỬA 2 DÒNG ====================
BOT_TOKEN = "8515267798:AAEUWB-9qZFcW2ZcDwbaLg8Vi0CtrrUO4gE"
ADMIN_IDS = [5736655322,8782842024]
API_PORT  = 8443
# =======================================================

def get_ip():
    try: return urllib.request.urlopen("https://api.ipify.org", timeout=5).read().decode().strip()
    except:
        try: return urllib.request.urlopen("https://icanhazip.com", timeout=5).read().decode().strip()
        except: return socket.gethostbyname(socket.gethostname())

SERVER_IP   = get_ip()
SERVER_URL  = f"http://{SERVER_IP}:{API_PORT}"
DB_PATH     = "license.db"
PRIV_PATH   = "private_key.pem"
PUB_PATH    = "public_key.pem"
FER_PATH    = "fernet.key"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
log = logging.getLogger("KEYGEN")

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

# ==================== RANDOM KEY PREFIX (theo server) ====================
def random_prefix():
    """Tạo prefix random 6 ký tự dựa trên public key fingerprint"""
    der = PUB.public_bytes(encoding=serialization.Encoding.DER, format=serialization.PublicFormat.SubjectPublicKeyInfo)
    fp = hashlib.sha256(der).hexdigest()
    chars = string.ascii_uppercase + string.digits
    random.seed(int(fp[:8], 16))
    return ''.join(random.choice(chars) for _ in range(6))

PREFIX = random_prefix()

def format_key_display(key):
    """Hiển thị key dạng đẹp: XXXX-XXXX-XXXX-XXXX"""
    k = key[:32] if len(key) >= 32 else key
    return '-'.join([k[i:i+4] for i in range(0, len(k), 4)])

# ==================== KEYGEN ====================
def gen_license(product, days, features, quantity=0):
    """Tạo key ngày (quantity=0 = không giới hạn)"""
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%Y-%m-%d')
    payload = {'product': product, 'expiry': exp, 'duration_days': days, 'features': features,
               'quantity': quantity if quantity > 0 else None, 'prefix': PREFIX,
               'generated_at': datetime.datetime.now().isoformat(), 'key_id': str(uuid.uuid4())[:8]}
    data = json.dumps(payload).encode()
    sig = PRIV.sign(data, padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH), hashes.SHA256())
    packed = len(data).to_bytes(4, 'big') + data + sig
    return base64.urlsafe_b64encode(packed).decode().rstrip('=')

def gen_license_hours(product, hours, features, quantity=0):
    """Tạo key giờ"""
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

# ==================== FLASK API ====================
app = Flask(__name__)

@app.route('/api/health')
def health(): return jsonify({'status':'ok','server':SERVER_URL,'prefix':PREFIX})

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
    await update.message.reply_text(f"""
╔══════════════════════════════════╗
║   🔐 LICENSE KEY SYSTEM        ║
║   🌐 {SERVER_URL[:30]}... ║
╚══════════════════════════════════╝

👤 {update.effective_user.first_name}

📋 LỆNH USER:
  /activate <key> — Kích hoạt key
  /mykeys — Key của bạn

⚡ LỆNH TẠO KEY NHANH (Admin):
  /key <tên> <ngày> — Key ngày, ko giới hạn
  /keyd <tên> <ngày> <số_lượng> — Key ngày + giới hạn máy
  /keyh <tên> <giờ> — Key giờ
  /keyvip <tên> <ngày> <số_lượng> <tính_năng> — Key VIP

📌 PREFIX KEY: `{PREFIX}-...`
""", parse_mode=ParseMode.MARKDOWN)

# ==================== LỆNH TẠO KEY SIÊU DỄ ====================

@admin_only
async def cmd_key(update, context):
    """/key <tên> <ngày> — Tạo key ngày, không giới hạn thiết bị"""
    a = update.message.text.split()
    if len(a) < 3:
        await update.message.reply_text("⚠️ `/key <tên_sản_phẩm> <số_ngày>`\nVí dụ: `/key ProApp 365`", parse_mode=ParseMode.MARKDOWN)
        return
    prod, days = a[1], int(a[2])
    key = gen_license(prod, days, ['basic'], 0)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'days', exp, 0, '["basic"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(
        f"✅ **KEY ĐÃ TẠO**\n\n"
        f"📦 Sản phẩm: `{prod}`\n"
        f"⏰ Hết hạn: `{exp}` ({days} ngày)\n"
        f"📱 Giới hạn: Không giới hạn\n"
        f"🏷 Prefix: `{PREFIX}`\n\n"
        f"🔑 **KEY:**\n`{key}`\n\n"
        f"📋 Format:\n`{format_key_display(key)}`",
        parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyd(update, context):
    """/keyd <tên> <ngày> <số_lượng> — Key ngày + giới hạn thiết bị"""
    a = update.message.text.split()
    if len(a) < 4:
        await update.message.reply_text("⚠️ `/keyd <tên> <ngày> <số_lượng_máy>`\nVí dụ: `/keyd ProApp 365 5`", parse_mode=ParseMode.MARKDOWN)
        return
    prod, days, qty = a[1], int(a[2]), int(a[3])
    key = gen_license(prod, days, ['basic'], qty)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'days_qty', exp, qty, '["basic"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(
        f"✅ **KEY ĐÃ TẠO**\n\n"
        f"📦 Sản phẩm: `{prod}`\n"
        f"⏰ Hết hạn: `{exp}` ({days} ngày)\n"
        f"📱 Giới hạn: `{qty}` thiết bị\n"
        f"🏷 Prefix: `{PREFIX}`\n\n"
        f"🔑 **KEY:**\n`{key}`",
        parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyh(update, context):
    """/keyh <tên> <giờ> — Key theo giờ"""
    a = update.message.text.split()
    if len(a) < 3:
        await update.message.reply_text("⚠️ `/keyh <tên> <số_giờ>`\nVí dụ: `/keyh Trial 72`", parse_mode=ParseMode.MARKDOWN)
        return
    prod, hours = a[1], int(a[2])
    key = gen_license_hours(prod, hours, ['trial'], 1)
    exp = (datetime.datetime.now() + datetime.timedelta(hours=hours)).strftime('%d/%m/%Y %H:%M')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'hours', exp, 1, '["trial"]', update.effective_user.id)).connection.commit()
    await update.message.reply_text(
        f"✅ **KEY GIỜ ĐÃ TẠO**\n\n"
        f"📦 Sản phẩm: `{prod}`\n"
        f"⏰ Hết hạn: `{exp}` ({hours} giờ)\n"
        f"📱 Giới hạn: 1 máy\n"
        f"🏷 Prefix: `{PREFIX}`\n\n"
        f"🔑 **KEY:**\n`{key}`",
        parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_keyvip(update, context):
    """/keyvip <tên> <ngày> <số_lượng> <tính_năng> — Key VIP đầy đủ"""
    a = update.message.text.split(maxsplit=4)
    if len(a) < 5:
        await update.message.reply_text("⚠️ `/keyvip <tên> <ngày> <số_lượng> <tính_năng>`\nVí dụ: `/keyvip Ultra 365 10 premium,api,cloud`", parse_mode=ParseMode.MARKDOWN)
        return
    prod, days, qty = a[1], int(a[2]), int(a[3])
    feats = [x.strip() for x in a[4].split(',')]
    key = gen_license(prod, days, feats, qty)
    exp = (datetime.date.today() + datetime.timedelta(days=days)).strftime('%d/%m/%Y')
    db().execute("INSERT INTO keys(key_full,key_short,product,type,expiry,quantity,features,created_by) VALUES (?,?,?,?,?,?,?,?)",
        (key, key[:30], prod, 'vip', exp, qty, json.dumps(feats), update.effective_user.id)).connection.commit()
    await update.message.reply_text(
        f"💎 **KEY VIP ĐÃ TẠO**\n\n"
        f"📦 Sản phẩm: `{prod}`\n"
        f"⏰ Hết hạn: `{exp}` ({days} ngày)\n"
        f"📱 Giới hạn: `{qty}` thiết bị\n"
        f"🛠 Tính năng: `{', '.join(feats)}`\n"
        f"🏷 Prefix: `{PREFIX}`\n\n"
        f"🔑 **KEY:**\n`{key}`",
        parse_mode=ParseMode.MARKDOWN)

# ==================== LỆNH USER ====================
async def cmd_activate(update, context):
    u = update.effective_user; t = update.message.text.strip()
    if t.startswith('/activate'):
        p = t.split(maxsplit=1)
        if len(p) < 2: await update.message.reply_text("⚠️ `/activate <key>`", parse_mode=ParseMode.MARKDOWN); return
        key = p[1].strip()
    else:
        if len(t) < 50: return
        key = t
    m = await update.message.reply_text("⏳ Đang kiểm tra key...")
    ok, msg, payload, kid = verify_license(key, u.id)
    if ok and payload:
        kh = hashlib.sha256(key.encode()).hexdigest()
        c = db()
        c.execute("INSERT OR IGNORE INTO activated(key_hash,key_short,user_id,username,product,expiry,features,source) VALUES (?,?,?,?,?,?,?,?)",
            (kh, key[:30], u.id, u.username or u.full_name, payload['product'], payload['expiry'], json.dumps(payload.get('features',[])), 'telegram'))
        c.commit(); c.close()
    icon = "✅" if ok else "❌"
    r = f"{icon} {msg}"
    if payload: r += f"\n📦 {payload['product']}\n⏰ {payload['expiry']}"
    await m.edit_text(r)

async def cmd_mykeys(update, context):
    rows = db().execute("SELECT product,expiry,features,created_at FROM activated WHERE user_id=? ORDER BY created_at DESC", (update.effective_user.id,)).fetchall()
    if not rows: await update.message.reply_text("📭 Bạn chưa có key nào."); return
    t = "🔑 **KEY CỦA BẠN:**\n\n"
    for i, r in enumerate(rows, 1):
        f = json.loads(r['features']) if r['features'] else []
        t += f"{i}. 📦 `{r['product']}`\n   ⏰ `{r['expiry']}`\n   🛠 {', '.join(f)}\n   📅 {r['created_at'][:10]}\n\n"
    await update.message.reply_text(t, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN KHÁC ====================
@admin_only
async def cmd_token(update, context):
    a = update.message.text.split()
    if len(a) < 3: await update.message.reply_text("⚠️ `/token <user_id> [limit]`", parse_mode=ParseMode.MARKDOWN); return
    uid, lim = int(a[1]), int(a[2]) if len(a) > 2 else 5
    try: ch = await context.bot.get_chat(uid); un = ch.username or ch.full_name
    except: un = f"user_{uid}"
    tok = secrets.token_hex(32); th = hashlib.sha256(tok.encode()).hexdigest()
    db().execute("INSERT INTO tokens(token,token_hash,user_id,username,device_limit) VALUES (?,?,?,?,?)", (tok, th, uid, un, lim)).connection.commit()
    await update.message.reply_text(f"✅ Token: `{tok}`\n👤 {un} | 📱 {lim} máy\n🌐 {SERVER_URL}", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_revoke(update, context):
    a = update.message.text.split(maxsplit=1)
    if len(a) < 2: await update.message.reply_text("⚠️ `/revoke <key>`", parse_mode=ParseMode.MARKDOWN); return
    key = a[1].strip(); kh = hashlib.sha256(key.encode()).hexdigest(); ks = key[:30]
    c = db()
    c.execute("INSERT OR IGNORE INTO revoked(key_short,key_hash,revoked_by) VALUES (?,?,?)", (ks, kh, update.effective_user.id))
    c.execute("DELETE FROM activated WHERE key_hash=?", (kh,)); c.commit(); c.close()
    await update.message.reply_text(f"🚫 Đã thu hồi: `{ks}...`", parse_mode=ParseMode.MARKDOWN)

@admin_only
async def cmd_status(update, context):
    c = db()
    ak = c.execute("SELECT COUNT(*) FROM activated").fetchone()[0]
    gk = c.execute("SELECT COUNT(*) FROM keys").fetchone()[0]
    rk = c.execute("SELECT COUNT(*) FROM revoked").fetchone()[0]
    dev = c.execute("SELECT COUNT(*) FROM devices WHERE is_active=1").fetchone()[0]
    tok = c.execute("SELECT COUNT(*) FROM tokens WHERE is_active=1").fetchone()[0]
    c.close()
    await update.message.reply_text(f"📊 **STATUS**\n🌐 {SERVER_URL}\n🏷 Prefix: `{PREFIX}`\n🔑 Generated: {gk}\n✅ Activated: {ak}\n🚫 Revoked: {rk}\n📱 Devices: {dev}\n🔗 Tokens: {tok}")

@admin_only
async def cmd_keys(update, context):
    rows = db().execute("SELECT * FROM keys ORDER BY created_at DESC LIMIT 20").fetchall()
    if not rows: await update.message.reply_text("📭 Chưa có key."); return
    t = "📋 **DANH SÁCH KEY GẦN ĐÂY:**\n\n"
    for r in rows:
        t += f"🆔 `{r['id']}` | 📦 `{r['product']}` | {r['type']}\n   ⏰ `{r['expiry']}` | 📱 Qty: {r['quantity'] or '∞'}\n   🔑 `{r['key_short']}...`\n\n"
    await update.message.reply_text(t, parse_mode=ParseMode.MARKDOWN)

async def handle_msg(update, context):
    t = update.message.text.strip()
    if len(t) > 50 and not t.startswith('/'): await cmd_activate(update, context)

# ==================== MAIN ====================
def run_flask(): app.run(host="0.0.0.0", port=API_PORT, debug=False, use_reloader=False)

def main():
    init_db()
    threading.Thread(target=run_flask, daemon=True).start()
    log.info(f"🌐 SERVER: {SERVER_URL} | 🏷 PREFIX: {PREFIX}")
    bot = Application.builder().token(BOT_TOKEN).build()
    for cmd, fn in [
        ("start", start), ("activate", cmd_activate), ("mykeys", cmd_mykeys),
        ("key", cmd_key), ("keyd", cmd_keyd), ("keyh", cmd_keyh), ("keyvip", cmd_keyvip),
        ("token", cmd_token), ("revoke", cmd_revoke), ("status", cmd_status), ("keys", cmd_keys)
    ]: bot.add_handler(CommandHandler(cmd, fn))
    bot.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    log.info("🤖 Bot started!")
    bot.run_polling(all_updates=True)

if __name__ == "__main__":
    main()
