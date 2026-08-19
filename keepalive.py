# keepalive.py - KEEPALIVE HACKER EFFECTS V2.0
# Tác giả: palofsc
# Mục đích: Giữ bot chạy 24/7 với hiệu ứng hacker matrix

import os
import sys
import subprocess
import time
import threading
import requests
import signal
import random
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ========== CẤU HÌNH ==========
PORT = int(os.environ.get("PORT", 10000))
BOT_SCRIPT = "bot.py"
START_TIME = datetime.now()

# ========== DANH SÁCH MÃ ĐỘC ĐỂ HIỂN THỊ ==========
HACKER_CODES = [
    "0x7F3A9C", "0xDEADBEEF", "0xC0FFEE", "0xBADC0DE",
    "0xFEEDFACE", "0xCAFEBABE", "0xDEADCODE", "0xFACEFEED",
    "0xB105F00D", "0xD15EA5E", "0xBAADF00D", "0xDEADC0DE"
]

HACKER_MESSAGES = [
    "INITIALIZING PROTOCOL...",
    "ESTABLISHING SECURE CONNECTION...",
    "BYPASSING FIREWALL...",
    "DECRYPTING DATA...",
    "ACCESS GRANTED...",
    "SCANNING NETWORK...",
    "INJECTING PAYLOAD...",
    "TRACING IP ADDRESS...",
    "MASKING IDENTITY...",
    "ENCRYPTING CHANNEL..."
]

# ========== WEB SERVER VỚI HIỆU ỨNG HACKER ==========
class HackerHandler(BaseHTTPRequestHandler):
    """Web server với hiệu ứng hacker matrix"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_hacker_page()
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            status_json = json.dumps({
                "status": "alive",
                "timestamp": datetime.now().isoformat(),
                "port": PORT,
                "pid": os.getpid(),
                "uptime": str(datetime.now() - START_TIME)
            })
            self.wfile.write(status_json.encode('utf-8'))
        
        elif self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        
        elif self.path == '/matrix':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_matrix_page()
            self.wfile.write(html.encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def generate_hacker_page(self):
        """Tạo trang HTML với hiệu ứng hacker"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>GARENA CHECKER - SECURE TERMINAL</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #00ff00;
            overflow: hidden;
            height: 100vh;
            cursor: crosshair;
        }
        
        #matrix {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
            opacity: 0.3;
        }
        
        .container {
            position: relative;
            z-index: 2;
            max-width: 800px;
            margin: 50px auto;
            padding: 30px;
            background: rgba(0, 0, 0, 0.9);
            border: 2px solid #00ff00;
            border-radius: 10px;
            box-shadow: 0 0 30px rgba(0, 255, 0, 0.2);
            animation: borderGlow 2s infinite;
        }
        
        @keyframes borderGlow {
            0% { box-shadow: 0 0 30px rgba(0, 255, 0, 0.2); }
            50% { box-shadow: 0 0 60px rgba(0, 255, 0, 0.5); }
            100% { box-shadow: 0 0 30px rgba(0, 255, 0, 0.2); }
        }
        
        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: rgba(0, 255, 0, 0.1);
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .terminal-buttons {
            display: flex;
            gap: 8px;
        }
        
        .terminal-btn {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            display: inline-block;
        }
        
        .btn-red { background: #ff5f56; }
        .btn-yellow { background: #ffbd2e; }
        .btn-green { background: #27c93f; }
        
        .terminal-title {
            font-size: 14px;
            color: #00ff00;
        }
        
        .title {
            font-size: 3em;
            text-align: center;
            margin-bottom: 10px;
            color: #00ff00;
            text-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
            animation: glitch 3s infinite;
        }
        
        @keyframes glitch {
            0% { text-shadow: 0 0 20px rgba(0, 255, 0, 0.5); }
            25% { text-shadow: -2px 0 20px rgba(255, 0, 0, 0.5), 2px 0 20px rgba(0, 0, 255, 0.5); }
            50% { text-shadow: 0 0 20px rgba(0, 255, 0, 0.5); }
            75% { text-shadow: 2px 0 20px rgba(255, 0, 0, 0.5), -2px 0 20px rgba(0, 0, 255, 0.5); }
            100% { text-shadow: 0 0 20px rgba(0, 255, 0, 0.5); }
        }
        
        .terminal-line {
            padding: 5px;
            margin: 5px 0;
            animation: typeIn 0.5s ease-out;
        }
        
        @keyframes typeIn {
            from { opacity: 0; transform: translateX(-20px); }
            to { opacity: 1; transform: translateX(0); }
        }
        
        .prompt {
            color: #00ff00;
        }
        
        .prompt::before {
            content: 'root@hacker:~# ';
            color: #00ff00;
        }
        
        .cursor {
            display: inline-block;
            width: 10px;
            height: 20px;
            background: #00ff00;
            animation: blink 1s infinite;
            vertical-align: middle;
        }
        
        @keyframes blink {
            0%, 49% { opacity: 1; }
            50%, 100% { opacity: 0; }
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        
        .status-item {
            padding: 10px;
            background: rgba(0, 255, 0, 0.05);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 5px;
            font-size: 14px;
        }
        
        .status-label {
            color: #666;
            font-size: 12px;
        }
        
        .status-value {
            color: #00ff00;
            font-weight: bold;
        }
        
        .progress-bar {
            width: 100%;
            height: 20px;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            border-radius: 10px;
            overflow: hidden;
            margin: 10px 0;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #00ff00, #00cc00);
            width: 0%;
            animation: progress 3s infinite;
        }
        
        @keyframes progress {
            0% { width: 0%; }
            50% { width: 80%; }
            100% { width: 100%; }
        }
        
        .hacker-log {
            margin-top: 20px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 5px;
            max-height: 200px;
            overflow-y: auto;
            font-size: 12px;
        }
        
        .admin-link {
            color: #00ff00;
            text-decoration: none;
            font-weight: bold;
        }
        
        .admin-link:hover {
            text-shadow: 0 0 10px #00ff00;
        }
        
        @media (max-width: 600px) {
            .container {
                margin: 20px;
                padding: 20px;
            }
            .title {
                font-size: 2em;
            }
            .status-grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <canvas id="matrix"></canvas>
    <div class="container">
        <div class="terminal-header">
            <div class="terminal-buttons">
                <span class="terminal-btn btn-red"></span>
                <span class="terminal-btn btn-yellow"></span>
                <span class="terminal-btn btn-green"></span>
            </div>
            <div class="terminal-title">SECURE TERMINAL - ENCRYPTED</div>
        </div>
        
        <div class="title">GARENA CHECKER</div>
        
        <div class="terminal-line">
            <span class="prompt">Initializing secure connection...</span>
            <span class="cursor"></span>
        </div>
        
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        
        <div class="status-grid">
            <div class="status-item">
                <div class="status-label">STATUS</div>
                <div class="status-value" id="status">ALIVE</div>
            </div>
            <div class="status-item">
                <div class="status-label">UPTIME</div>
                <div class="status-value" id="uptime">Calculating...</div>
            </div>
            <div class="status-item">
                <div class="status-label">ADMIN</div>
                <div class="status-value"><a href="https://t.me/baohuyno1" class="admin-link">@baohuyno1</a></div>
            </div>
            <div class="status-item">
                <div class="status-label">PORT</div>
                <div class="status-value">""" + str(PORT) + """</div>
            </div>
        </div>
        
        <div class="hacker-log" id="hacker-log">
            <div>[SYSTEM] Initializing...</div>
        </div>
    </div>
    
    <script>
        // ========== MATRIX EFFECT ==========
        const canvas = document.getElementById('matrix');
        const ctx = canvas.getContext('2d');
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const matrixChars = 'ABCDEF0123456789!@#$%^&*()_+{}[]|;:,.<>?~';
        const fontSize = 14;
        const columns = canvas.width / fontSize;
        const drops = [];
        
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -100;
        }
        
        function drawMatrix() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            ctx.fillStyle = '#00ff00';
            ctx.font = fontSize + 'px monospace';
            
            for (let i = 0; i < drops.length; i++) {
                const text = matrixChars[Math.floor(Math.random() * matrixChars.length)];
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                
                drops[i]++;
            }
        }
        
        setInterval(drawMatrix, 50);
        
        // ========== UPTIME COUNTER ==========
        const startTime = new Date();
        
        setInterval(() => {
            const now = new Date();
            const diff = Math.floor((now - startTime) / 1000);
            const days = Math.floor(diff / 86400);
            const hours = Math.floor((diff % 86400) / 3600);
            const minutes = Math.floor((diff % 3600) / 60);
            const seconds = diff % 60;
            
            let uptimeStr = '';
            if (days > 0) uptimeStr += days + 'd ';
            uptimeStr += hours + 'h ' + minutes + 'm ' + seconds + 's';
            
            document.getElementById('uptime').textContent = uptimeStr;
        }, 1000);
        
        // ========== HACKER LOG ==========
        const hackerMessages = [
            'INITIALIZING PROTOCOL...',
            'ESTABLISHING SECURE CONNECTION...',
            'BYPASSING FIREWALL...',
            'DECRYPTING DATA...',
            'ACCESS GRANTED...',
            'SCANNING NETWORK...',
            'INJECTING PAYLOAD...',
            'TRACING IP ADDRESS...',
            'MASKING IDENTITY...',
            'ENCRYPTING CHANNEL...',
            'VERIFYING CREDENTIALS...',
            'SYSTEM ONLINE...'
        ];
        
        const hackerCodes = [
            '0x7F3A9C', '0xDEADBEEF', '0xC0FFEE', '0xBADC0DE',
            '0xFEEDFACE', '0xCAFEBABE', '0xDEADCODE', '0xFACEFEED',
            '0xB105F00D', '0xD15EA5E', '0xBAADF00D', '0xDEADC0DE'
        ];
        
        const logElement = document.getElementById('hacker-log');
        let messageIndex = 0;
        
        setInterval(() => {
            const message = hackerMessages[messageIndex % hackerMessages.length];
            const code = hackerCodes[Math.floor(Math.random() * hackerCodes.length)];
            const timestamp = new Date().toLocaleTimeString();
            const logEntry = document.createElement('div');
            logEntry.textContent = '[' + timestamp + '] ' + message + ' ' + code;
            logEntry.style.color = '#00ff00';
            logEntry.style.opacity = '0.7';
            logElement.appendChild(logEntry);
            logElement.scrollTop = logElement.scrollHeight;
            messageIndex++;
            
            if (logElement.children.length > 20) {
                logElement.removeChild(logElement.firstChild);
            }
        }, 2000);
        
        // ========== PING CHECK ==========
        setInterval(() => {
            fetch('/ping')
                .then(response => response.text())
                .then(data => {
                    document.getElementById('status').textContent = 'ALIVE';
                    document.getElementById('status').style.color = '#00ff00';
                })
                .catch(() => {
                    document.getElementById('status').textContent = 'OFFLINE';
                    document.getElementById('status').style.color = '#ff0000';
                });
        }, 5000);
        
        // ========== RESIZE HANDLER ==========
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    </script>
</body>
</html>"""
    
    def generate_matrix_page(self):
        """Tạo trang matrix fullscreen"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>MATRIX MODE</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; }
        body { background: #000; overflow: hidden; }
        canvas { display: block; }
    </style>
</head>
<body>
    <canvas id="matrix"></canvas>
    <script>
        const canvas = document.getElementById('matrix');
        const ctx = canvas.getContext('2d');
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const chars = 'アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
        const fontSize = 16;
        const columns = canvas.width / fontSize;
        const drops = [];
        
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -100;
        }
        
        function draw() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            for (let i = 0; i < drops.length; i++) {
                const text = chars[Math.floor(Math.random() * chars.length)];
                
                if (Math.random() > 0.95) {
                    ctx.fillStyle = '#ffffff';
                } else {
                    ctx.fillStyle = '#00ff00';
                }
                
                ctx.font = fontSize + 'px monospace';
                ctx.fillText(text, i * fontSize, drops[i] * fontSize);
                
                if (drops[i] * fontSize > canvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                
                drops[i]++;
            }
        }
        
        setInterval(draw, 33);
        
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    </script>
</body>
</html>"""
    
    def log_message(self, format, *args):
        """Tắt log để tránh spam"""
        pass

# ========== HÀM CHẠY WEB SERVER ==========
def run_web_server():
    """Chạy web server với hiệu ứng hacker"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), HackerHandler)
        print(f"[*] Web server hacker dang chay tren port {PORT}")
        print(f"[*] Truy cap: http://localhost:{PORT}")
        print(f"[*] Matrix mode: http://localhost:{PORT}/matrix")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

# ========== HÀM KEEP ALIVE ==========
def keep_alive():
    """Giữ bot sống bằng cách ping mỗi 5 phút"""
    while True:
        try:
            requests.get(f"http://localhost:{PORT}/ping", timeout=5)
            requests.get(f"http://localhost:{PORT}/status", timeout=5)
            requests.get(f"http://localhost:{PORT}/health", timeout=5)
            print(f"[*] Keep alive ping at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            print(f"[!] Keep alive error: {e}")
        time.sleep(300)  # 5 phút

# ========== HÀM CHẠY BOT ==========
def run_bot():
    """Chạy bot chính với tự động restart"""
    while True:
        try:
            print("[*] Dang khoi dong bot...")
            # Sử dụng subprocess để chạy bot.py
            subprocess.run([sys.executable, BOT_SCRIPT], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[!] Bot loi: {e}")
            time.sleep(5)
        except FileNotFoundError:
            print("[!] Khong tim thay bot.py!")
            print("[*] Dang tim bot.py trong thu muc hien tai...")
            time.sleep(10)
        except Exception as e:
            print(f"[!] Loi: {e}")
            time.sleep(5)
        print("[*] Dang khoi dong lai bot...")

# ========== HIỆU ỨNG CONSOLE ==========
def print_hacker_banner():
    """In banner hacker ra console"""
    banner = """
╔══════════════════════════════════════════════════════╗
║                                                      ║
║     ██████╗  █████╗ ██████╗ ███████╗███╗   ██╗      ║
║    ██╔════╝ ██╔══██╗██╔══██╗██╔════╝████╗  ██║      ║
║    ██║  ███╗███████║██████╔╝█████╗  ██╔██╗ ██║      ║
║    ██║   ██║██╔══██║██╔══██╗██╔══╝  ██║╚██╗██║      ║
║    ╚██████╔╝██║  ██║██║  ██║███████╗██║ ╚████║      ║
║     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝╚═╝  ╚═══╝      ║
║                                                      ║
║           SECURE TERMINAL - ENCRYPTED                ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """
    print("\033[92m" + banner + "\033[0m")

def main():
    """Hàm chính"""
    print_hacker_banner()
    
    print("=" * 60)
    print("    KEEPALIVE HACKER EFFECTS V2.0")
    print("    ADMIN: @baohuyno1")
    print("=" * 60)
    print(f"[*] Port: {PORT}")
    print(f"[*] PID: {os.getpid()}")
    print(f"[*] Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("[*] Dang khoi dong cac service...")
    print("=" * 60)
    
    # Chạy web server
    threading.Thread(target=run_web_server, daemon=True).start()
    time.sleep(2)
    
    # Chạy keep alive
    threading.Thread(target=keep_alive, daemon=True).start()
    time.sleep(2)
    
    print("[*] Tat ca service da khoi dong!")
    print("[*] Bot dang chay 24/7...")
    print("[*] Truy cap web de xem hieu ung hacker")
    print("=" * 60)
    
    # Chạy bot chính
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Da dung!")
        sys.exit(0)
