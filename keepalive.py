# keepalive.py - Giữ bot chạy 24/7 trên Replit/Railway/Heroku/VPS
import os
import sys
import subprocess
import time
import threading
import requests
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ========== WEB SERVER GIỮ BOT SỐNG ==========
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(f"""
            <!DOCTYPE html>
            <html>
                <head>
                    <title>🤖 Garena Checker Bot - 24/7</title>
                    <meta charset="UTF-8">
                    <meta name="viewport" content="width=device-width, initial-scale=1">
                    <style>
                        body {{
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                            background: linear-gradient(135deg, #0a0a0a, #1a1a2e);
                            color: #00ff00;
                            margin: 0;
                        }}
                        .container {{
                            max-width: 600px;
                            margin: 0 auto;
                            background: rgba(0,0,0,0.8);
                            padding: 40px;
                            border-radius: 20px;
                            border: 2px solid #00ff00;
                            box-shadow: 0 0 50px rgba(0,255,0,0.1);
                        }}
                        h1 {{
                            font-size: 3em;
                            margin-bottom: 10px;
                            color: #00ff00;
                            text-shadow: 0 0 20px rgba(0,255,0,0.3);
                        }}
                        .status {{
                            font-size: 1.5em;
                            padding: 15px;
                            margin: 20px 0;
                            background: rgba(0,255,0,0.1);
                            border-radius: 10px;
                            border: 1px solid #00ff00;
                        }}
                        .status .alive {{
                            color: #00ff00;
                            font-weight: bold;
                            animation: blink 1s infinite;
                        }}
                        @keyframes blink {{
                            0% {{ opacity: 1; }}
                            50% {{ opacity: 0.3; }}
                            100% {{ opacity: 1; }}
                        }}
                        .info {{
                            text-align: left;
                            padding: 20px;
                            background: rgba(255,255,255,0.05);
                            border-radius: 10px;
                            margin: 20px 0;
                        }}
                        .info-item {{
                            padding: 8px 0;
                            border-bottom: 1px solid rgba(255,255,255,0.1);
                        }}
                        .admin-link {{
                            color: #00ff00;
                            text-decoration: none;
                            font-weight: bold;
                        }}
                        .admin-link:hover {{
                            text-decoration: underline;
                        }}
                        .footer {{
                            margin-top: 30px;
                            font-size: 0.9em;
                            color: #666;
                        }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>🤖 Garena Checker Bot</h1>
                        <div class="status">
                            Status: <span class="alive">🟢 ALIVE</span>
                        </div>
                        <div class="info">
                            <div class="info-item">⏱ Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                            <div class="info-item">⏱ Uptime: <span id="uptime">Loading...</span></div>
                            <div class="info-item">👤 Admin: <a href="https://t.me/baohuyno1" class="admin-link">@baohuyno1</a></div>
                            <div class="info-item">📌 Status: <span id="bot_status">Checking...</span></div>
                        </div>
                        <div class="footer">
                            Powered by ❤️ | Bot 24/7
                        </div>
                    </div>
                    <script>
                        let startTime = new Date();
                        setInterval(() => {{
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
                        }}, 1000);
                        
                        // Check bot status
                        setInterval(() => {{
                            fetch('/ping')
                                .then(response => response.text())
                                .then(data => {{
                                    document.getElementById('bot_status').textContent = '🟢 Online';
                                    document.getElementById('bot_status').style.color = '#00ff00';
                                }})
                                .catch(() => {{
                                    document.getElementById('bot_status').textContent = '🔴 Offline';
                                    document.getElementById('bot_status').style.color = '#ff0000';
                                }});
                        }}, 5000);
                    </script>
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
        elif self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(b'{"status":"alive","timestamp":"' + str(datetime.now()).encode() + b'"}')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def log_message(self, format, *args):
        # Tắt log để tránh spam
        pass

def run_web_server():
    """Chạy web server trên port 8080"""
    try:
        port = int(os.environ.get("PORT", 8080))
        server = HTTPServer(("0.0.0.0", port), KeepAliveHandler)
        print(f"[*] Web server đang chạy trên port {port}")
        print(f"[*] Truy cập: http://localhost:{port}")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Lỗi web server: {e}")

def keep_alive():
    """Giữ bot sống bằng cách ping mỗi 5 phút"""
    while True:
        try:
            # Ping web server
            requests.get("http://localhost:8080/ping", timeout=5)
            requests.get("http://localhost:8080/status", timeout=5)
            requests.get("http://localhost:8080/health", timeout=5)
            print(f"[*] Keep alive ping at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"[!] Keep alive error: {e}")
        time.sleep(300)  # 5 phút

def run_bot():
    """Chạy bot chính với tự động restart"""
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
    print("=" * 60)
    print("    KEEPALIVE - GIỮ BOT 24/7")
    print("    ADMIN: @baohuyno1")
    print("=" * 60)
    print(f"[*] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[*] Đang khởi động các service...")
    print("=" * 60)
    
    # Chạy web server
    threading.Thread(target=run_web_server, daemon=True).start()
    time.sleep(1)
    
    # Chạy keep alive
    threading.Thread(target=keep_alive, daemon=True).start()
    time.sleep(1)
    
    print("[*] Tất cả service đã khởi động!")
    print("[*] Bot đang chạy 24/7...")
    print("=" * 60)
    
    # Chạy bot chính
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Đã dừng!")
        sys.exit(0)
