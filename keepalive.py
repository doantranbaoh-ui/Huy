# keepalive.py - Giữ bot chạy 24/7 trên Render (Web Service)
import os
import sys
import subprocess
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ========== CẤU HÌNH ==========
PORT = int(os.environ.get("PORT", 10000))

# ========== WEB SERVER ==========
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = """<!DOCTYPE html>
<html>
<head>
    <title>Garena Checker Bot 24/7</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            text-align: center;
            padding: 50px;
            background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
            color: #00ff00;
            margin: 0;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            background: rgba(0,0,0,0.8);
            padding: 40px;
            border-radius: 20px;
            border: 2px solid #00ff00;
            box-shadow: 0 0 50px rgba(0,255,0,0.1);
        }
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
            color: #00ff00;
            text-shadow: 0 0 20px rgba(0,255,0,0.3);
        }
        .status {
            font-size: 1.5em;
            padding: 15px;
            margin: 20px 0;
            background: rgba(0,255,0,0.1);
            border-radius: 10px;
            border: 1px solid #00ff00;
        }
        .alive {
            color: #00ff00;
            font-weight: bold;
            animation: blink 1s infinite;
        }
        @keyframes blink {
            0% { opacity: 1; }
            50% { opacity: 0.3; }
            100% { opacity: 1; }
        }
        .info {
            text-align: left;
            padding: 20px;
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
            margin: 20px 0;
        }
        .info-item {
            padding: 8px 0;
            border-bottom: 1px solid rgba(255,255,255,0.1);
        }
        .admin-link {
            color: #00ff00;
            text-decoration: none;
            font-weight: bold;
        }
        .admin-link:hover {
            text-decoration: underline;
        }
        .footer {
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Garena Checker Bot</h1>
        <div class="status">
            Status: <span class="alive">ALIVE</span>
        </div>
        <div class="info">
            <div class="info-item">Time: """ + datetime.now().strftime('%Y-%m-%d %H:%M:%S') + """</div>
            <div class="info-item">Uptime: <span id="uptime">Loading...</span></div>
            <div class="info-item">Admin: <a href="https://t.me/baohuyno1" class="admin-link">@baohuyno1</a></div>
            <div class="info-item">Port: """ + str(PORT) + """</div>
            <div class="info-item">Bot Status: <span id="bot_status">Checking...</span></div>
        </div>
        <div class="footer">
            Powered by ❤️ | Bot 24/7
        </div>
    </div>
    <script>
        let startTime = new Date();
        setInterval(() => {
            let now = new Date();
            let diff = Math.floor((now - startTime) / 1000);
            let days = Math.floor(diff / 86400);
            let hours = Math.floor((diff % 86400) / 3600);
            let minutes = Math.floor((diff % 3600) / 60);
            let seconds = diff % 60;
            let uptimeStr = '';
            if (days > 0) uptimeStr += days + 'd ';
            uptimeStr += hours + 'h ' + minutes + 'm ' + seconds + 's';
            document.getElementById('uptime').textContent = uptimeStr;
        }, 1000);
        
        setInterval(() => {
            fetch('/ping')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('bot_status').textContent = 'Online';
                    document.getElementById('bot_status').style.color = '#00ff00';
                })
                .catch(() => {
                    document.getElementById('bot_status').textContent = 'Offline';
                    document.getElementById('bot_status').style.color = '#ff0000';
                });
        }, 5000);
    </script>
</body>
</html>"""
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            status_json = f'''{{
                "status": "alive",
                "timestamp": "{datetime.now().isoformat()}",
                "port": {PORT},
                "pid": {os.getpid()}
            }}'''
            self.wfile.write(status_json.encode('utf-8'))
        
        elif self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    """Chay web server tren port"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), KeepAliveHandler)
        print(f"[*] Web server dang chay tren port {PORT}")
        print(f"[*] Truy cap: http://localhost:{PORT}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

def keep_alive():
    """Giup bot song bang cach ping moi 5 phut"""
    while True:
        try:
            requests.get(f"http://localhost:{PORT}/ping", timeout=5)
            requests.get(f"http://localhost:{PORT}/status", timeout=5)
            requests.get(f"http://localhost:{PORT}/health", timeout=5)
            print(f"[*] Keep alive ping at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"[!] Keep alive error: {e}")
        time.sleep(300)  # 5 phut

def run_bot():
    """Chay bot chinh voi tu dong restart"""
    while True:
        try:
            print("[*] Dang khoi dong bot...")
            subprocess.run([sys.executable, "bot.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] Bot loi: {e}")
            time.sleep(5)
        except FileNotFoundError:
            print("[!] Khong tim thay bot.py!")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Loi: {e}")
            time.sleep(5)
        print("[*] Dang khoi dong lai bot...")

def main():
    print("=" * 60)
    print("    KEEPALIVE - GIU BOT 24/7")
    print("    ADMIN: @baohuyno1")
    print("=" * 60)
    print(f"[*] Port: {PORT}")
    print(f"[*] PID: {os.getpid()}")
    print(f"[*] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[*] Dang khoi dong cac service...")
    print("=" * 60)
    
    # Chay web server
    threading.Thread(target=run_web_server, daemon=True).start()
    time.sleep(2)
    
    # Chay keep alive
    threading.Thread(target=keep_alive, daemon=True).start()
    time.sleep(2)
    
    print("[*] Tat ca service da khoi dong!")
    print("[*] Bot dang chay 24/7...")
    print("=" * 60)
    
    # Chay bot chinh
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Da dung!")
        sys.exit(0)
