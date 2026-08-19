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
                <head>
                    <title>🤖 Garena Checker Bot 24/7</title>
                    <style>
                        body {{ font-family: Arial; text-align: center; padding: 50px; background: #0a0a0a; color: #00ff00; }}
                        h1 {{ color: #00ff00; }}
                        .status {{ color: #00ff00; font-weight: bold; }}
                        .admin {{ color: #00ff00; text-decoration: none; }}
                    </style>
                </head>
                <body>
                    <h1>🤖 Garena Checker Bot</h1>
                    <p>Status: <span class="status">🟢 ALIVE</span></p>
                    <p>Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <p>Admin: <a href="https://t.me/baohuyno1" class="admin">@baohuyno1</a></p>
                </body>
            </html>
            """.encode())
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/status':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    try:
        port = int(os.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
        print(f"[*] Web server chạy trên port {port}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Lỗi web server: {e}")

def keep_alive():
    while True:
        try:
            requests.get("http://localhost:10000/ping", timeout=5)
        except:
            pass
        time.sleep(300)

def run_bot():
    while True:
        try:
            print("[*] Đang khởi động bot...")
            subprocess.run([sys.executable, "bot.py"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] Bot lỗi: {e}")
            time.sleep(5)
        except FileNotFoundError:
            print("[!] Không tìm thấy bot.py!")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Lỗi: {e}")
            time.sleep(5)
        print("[*] Đang khởi động lại bot...")

def main():
    print("=" * 50)
    print("    KEEPALIVE - BOT 24/7")
    print("    ADMIN: @baohuyno1")
    print("=" * 50)
    
    threading.Thread(target=run_web_server, daemon=True).start()
    time.sleep(2)
    threading.Thread(target=keep_alive, daemon=True).start()
    time.sleep(2)
    
    print("[*] Bot đang chạy 24/7...")
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Dừng!")
        sys.exit(0)
