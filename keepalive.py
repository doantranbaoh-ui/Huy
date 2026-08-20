# ==================== PALOFSC - KEEPALIVE HACKER LASER V3 ====================
# Code day du: web server hieu ung laser, matrix, am thanh, keep alive

import os
import sys
import subprocess
import time
import threading
import requests
import signal
import random
import json
import struct
import math
import base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

# ========== CAU HINH ==========
PORT = int(os.environ.get("PORT", 10000))
BOT_SCRIPT = "bot.py"
START_TIME = datetime.now()

# Bien toan cuc cho stats
bot_stats = {
    "total": 0,
    "checked": 0,
    "hits": 0,
    "dead": 0,
    "errors": 0,
    "unknown": 0,
    "checking": False,
    "proxy_count": 0,
    "start_time": datetime.now().isoformat()
}

def read_bot_stats():
    """Doc thong ke tu cac file output"""
    global bot_stats
    
    hits_count = 0
    dead_count = 0
    error_count = 0
    
    try:
        if os.path.exists("hits.txt"):
            with open("hits.txt", 'r', encoding='utf-8') as f:
                hits_count = len(f.readlines())
    except:
        pass
    
    try:
        if os.path.exists("dead.txt"):
            with open("dead.txt", 'r', encoding='utf-8') as f:
                dead_count = len(f.readlines())
    except:
        pass
    
    try:
        if os.path.exists("error.txt"):
            with open("error.txt", 'r', encoding='utf-8') as f:
                error_count = len(f.readlines())
    except:
        pass
    
    bot_stats["hits"] = hits_count
    bot_stats["dead"] = dead_count
    bot_stats["errors"] = error_count
    
    return bot_stats

# ========== WEB SERVER VOI HIEU UNG TIA HACKER ==========
class HackerHandler(BaseHTTPRequestHandler):
    """Web server voi hieu ung tia hacker laser va am thanh"""
    
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_laser_page()
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            status_data = read_bot_stats()
            status_data["status"] = "alive"
            status_data["timestamp"] = datetime.now().isoformat()
            status_data["port"] = PORT
            status_data["pid"] = os.getpid()
            status_data["uptime"] = str(datetime.now() - START_TIME)
            status_json = json.dumps(status_data)
            self.wfile.write(status_json.encode('utf-8'))
        
        elif self.path == '/health':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")
        
        elif self.path == '/laser':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_full_laser_page()
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/matrix':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_matrix_page()
            self.wfile.write(html.encode('utf-8'))
        
        elif self.path == '/audio':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_hacker_audio()
            self.wfile.write(audio_data)
        
        elif self.path == '/audio2':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_cyber_audio()
            self.wfile.write(audio_data)
        
        elif self.path == '/audio3':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_techno_audio()
            self.wfile.write(audio_data)
        
        elif self.path == '/stats-page':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_stats_page()
            self.wfile.write(html.encode('utf-8'))
        
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"404 Not Found")
    
    def generate_hacker_audio(self):
        """Tao am thanh hacker don gian"""
        try:
            sample_rate = 44100
            duration = 2.0
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                value = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * 440 * t) * math.exp(-3 * t) +
                    math.sin(2 * math.pi * 880 * t) * math.exp(-5 * t) * 0.5 +
                    math.sin(2 * math.pi * 220 * t) * math.exp(-2 * t) * 0.3 +
                    math.sin(2 * math.pi * 1320 * t) * math.exp(-7 * t) * 0.2
                ))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_cyber_audio(self):
        """Tao am thanh cyberpunk"""
        try:
            sample_rate = 44100
            duration = 3.0
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                freq = 200 + 600 * (t / duration)
                value = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * freq * t) * math.exp(-1.5 * t) +
                    math.sin(2 * math.pi * freq * 2 * t) * math.exp(-2 * t) * 0.4 +
                    math.sin(2 * math.pi * freq * 0.5 * t) * math.exp(-1 * t) * 0.3
                ))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_techno_audio(self):
        """Tao am thanh techno"""
        try:
            sample_rate = 44100
            duration = 4.0
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            beat_interval = 0.25
            beat_count = int(duration / beat_interval)
            
            for i in range(num_samples):
                t = i / sample_rate
                
                beat_phase = (t % beat_interval) / beat_interval
                beat = 0
                if beat_phase < 0.1:
                    beat = math.exp(-beat_phase * 50)
                
                bass_freq = 100
                bass = math.sin(2 * math.pi * bass_freq * t) * beat
                
                hi_hat_phase = (t % 0.125) / 0.125
                hi_hat = 0
                if hi_hat_phase < 0.05:
                    hi_hat = math.exp(-hi_hat_phase * 100) * 0.3
                
                melody_freq = 440 + 220 * math.sin(2 * math.pi * 0.5 * t)
                melody = math.sin(2 * math.pi * melody_freq * t) * 0.2 * math.exp(-0.5 * (t % beat_interval))
                
                value = int(32767 * 0.4 * (bass + hi_hat + melody))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_laser_page(self):
        """Tao trang HTML voi hieu ung tia hacker va am thanh"""
        stats = read_bot_stats()
        
        hits = stats.get("hits", 0)
        dead = stats.get("dead", 0)
        errors = stats.get("errors", 0)
        
        return """<!DOCTYPE html>
<html>
<head>
    <title>GARENA CHECKER - LASER SECURITY V3</title>
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
            position: relative;
        }
        
        #laserCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 1;
        }
        
        #matrixCanvas {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            opacity: 0.3;
        }
        
        .container {
            position: relative;
            z-index: 2;
            max-width: 800px;
            margin: 30px auto;
            padding: 30px;
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid #00ff00;
            border-radius: 10px;
            box-shadow: 0 0 50px rgba(0, 255, 0, 0.3), 0 0 100px rgba(0, 255, 0, 0.1);
            animation: borderPulse 2s infinite;
        }
        
        @keyframes borderPulse {
            0%, 100% { 
                border-color: #00ff00;
                box-shadow: 0 0 30px rgba(0, 255, 0, 0.3);
            }
            25% {
                border-color: #00ffff;
                box-shadow: 0 0 60px rgba(0, 255, 255, 0.5);
            }
            50% {
                border-color: #ff00ff;
                box-shadow: 0 0 60px rgba(255, 0, 255, 0.5);
            }
            75% {
                border-color: #ffff00;
                box-shadow: 0 0 60px rgba(255, 255, 0, 0.5);
            }
        }
        
        .terminal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px;
            background: rgba(0, 255, 0, 0.1);
            border-radius: 5px;
            margin-bottom: 20px;
            border: 1px solid rgba(0, 255, 0, 0.3);
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
            animation: btnGlow 1s infinite;
        }
        
        .btn-red { 
            background: #ff5f56; 
            box-shadow: 0 0 10px #ff5f56;
        }
        .btn-yellow { 
            background: #ffbd2e; 
            box-shadow: 0 0 10px #ffbd2e;
            animation-delay: 0.3s;
        }
        .btn-green { 
            background: #27c93f; 
            box-shadow: 0 0 10px #27c93f;
            animation-delay: 0.6s;
        }
        
        @keyframes btnGlow {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .terminal-title {
            font-size: 14px;
            color: #00ff00;
            animation: titleFlicker 2s infinite;
        }
        
        @keyframes titleFlicker {
            0%, 100% { opacity: 1; }
            95% { opacity: 1; }
            96% { opacity: 0.3; }
            97% { opacity: 1; }
        }
        
        .title {
            font-size: 2.5em;
            text-align: center;
            margin-bottom: 10px;
            color: #00ff00;
            text-shadow: 0 0 20px rgba(0, 255, 0, 0.8), 0 0 40px rgba(0, 255, 0, 0.5);
            animation: glitchText 2s infinite;
        }
        
        @keyframes glitchText {
            0%, 100% { 
                transform: translateX(0);
                text-shadow: 0 0 20px #00ff00, 0 0 40px #00ff00;
            }
            20% { 
                transform: translateX(-3px);
                text-shadow: -3px 0 20px #ff0000, 3px 0 20px #00ffff;
            }
            40% { 
                transform: translateX(3px);
                text-shadow: 3px 0 20px #ff00ff, -3px 0 20px #ffff00;
            }
            60% { 
                transform: translateX(-2px);
                text-shadow: -2px 0 20px #00ffff, 2px 0 20px #ff0000;
            }
            80% { 
                transform: translateX(2px);
                text-shadow: 2px 0 20px #ffff00, -2px 0 20px #ff00ff;
            }
        }
        
        .laser-line {
            height: 2px;
            background: linear-gradient(90deg, transparent, #00ff00, transparent);
            animation: laserScan 2s linear infinite;
            margin: 10px 0;
        }
        
        @keyframes laserScan {
            0% { transform: translateX(-100%); opacity: 0; }
            10% { opacity: 1; }
            90% { opacity: 1; }
            100% { transform: translateX(100%); opacity: 0; }
        }
        
        .terminal-line {
            padding: 5px;
            margin: 5px 0;
            animation: typeIn 0.5s ease-out;
        }
        
        @keyframes typeIn {
            from { opacity: 0; transform: translateX(-30px); }
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
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
            margin: 20px 0;
        }
        
        .status-item {
            padding: 10px;
            background: rgba(0, 255, 0, 0.05);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 5px;
            font-size: 14px;
            transition: all 0.3s ease;
            text-align: center;
        }
        
        .status-item:hover {
            background: rgba(0, 255, 0, 0.15);
            border-color: #00ff00;
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.3);
        }
        
        .status-label {
            color: #666;
            font-size: 11px;
            text-transform: uppercase;
        }
        
        .status-value {
            color: #00ff00;
            font-weight: bold;
            font-size: 20px;
        }
        
        .stat-hits .status-value { color: #00ff00; }
        .stat-dead .status-value { color: #ff4444; }
        .stat-errors .status-value { color: #ff9800; }
        
        .audio-buttons {
            display: flex;
            gap: 10px;
            justify-content: center;
            margin: 15px 0;
            flex-wrap: wrap;
        }
        
        .audio-btn {
            padding: 8px 16px;
            background: rgba(0, 255, 0, 0.1);
            border: 1px solid #00ff00;
            border-radius: 5px;
            color: #00ff00;
            cursor: pointer;
            font-family: 'Courier New', monospace;
            font-size: 12px;
            transition: all 0.3s ease;
        }
        
        .audio-btn:hover {
            background: rgba(0, 255, 0, 0.3);
            box-shadow: 0 0 20px rgba(0, 255, 0, 0.5);
        }
        
        .audio-btn.active {
            background: #00ff00;
            color: #000;
        }
        
        .hacker-log {
            margin-top: 20px;
            padding: 10px;
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid rgba(0, 255, 0, 0.3);
            border-radius: 5px;
            max-height: 150px;
            overflow-y: auto;
            font-size: 12px;
        }
        
        .admin-link {
            color: #00ff00;
            text-decoration: none;
            font-weight: bold;
            animation: linkGlow 2s infinite;
        }
        
        @keyframes linkGlow {
            0%, 100% { text-shadow: 0 0 5px #00ff00; }
            50% { text-shadow: 0 0 20px #00ff00, 0 0 30px #00ff00; }
        }
        
        .admin-link:hover {
            text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00;
        }
        
        @media (max-width: 600px) {
            .container {
                margin: 15px;
                padding: 15px;
            }
            .title {
                font-size: 1.5em;
            }
            .status-grid {
                grid-template-columns: 1fr;
            }
            .audio-buttons {
                flex-direction: column;
            }
        }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <canvas id="laserCanvas"></canvas>
    <div class="container">
        <div class="terminal-header">
            <div class="terminal-buttons">
                <span class="terminal-btn btn-red"></span>
                <span class="terminal-btn btn-yellow"></span>
                <span class="terminal-btn btn-green"></span>
            </div>
            <div class="terminal-title">LASER SECURITY - ENCRYPTED V3</div>
        </div>
        
        <div class="title">GARENA CHECKER</div>
        
        <div class="laser-line"></div>
        
        <div class="terminal-line">
            <span class="prompt">Initializing laser security...</span>
            <span class="cursor"></span>
        </div>
        
        <div class="status-grid">
            <div class="status-item stat-hits">
                <div class="status-label">HITS</div>
                <div class="status-value">""" + str(hits) + """</div>
            </div>
            <div class="status-item stat-dead">
                <div class="status-label">DEAD</div>
                <div class="status-value">""" + str(dead) + """</div>
            </div>
            <div class="status-item stat-errors">
                <div class="status-label">ERRORS</div>
                <div class="status-value">""" + str(errors) + """</div>
            </div>
            <div class="status-item">
                <div class="status-label">STATUS</div>
                <div class="status-value" id="status">ALIVE</div>
            </div>
            <div class="status-item">
                <div class="status-label">UPTIME</div>
                <div class="status-value" id="uptime" style="font-size: 14px;">Calculating...</div>
            </div>
            <div class="status-item">
                <div class="status-label">ADMIN</div>
                <div class="status-value" style="font-size: 14px;"><a href="https://t.me/baohuyno1" class="admin-link">@baohuyno1</a></div>
            </div>
        </div>
        
        <div class="audio-buttons">
            <button class="audio-btn" onclick="playAudio('/audio', this)">🔊 HACKER SOUND</button>
            <button class="audio-btn" onclick="playAudio('/audio2', this)">🔊 CYBER SOUND</button>
            <button class="audio-btn" onclick="playAudio('/audio3', this)">🔊 TECHNO SOUND</button>
            <button class="audio-btn" onclick="stopAudio()">🔇 STOP</button>
        </div>
        
        <div class="hacker-log" id="hacker-log">
            <div>[SYSTEM] Laser security initialized...</div>
        </div>
    </div>
    
    <audio id="bg-audio" loop>
        <source src="/audio2" type="audio/wav">
    </audio>
    
    <script>
        // ========== MATRIX BACKGROUND ==========
        const matrixCanvas = document.getElementById('matrixCanvas');
        const matrixCtx = matrixCanvas.getContext('2d');
        
        matrixCanvas.width = window.innerWidth;
        matrixCanvas.height = window.innerHeight;
        
        const matrixChars = 'ABCDEF0123456789!@#$%^&*()_+{}[]|;:,.<>?~';
        const fontSize = 14;
        const columns = matrixCanvas.width / fontSize;
        const drops = [];
        
        for (let i = 0; i < columns; i++) {
            drops[i] = Math.random() * -100;
        }
        
        function drawMatrix() {
            matrixCtx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            matrixCtx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);
            
            matrixCtx.fillStyle = '#00ff00';
            matrixCtx.font = fontSize + 'px monospace';
            
            for (let i = 0; i < drops.length; i++) {
                const text = matrixChars[Math.floor(Math.random() * matrixChars.length)];
                matrixCtx.fillText(text, i * fontSize, drops[i] * fontSize);
                
                if (drops[i] * fontSize > matrixCanvas.height && Math.random() > 0.975) {
                    drops[i] = 0;
                }
                
                drops[i]++;
            }
        }
        
        setInterval(drawMatrix, 50);
        
        // ========== LASER EFFECT ==========
        const laserCanvas = document.getElementById('laserCanvas');
        const laserCtx = laserCanvas.getContext('2d');
        
        laserCanvas.width = window.innerWidth;
        laserCanvas.height = window.innerHeight;
        
        const lasers = [];
        const laserColors = ['#00ff00', '#00ffff', '#ff00ff', '#ffff00', '#ff0000', '#ffffff'];
        
        class LaserBeam {
            constructor() {
                this.reset();
            }
            
            reset() {
                this.x = Math.random() * laserCanvas.width;
                this.y = Math.random() * laserCanvas.height;
                this.targetX = Math.random() * laserCanvas.width;
                this.targetY = Math.random() * laserCanvas.height;
                this.color = laserColors[Math.floor(Math.random() * laserColors.length)];
                this.width = Math.random() * 2 + 0.5;
                this.speed = Math.random() * 5 + 2;
                this.life = 0;
                this.maxLife = Math.random() * 50 + 30;
                this.particles = [];
            }
            
            update() {
                this.life++;
                
                if (Math.random() > 0.5) {
                    this.particles.push({
                        x: this.x + (this.targetX - this.x) * Math.random(),
                        y: this.y + (this.targetY - this.y) * Math.random(),
                        vx: (Math.random() - 0.5) * 2,
                        vy: (Math.random() - 0.5) * 2,
                        life: 0,
                        maxLife: Math.random() * 20 + 10
                    });
                }
                
                for (let i = this.particles.length - 1; i >= 0; i--) {
                    const p = this.particles[i];
                    p.x += p.vx;
                    p.y += p.vy;
                    p.life++;
                    if (p.life > p.maxLife) {
                        this.particles.splice(i, 1);
                    }
                }
                
                if (this.life > this.maxLife) {
                    this.reset();
                }
            }
            
            draw(ctx) {
                const progress = this.life / this.maxLife;
                const alpha = progress < 0.2 ? progress * 5 : progress > 0.8 ? (1 - progress) * 5 : 1;
                
                const gradient = ctx.createLinearGradient(this.x, this.y, this.targetX, this.targetY);
                gradient.addColorStop(0, this.color + '00');
                gradient.addColorStop(0.5, this.color + 'FF');
                gradient.addColorStop(1, this.color + '00');
                
                ctx.strokeStyle = gradient;
                ctx.lineWidth = this.width;
                ctx.globalAlpha = alpha;
                ctx.beginPath();
                ctx.moveTo(this.x, this.y);
                ctx.lineTo(this.targetX, this.targetY);
                ctx.stroke();
                
                for (const p of this.particles) {
                    const pAlpha = 1 - (p.life / p.maxLife);
                    ctx.fillStyle = this.color;
                    ctx.globalAlpha = pAlpha * alpha;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
                
                ctx.globalAlpha = 1;
            }
        }
        
        for (let i = 0; i < 20; i++) {
            lasers.push(new LaserBeam());
        }
        
        function drawLasers() {
            laserCtx.clearRect(0, 0, laserCanvas.width, laserCanvas.height);
            
            for (const laser of lasers) {
                laser.update();
                laser.draw(laserCtx);
            }
            
            if (Math.random() > 0.98) {
                const flashX = Math.random() * laserCanvas.width;
                const flashY = Math.random() * laserCanvas.height;
                const flashRadius = Math.random() * 30 + 10;
                const flashColor = laserColors[Math.floor(Math.random() * laserColors.length)];
                
                const gradient = laserCtx.createRadialGradient(flashX, flashY, 0, flashX, flashY, flashRadius);
                gradient.addColorStop(0, flashColor + 'FF');
                gradient.addColorStop(1, flashColor + '00');
                
                laserCtx.fillStyle = gradient;
                laserCtx.beginPath();
                laserCtx.arc(flashX, flashY, flashRadius, 0, Math.PI * 2);
                laserCtx.fill();
            }
            
            requestAnimationFrame(drawLasers);
        }
        
        drawLasers();
        
        // ========== AUDIO SYSTEM ==========
        const bgAudio = document.getElementById('bg-audio');
        let currentAudio = null;
        
        function playAudio(url, button) {
            stopAudio();
            
            currentAudio = new Audio(url);
            currentAudio.loop = true;
            currentAudio.volume = 0.5;
            currentAudio.play().catch(e => console.log('Audio error:', e));
            
            document.querySelectorAll('.audio-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            
            if (button) {
                button.classList.add('active');
            }
        }
        
        function stopAudio() {
            if (currentAudio) {
                currentAudio.pause();
                currentAudio = null;
            }
            
            document.querySelectorAll('.audio-btn').forEach(btn => {
                btn.classList.remove('active');
            });
        }
        
        // Tu dong play nhac nen
        bgAudio.volume = 0.3;
        bgAudio.play().catch(e => console.log('Auto play blocked:', e));
        
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
            'INITIALIZING LASER PROTOCOL...',
            'ESTABLISHING SECURE CONNECTION...',
            'BYPASSING FIREWALL...',
            'DECRYPTING DATA...',
            'ACCESS GRANTED...',
            'SCANNING NETWORK...',
            'INJECTING PAYLOAD...',
            'TRACING IP ADDRESS...',
            'MASKING IDENTITY...',
            'ENCRYPTING CHANNEL...',
            'ACTIVATING LASER DEFENSE...',
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
        
        // ========== STATS UPDATE ==========
        setInterval(() => {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    document.querySelector('.stat-hits .status-value').textContent = data.hits || 0;
                    document.querySelector('.stat-dead .status-value').textContent = data.dead || 0;
                    document.querySelector('.stat-errors .status-value').textContent = data.errors || 0;
                })
                .catch(err => console.log('Stats error:', err));
        }, 10000);
        
        // ========== RESIZE HANDLER ==========
        window.addEventListener('resize', () => {
            matrixCanvas.width = window.innerWidth;
            matrixCanvas.height = window.innerHeight;
            laserCanvas.width = window.innerWidth;
            laserCanvas.height = window.innerHeight;
        });
        
        // ========== MOUSE LASER EFFECT ==========
        document.addEventListener('mousemove', (e) => {
            if (Math.random() > 0.7) {
                const laser = new LaserBeam();
                laser.x = e.clientX;
                laser.y = e.clientY;
                laser.targetX = Math.random() * laserCanvas.width;
                laser.targetY = Math.random() * laserCanvas.height;
                lasers.push(laser);
                
                if (lasers.length > 40) {
                    lasers.shift();
                }
            }
        });
    </script>
</body>
</html>"""
    
    def generate_full_laser_page(self):
        """Tao trang laser fullscreen"""
        return """<!DOCTYPE html>
<html>
<head>
    <title>LASER MODE</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; }
        body { background: #000; overflow: hidden; cursor: crosshair; }
        canvas { display: block; }
    </style>
</head>
<body>
    <canvas id="laserCanvas"></canvas>
    <script>
        const canvas = document.getElementById('laserCanvas');
        const ctx = canvas.getContext('2d');
        
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const lasers = [];
        const colors = ['#00ff00', '#00ffff', '#ff00ff', '#ffff00', '#ff0000', '#ffffff', '#ff8800'];
        
        class Laser {
            constructor(x, y) {
                this.x = x || Math.random() * canvas.width;
                this.y = y || Math.random() * canvas.height;
                this.targetX = Math.random() * canvas.width;
                this.targetY = Math.random() * canvas.height;
                this.color = colors[Math.floor(Math.random() * colors.length)];
                this.width = Math.random() * 3 + 1;
                this.life = 0;
                this.maxLife = Math.random() * 100 + 50;
                this.particles = [];
            }
            
            update() {
                this.life++;
                
                if (Math.random() > 0.3) {
                    this.particles.push({
                        x: this.x + (this.targetX - this.x) * Math.random(),
                        y: this.y + (this.targetY - this.y) * Math.random(),
                        vx: (Math.random() - 0.5) * 3,
                        vy: (Math.random() - 0.5) * 3,
                        life: 0,
                        maxLife: Math.random() * 30 + 10
                    });
                }
                
                for (let i = this.particles.length - 1; i >= 0; i--) {
                    const p = this.particles[i];
                    p.x += p.vx;
                    p.y += p.vy;
                    p.life++;
                    if (p.life > p.maxLife) {
                        this.particles.splice(i, 1);
                    }
                }
                
                if (this.life > this.maxLife) {
                    const index = lasers.indexOf(this);
                    if (index > -1) {
                        lasers.splice(index, 1);
                    }
                }
            }
            
            draw() {
                const progress = this.life / this.maxLife;
                const alpha = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
                
                const gradient = ctx.createLinearGradient(this.x, this.y, this.targetX, this.targetY);
                gradient.addColorStop(0, this.color + '00');
                gradient.addColorStop(0.5, this.color + 'FF');
                gradient.addColorStop(1, this.color + '00');
                
                ctx.strokeStyle = gradient;
                ctx.lineWidth = this.width;
                ctx.globalAlpha = alpha;
                ctx.beginPath();
                ctx.moveTo(this.x, this.y);
                ctx.lineTo(this.targetX, this.targetY);
                ctx.stroke();
                
                for (const p of this.particles) {
                    const pAlpha = 1 - (p.life / p.maxLife);
                    ctx.fillStyle = this.color;
                    ctx.globalAlpha = pAlpha * alpha;
                    ctx.beginPath();
                    ctx.arc(p.x, p.y, 2, 0, Math.PI * 2);
                    ctx.fill();
                }
                
                ctx.globalAlpha = 1;
            }
        }
        
        function createLaser() {
            if (lasers.length < 60) {
                lasers.push(new Laser());
            }
        }
        
        function draw() {
            ctx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            
            for (const laser of lasers) {
                laser.update();
                laser.draw();
            }
            
            if (Math.random() > 0.95) {
                createLaser();
            }
            
            requestAnimationFrame(draw);
        }
        
        for (let i = 0; i < 25; i++) {
            createLaser();
        }
        
        draw();
        
        document.addEventListener('mousemove', (e) => {
            if (Math.random() > 0.5) {
                lasers.push(new Laser(e.clientX, e.clientY));
                if (lasers.length > 60) {
                    lasers.shift();
                }
            }
        });
        
        document.addEventListener('click', (e) => {
            for (let i = 0; i < 10; i++) {
                lasers.push(new Laser(e.clientX, e.clientY));
            }
            if (lasers.length > 60) {
                lasers.splice(0, 10);
            }
        });
        
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    </script>
</body>
</html>"""
    
    def generate_matrix_page(self):
        """Tao trang matrix fullscreen"""
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
    
    def generate_stats_page(self):
        """Tao trang thong ke chi tiet"""
        stats = read_bot_stats()
        
        hits = stats.get("hits", 0)
        dead = stats.get("dead", 0)
        errors = stats.get("errors", 0)
        total = hits + dead + errors
        
        return """<!DOCTYPE html>
<html>
<head>
    <title>STATS - GARENA CHECKER</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0a;
            color: #00ff00;
            padding: 20px;
            min-height: 100vh;
        }
        .container { max-width: 800px; margin: 0 auto; }
        .title {
            text-align: center;
            font-size: 2em;
            margin-bottom: 30px;
            text-shadow: 0 0 20px #00ff00;
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: #111;
            border: 1px solid #00ff00;
            border-radius: 10px;
            padding: 20px;
            text-align: center;
            box-shadow: 0 0 20px rgba(0,255,0,0.2);
        }
        .stat-value { font-size: 2.5em; font-weight: bold; }
        .stat-label { font-size: 0.8em; color: #666; margin-top: 5px; }
        .hits .stat-value { color: #00ff00; }
        .dead .stat-value { color: #ff4444; }
        .errors .stat-value { color: #ff9800; }
        .total .stat-value { color: #00ffff; }
        .back-link {
            display: block;
            text-align: center;
            color: #00ff00;
            text-decoration: none;
            margin-top: 30px;
            padding: 10px;
            border: 1px solid #00ff00;
            border-radius: 5px;
        }
        .back-link:hover {
            background: #00ff00;
            color: #000;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="title">📊 STATISTICS</div>
        <div class="stats-grid">
            <div class="stat-card hits">
                <div class="stat-value">""" + str(hits) + """</div>
                <div class="stat-label">✅ HITS</div>
            </div>
            <div class="stat-card dead">
                <div class="stat-value">""" + str(dead) + """</div>
                <div class="stat-label">❌ DEAD</div>
            </div>
            <div class="stat-card errors">
                <div class="stat-value">""" + str(errors) + """</div>
                <div class="stat-label">⚠️ ERRORS</div>
            </div>
            <div class="stat-card total">
                <div class="stat-value">""" + str(total) + """</div>
                <div class="stat-label">📊 TOTAL</div>
            </div>
        </div>
        <a href="/" class="back-link">⬅ BACK TO DASHBOARD</a>
    </div>
</body>
</html>"""
    
    def log_message(self, format, *args):
        """Tat log de tranh spam"""
        pass

# ========== HAM CHAY WEB SERVER ==========
def run_web_server():
    """Chay web server voi hieu ung tia hacker va am thanh"""
    try:
        server = HTTPServer(("0.0.0.0", PORT), HackerHandler)
        print(f"[*] Web server laser hacker dang chay tren port {PORT}")
        print(f"[*] Truy cap: http://localhost:{PORT}")
        print(f"[*] Laser mode: http://localhost:{PORT}/laser")
        print(f"[*] Matrix mode: http://localhost:{PORT}/matrix")
        print(f"[*] Stats: http://localhost:{PORT}/stats-page")
        print(f"[*] Audio 1: http://localhost:{PORT}/audio")
        print(f"[*] Audio 2: http://localhost:{PORT}/audio2")
        print(f"[*] Audio 3: http://localhost:{PORT}/audio3")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

# ========== HAM KEEP ALIVE ==========
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
        time.sleep(300)

# ========== HAM CHAY BOT ==========
def run_bot():
    """Chay bot chinh voi tu dong restart"""
    while True:
        try:
            print("[*] Dang khoi dong bot...")
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

# ========== HIEU UNG CONSOLE ==========
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
║           LASER SECURITY - ENCRYPTED V3              ║
║                                                      ║
╚══════════════════════════════════════════════════════╝
    """
    print("\033[92m" + banner + "\033[0m")

def main():
    """Ham chinh"""
    print_hacker_banner()
    
    print("=" * 60)
    print("    KEEPALIVE HACKER LASER EFFECTS V3")
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
    print("[*] Truy cap web de xem hieu ung laser hacker va am thanh")
    print("=" * 60)
    
    # Chay bot chinh
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Da dung!")
        sys.exit(0)
