# File: keep_alive.py (KHÔNG dùng tên keepalive.py)
from flask import Flask
from threading import Thread
import time
import requests

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot Check Account - Online"

@app.route('/health')
def health():
    return {"status": "ok", "bot": "running"}

def keep_alive():
    while True:
        time.sleep(300)
        try:
            requests.get("http://localhost:8080/health", timeout=10)
        except:
            pass

def run_flask():
    app.run(host='0.0.0.0', port=8080)

def start_keepalive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()
    
    keep = Thread(target=keep_alive)
    keep.daemon = True
    keep.start()
