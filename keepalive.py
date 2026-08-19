# keepalive.py - Giữ bot chạy 24/7
import os
import sys
import subprocess
import time
import threading
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ========== WEB SERVER ==========
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
            <html>
                <head><title>🤖 Garena Checker Bot 24/7</title></head>
                <body style="font-family: Arial; text-align: center; padding: 50px; background: #0a0a0a; color: #00ff00;">
                    <h1>🤖 Garena Checker Bot</h1>
                    <p>Status: <b style="color: #00ff00;">🟢 ALIVE</b></p>
                    <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Admin: <a href="https://t.me/baohuyno1" style="color: #00ff00;">@baohuyno1</a></p>
                </body>
            </html>
            """.encode())
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
        print(f"[*] Web server chạy trên port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Lỗi web server: {e}")

def keep_alive():
    while True:
        try:
            requests.get("http://localhost:8080/ping", timeout=5)
        except:
            pass
        time.sleep(300)

def run_bot():
    while True:
        try:
            subprocess.run([sys.executable, "bot.py"], check=True)
        except:
            time.sleep(5)

def main():
    print("=" * 50)
    print("    KEEPALIVE - BOT 24/7")
    print("=" * 50)
    
    threading.Thread(target=run_web_server, daemon=True).start()
    threading.Thread(target=keep_alive, daemon=True).start()
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Dừng!")
        sys.exit(0)
