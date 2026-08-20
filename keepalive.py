# ========================================================================
#    KEEPALIVE HACKER LASER EFFECTS V3 - DAY DU TIA HACKER
# ========================================================================
#    - Hieu ung tia laser hacker day du khi click
#    - Nhieu mau sac, tia to, hat bui
#    - Am thanh phat khi an nut
#    - Hieu ung tia laser truc tiep tu con tro chuot
# ========================================================================

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
        
        elif self.path == '/audio-click':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_click_audio()
            self.wfile.write(audio_data)
        
        elif self.path == '/audio-laser':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_laser_audio()
            self.wfile.write(audio_data)
        
        elif self.path == '/audio-explosion':
            self.send_response(200)
            self.send_header('Content-type', 'audio/wav')
            self.send_header('Cache-Control', 'no-cache')
            self.end_headers()
            audio_data = self.generate_explosion_audio()
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
    
    def generate_click_audio(self):
        """Tao am thanh click khi an nut"""
        try:
            sample_rate = 44100
            duration = 0.1
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                value = int(32767 * 0.5 * math.exp(-t * 100) * (
                    math.sin(2 * math.pi * 1000 * t) * 0.5 +
                    math.sin(2 * math.pi * 2000 * t) * 0.3
                ))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_laser_audio(self):
        """Tao am thanh laser ban ra"""
        try:
            sample_rate = 44100
            duration = 0.3
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                freq = 2000 - 1500 * (t / duration)
                value = int(32767 * 0.4 * math.exp(-t * 10) * math.sin(2 * math.pi * freq * t))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_explosion_audio(self):
        """Tao am thanh no"""
        try:
            sample_rate = 44100
            duration = 0.5
            num_samples = int(sample_rate * duration)
            
            data_size = num_samples * 2
            header = b'RIFF' + struct.pack('<I', 36 + data_size) + b'WAVE'
            header += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 1, sample_rate, sample_rate * 2, 2, 16)
            header += b'data' + struct.pack('<I', data_size)
            
            audio_data = bytearray()
            for i in range(num_samples):
                t = i / sample_rate
                value = int(32767 * 0.5 * math.exp(-t * 8) * (
                    math.sin(2 * math.pi * 200 * t) * 0.3 +
                    math.sin(2 * math.pi * 400 * t) * 0.5 +
                    math.sin(2 * math.pi * 800 * t) * 0.3 +
                    math.sin(2 * math.pi * 1600 * t) * 0.1
                ))
                audio_data += struct.pack('<h', value)
            
            return header + bytes(audio_data)
        except:
            return b''
    
    def generate_laser_page(self):
        """Tao trang HTML voi hieu ung tia hacker day du"""
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
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Courier New', monospace;
            background: #000;
            color: #00ff00;
            overflow: hidden;
            height: 100vh;
            cursor: crosshair;
            position: relative;
        }
        #laserCanvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 1; pointer-events: none; }
        #matrixCanvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; z-index: 0; opacity: 0.25; }
        .container {
            position: relative; z-index: 2;
            max-width: 800px; margin: 30px auto; padding: 30px;
            background: rgba(0, 0, 0, 0.85);
            border: 2px solid #00ff00;
            border-radius: 10px;
            box-shadow: 0 0 50px rgba(0, 255, 0, 0.3), 0 0 100px rgba(0, 255, 0, 0.1);
            animation: borderPulse 3s infinite;
        }
        @keyframes borderPulse {
            0%, 100% { border-color: #00ff00; box-shadow: 0 0 30px rgba(0,255,0,0.3); }
            25% { border-color: #00ffff; box-shadow: 0 0 60px rgba(0,255,255,0.5); }
            50% { border-color: #ff00ff; box-shadow: 0 0 60px rgba(255,0,255,0.5); }
            75% { border-color: #ffff00; box-shadow: 0 0 60px rgba(255,255,0,0.5); }
        }
        .terminal-header {
            display: flex; justify-content: space-between; align-items: center;
            padding: 10px; background: rgba(0,255,0,0.1);
            border-radius: 5px; margin-bottom: 20px;
            border: 1px solid rgba(0,255,0,0.3);
        }
        .terminal-buttons { display: flex; gap: 8px; }
        .terminal-btn {
            width: 12px; height: 12px; border-radius: 50%;
            display: inline-block; animation: btnGlow 1s infinite;
            cursor: pointer; transition: all 0.3s ease;
        }
        .terminal-btn:hover { transform: scale(1.4); }
        .btn-red { background: #ff5f56; box-shadow: 0 0 10px #ff5f56; }
        .btn-yellow { background: #ffbd2e; box-shadow: 0 0 10px #ffbd2e; animation-delay: 0.3s; }
        .btn-green { background: #27c93f; box-shadow: 0 0 10px #27c93f; animation-delay: 0.6s; }
        @keyframes btnGlow { 0%,100%{opacity:1;} 50%{opacity:0.5;} }
        .terminal-title { font-size: 14px; color: #00ff00; animation: titleFlicker 2s infinite; }
        @keyframes titleFlicker { 0%,100%{opacity:1;} 95%{opacity:1;} 96%{opacity:0.3;} 97%{opacity:1;} }
        .title {
            font-size: 2.5em; text-align: center; margin-bottom: 10px;
            color: #00ff00; text-shadow: 0 0 20px rgba(0,255,0,0.8), 0 0 40px rgba(0,255,0,0.5);
            animation: glitchText 2s infinite; cursor: pointer;
            transition: all 0.3s ease;
        }
        .title:hover { transform: scale(1.05); text-shadow: 0 0 40px #00ff00, 0 0 80px #00ff00; }
        @keyframes glitchText {
            0%,100%{transform:translateX(0);text-shadow:0 0 20px #00ff00,0 0 40px #00ff00;}
            20%{transform:translateX(-3px);text-shadow:-3px 0 20px #ff0000,3px 0 20px #00ffff;}
            40%{transform:translateX(3px);text-shadow:3px 0 20px #ff00ff,-3px 0 20px #ffff00;}
            60%{transform:translateX(-2px);text-shadow:-2px 0 20px #00ffff,2px 0 20px #ff0000;}
            80%{transform:translateX(2px);text-shadow:2px 0 20px #ffff00,-2px 0 20px #ff00ff;}
        }
        .laser-line {
            height: 2px; background: linear-gradient(90deg, transparent, #00ff00, transparent);
            animation: laserScan 2s linear infinite; margin: 10px 0;
        }
        @keyframes laserScan { 0%{transform:translateX(-100%);opacity:0;} 10%{opacity:1;} 90%{opacity:1;} 100%{transform:translateX(100%);opacity:0;} }
        .terminal-line { padding: 5px; margin: 5px 0; animation: typeIn 0.5s ease-out; }
        @keyframes typeIn { from{opacity:0;transform:translateX(-30px);} to{opacity:1;transform:translateX(0);} }
        .prompt { color: #00ff00; }
        .prompt::before { content: 'root@hacker:~# '; color: #00ff00; }
        .cursor { display: inline-block; width: 10px; height: 20px; background: #00ff00; animation: blink 1s infinite; vertical-align: middle; }
        @keyframes blink { 0%,49%{opacity:1;} 50%,100%{opacity:0;} }
        .status-grid {
            display: grid; grid-template-columns: repeat(3, 1fr);
            gap: 10px; margin: 20px 0;
        }
        .status-item {
            padding: 10px; background: rgba(0,255,0,0.05);
            border: 1px solid rgba(0,255,0,0.3); border-radius: 5px;
            font-size: 14px; transition: all 0.3s ease;
            text-align: center; cursor: pointer;
        }
        .status-item:hover { background: rgba(0,255,0,0.15); border-color: #00ff00; box-shadow: 0 0 20px rgba(0,255,0,0.3); transform: scale(1.05); }
        .status-item:active { transform: scale(0.92); box-shadow: 0 0 40px rgba(0,255,0,0.8); }
        .status-label { color: #666; font-size: 11px; text-transform: uppercase; }
        .status-value { color: #00ff00; font-weight: bold; font-size: 20px; }
        .stat-hits .status-value { color: #00ff00; }
        .stat-dead .status-value { color: #ff4444; }
        .stat-errors .status-value { color: #ff9800; }
        .audio-buttons {
            display: flex; gap: 10px; justify-content: center;
            margin: 15px 0; flex-wrap: wrap;
        }
        .audio-btn {
            padding: 8px 16px; background: rgba(0,255,0,0.1);
            border: 1px solid #00ff00; border-radius: 5px;
            color: #00ff00; cursor: pointer;
            font-family: 'Courier New', monospace; font-size: 12px;
            transition: all 0.3s ease; position: relative; overflow: hidden;
        }
        .audio-btn:hover { background: rgba(0,255,0,0.3); box-shadow: 0 0 20px rgba(0,255,0,0.5); transform: scale(1.05); }
        .audio-btn:active { transform: scale(0.88); box-shadow: 0 0 40px rgba(0,255,0,0.8); }
        .audio-btn.active { background: #00ff00; color: #000; box-shadow: 0 0 30px #00ff00; }
        @keyframes rippleAnim { to { transform: scale(4); opacity: 0; } }
        .hacker-log {
            margin-top: 20px; padding: 10px;
            background: rgba(0,0,0,0.5);
            border: 1px solid rgba(0,255,0,0.3); border-radius: 5px;
            max-height: 150px; overflow-y: auto; font-size: 12px;
        }
        .hacker-log::-webkit-scrollbar { width: 4px; }
        .hacker-log::-webkit-scrollbar-track { background: #000; }
        .hacker-log::-webkit-scrollbar-thumb { background: #00ff00; border-radius: 2px; }
        .admin-link {
            color: #00ff00; text-decoration: none; font-weight: bold;
            animation: linkGlow 2s infinite;
        }
        @keyframes linkGlow { 0%,100%{text-shadow:0 0 5px #00ff00;} 50%{text-shadow:0 0 20px #00ff00,0 0 30px #00ff00;} }
        .admin-link:hover { text-shadow: 0 0 10px #00ff00, 0 0 20px #00ff00, 0 0 30px #00ff00; }
        .laser-burst {
            position: fixed; pointer-events: none; z-index: 999;
            width: 15px; height: 15px; border-radius: 50%;
            background: #00ff00;
            box-shadow: 0 0 60px #00ff00, 0 0 120px #00ff00;
            animation: burstAnim 0.6s ease-out forwards;
        }
        @keyframes burstAnim { 0%{transform:scale(0);opacity:1;} 100%{transform:scale(12);opacity:0;} }
        .toast {
            position: fixed; bottom: 30px; left: 50%;
            transform: translateX(-50%) translateY(100px);
            background: rgba(0,0,0,0.9); color: #00ff00;
            padding: 15px 30px; border-radius: 10px;
            border: 1px solid #00ff00; box-shadow: 0 0 30px rgba(0,255,0,0.3);
            font-family: 'Courier New', monospace; font-size: 14px;
            opacity: 0; transition: all 0.5s ease; z-index: 999;
            pointer-events: none;
        }
        .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
        @media (max-width: 600px) {
            .container { margin: 15px; padding: 15px; }
            .title { font-size: 1.5em; }
            .status-grid { grid-template-columns: 1fr 1fr; }
            .audio-buttons { flex-direction: row; flex-wrap: wrap; }
        }
    </style>
</head>
<body>
    <canvas id="matrixCanvas"></canvas>
    <canvas id="laserCanvas"></canvas>
    <div class="container">
        <div class="terminal-header">
            <div class="terminal-buttons">
                <span class="terminal-btn btn-red" onclick="fireLaser(event, this)"></span>
                <span class="terminal-btn btn-yellow" onclick="fireLaser(event, this)"></span>
                <span class="terminal-btn btn-green" onclick="fireLaser(event, this)"></span>
            </div>
            <div class="terminal-title">LASER SECURITY - ENCRYPTED V3</div>
        </div>
        
        <div class="title" onclick="fireLaser(event, this)">GARENA CHECKER</div>
        
        <div class="laser-line"></div>
        
        <div class="terminal-line">
            <span class="prompt">Initializing laser security...</span>
            <span class="cursor"></span>
        </div>
        
        <div class="status-grid">
            <div class="status-item stat-hits" onclick="fireLaser(event, this)">
                <div class="status-label">HITS</div>
                <div class="status-value">""" + str(hits) + """</div>
            </div>
            <div class="status-item stat-dead" onclick="fireLaser(event, this)">
                <div class="status-label">DEAD</div>
                <div class="status-value">""" + str(dead) + """</div>
            </div>
            <div class="status-item stat-errors" onclick="fireLaser(event, this)">
                <div class="status-label">ERRORS</div>
                <div class="status-value">""" + str(errors) + """</div>
            </div>
            <div class="status-item" onclick="fireLaser(event, this)">
                <div class="status-label">STATUS</div>
                <div class="status-value" id="status">ALIVE</div>
            </div>
            <div class="status-item" onclick="fireLaser(event, this)">
                <div class="status-label">UPTIME</div>
                <div class="status-value" id="uptime" style="font-size:14px;">Calculating...</div>
            </div>
            <div class="status-item" onclick="fireLaser(event, this)">
                <div class="status-label">ADMIN</div>
                <div class="status-value" style="font-size:14px;"><a href="https://t.me/baohuyno1" class="admin-link" onclick="event.stopPropagation();">@baohuyno1</a></div>
            </div>
        </div>
        
        <div class="audio-buttons">
            <button class="audio-btn" onclick="playAudio('/audio', this)">🔊 HACKER</button>
            <button class="audio-btn" onclick="playAudio('/audio2', this)">🔊 CYBER</button>
            <button class="audio-btn" onclick="playAudio('/audio3', this)">🔊 TECHNO</button>
            <button class="audio-btn" onclick="playClick()">🔊 CLICK</button>
            <button class="audio-btn" onclick="playLaser()">🔊 LASER</button>
            <button class="audio-btn" onclick="playExplosion()">💥 EXPLOSION</button>
            <button class="audio-btn" onclick="stopAudio()">🔇 STOP</button>
        </div>
        
        <div class="hacker-log" id="hacker-log">
            <div style="color:#00ff00;">[SYSTEM] Laser security initialized...</div>
        </div>
    </div>
    
    <div class="toast" id="toast"></div>
    
    <audio id="bg-audio" loop><source src="/audio2" type="audio/wav"></audio>
    
    <script>
        // ========== TOAST ==========
        function showToast(msg, duration) {
            duration = duration || 1500;
            const toast = document.getElementById('toast');
            toast.textContent = msg;
            toast.classList.add('show');
            clearTimeout(toast._hide);
            toast._hide = setTimeout(function(){ toast.classList.remove('show'); }, duration);
        }
        
        // ========== MATRIX BACKGROUND ==========
        var matrixCanvas = document.getElementById('matrixCanvas');
        var matrixCtx = matrixCanvas.getContext('2d');
        matrixCanvas.width = window.innerWidth;
        matrixCanvas.height = window.innerHeight;
        var matrixChars = 'ABCDEF0123456789!@#$%^&*()_+{}[]|;:,.<>?~';
        var fontSize = 14;
        var columns = matrixCanvas.width / fontSize;
        var drops = [];
        for (var i = 0; i < columns; i++) { drops[i] = Math.random() * -100; }
        function drawMatrix() {
            matrixCtx.fillStyle = 'rgba(0, 0, 0, 0.05)';
            matrixCtx.fillRect(0, 0, matrixCanvas.width, matrixCanvas.height);
            matrixCtx.fillStyle = '#00ff00';
            matrixCtx.font = fontSize + 'px monospace';
            for (var i = 0; i < drops.length; i++) {
                var text = matrixChars[Math.floor(Math.random() * matrixChars.length)];
                matrixCtx.fillText(text, i * fontSize, drops[i] * fontSize);
                if (drops[i] * fontSize > matrixCanvas.height && Math.random() > 0.975) { drops[i] = 0; }
                drops[i]++;
            }
        }
        setInterval(drawMatrix, 50);
        
        // ========== LASER SYSTEM ==========
        var laserCanvas = document.getElementById('laserCanvas');
        var laserCtx = laserCanvas.getContext('2d');
        laserCanvas.width = window.innerWidth;
        laserCanvas.height = window.innerHeight;
        
        var lasers = [];
        var laserColors = ['#00ff00', '#00ffff', '#ff00ff', '#ffff00', '#ff0000', '#ffffff', '#ff8800', '#00ff88', '#ff0088', '#88ff00'];
        
        function LaserBeam(x, y, targetX, targetY, color) {
            this.x = x || Math.random() * laserCanvas.width;
            this.y = y || Math.random() * laserCanvas.height;
            this.targetX = targetX || Math.random() * laserCanvas.width;
            this.targetY = targetY || Math.random() * laserCanvas.height;
            this.color = color || laserColors[Math.floor(Math.random() * laserColors.length)];
            this.width = Math.random() * 4 + 1;
            this.life = 0;
            this.maxLife = Math.random() * 80 + 40;
            this.particles = [];
            this.alive = true;
        }
        
        LaserBeam.prototype.update = function() {
            this.life++;
            
            // Tao hat bui
            if (Math.random() > 0.3) {
                this.particles.push({
                    x: this.x + (this.targetX - this.x) * Math.random(),
                    y: this.y + (this.targetY - this.y) * Math.random(),
                    vx: (Math.random() - 0.5) * 4,
                    vy: (Math.random() - 0.5) * 4,
                    life: 0,
                    maxLife: Math.random() * 30 + 10
                });
            }
            
            // Cap nhat hat
            for (var i = this.particles.length - 1; i >= 0; i--) {
                var p = this.particles[i];
                p.x += p.vx;
                p.y += p.vy;
                p.life++;
                if (p.life > p.maxLife) {
                    this.particles.splice(i, 1);
                }
            }
            
            if (this.life > this.maxLife) {
                this.alive = false;
            }
        };
        
        LaserBeam.prototype.draw = function(ctx) {
            var progress = this.life / this.maxLife;
            var alpha = progress < 0.1 ? progress * 10 : progress > 0.9 ? (1 - progress) * 10 : 1;
            
            // Ve tia chinh
            var gradient = ctx.createLinearGradient(this.x, this.y, this.targetX, this.targetY);
            gradient.addColorStop(0, this.color + '00');
            gradient.addColorStop(0.3, this.color + 'FF');
            gradient.addColorStop(0.7, this.color + 'FF');
            gradient.addColorStop(1, this.color + '00');
            
            ctx.strokeStyle = gradient;
            ctx.lineWidth = this.width;
            ctx.globalAlpha = alpha;
            ctx.shadowColor = this.color;
            ctx.shadowBlur = 20;
            ctx.beginPath();
            ctx.moveTo(this.x, this.y);
            ctx.lineTo(this.targetX, this.targetY);
            ctx.stroke();
            ctx.shadowBlur = 0;
            
            // Ve tia phu (gay hieu ung chum)
            for (var j = 0; j < 3; j++) {
                var offsetX = (Math.random() - 0.5) * 10;
                var offsetY = (Math.random() - 0.5) * 10;
                ctx.strokeStyle = this.color;
                ctx.globalAlpha = alpha * 0.2;
                ctx.lineWidth = this.width * 0.3;
                ctx.beginPath();
                ctx.moveTo(this.x + offsetX, this.y + offsetY);
                ctx.lineTo(this.targetX + offsetX, this.targetY + offsetY);
                ctx.stroke();
            }
            
            // Ve hat bui
            for (var i = 0; i < this.particles.length; i++) {
                var p = this.particles[i];
                var pAlpha = 1 - (p.life / p.maxLife);
                ctx.fillStyle = this.color;
                ctx.globalAlpha = pAlpha * alpha;
                ctx.shadowColor = this.color;
                ctx.shadowBlur = 10;
                ctx.beginPath();
                ctx.arc(p.x, p.y, Math.random() * 3 + 1, 0, Math.PI * 2);
                ctx.fill();
                ctx.shadowBlur = 0;
            }
            
            ctx.globalAlpha = 1;
        };
        
        function createLaser(x, y, targetX, targetY, color) {
            if (lasers.length < 100) {
                var laser = new LaserBeam(x, y, targetX, targetY, color);
                lasers.push(laser);
                return laser;
            }
            return null;
        }
        
        function fireLaser(event, element) {
            // Ripple effect
            if (element) {
                var rect = element.getBoundingClientRect();
                var ripple = document.createElement('span');
                var size = Math.max(rect.width, rect.height);
                var cx = (event ? event.clientX - rect.left : rect.width/2) - size/2;
                var cy = (event ? event.clientY - rect.top : rect.height/2) - size/2;
                ripple.style.cssText = 'width:'+size+'px;height:'+size+'px;left:'+cx+'px;top:'+cy+'px;position:absolute;border-radius:50%;background:rgba(255,255,255,0.3);transform:scale(0);animation:rippleAnim 0.6s linear;pointer-events:none;';
                element.style.position = 'relative';
                element.style.overflow = 'hidden';
                element.appendChild(ripple);
                setTimeout(function(){ ripple.remove(); }, 600);
            }
            
            // Laser burst
            if (event) {
                var burst = document.createElement('div');
                burst.className = 'laser-burst';
                burst.style.left = (event.clientX - 7) + 'px';
                burst.style.top = (event.clientY - 7) + 'px';
                var color = laserColors[Math.floor(Math.random() * laserColors.length)];
                burst.style.background = color;
                burst.style.boxShadow = '0 0 60px ' + color + ', 0 0 120px ' + color;
                document.body.appendChild(burst);
                setTimeout(function(){ burst.remove(); }, 600);
            }
            
            // Tao nhieu tia tu vi tri click
            if (event) {
                var numLasers = Math.floor(Math.random() * 8) + 5;
                for (var i = 0; i < numLasers; i++) {
                    var angle = Math.random() * Math.PI * 2;
                    var distance = Math.random() * 500 + 200;
                    var tx = event.clientX + Math.cos(angle) * distance;
                    var ty = event.clientY + Math.sin(angle) * distance;
                    var color = laserColors[Math.floor(Math.random() * laserColors.length)];
                    createLaser(event.clientX, event.clientY, tx, ty, color);
                }
                
                // Tia dac biet
                for (var i = 0; i < 3; i++) {
                    var angle = Math.random() * Math.PI * 2;
                    var tx = event.clientX + Math.cos(angle) * 800;
                    var ty = event.clientY + Math.sin(angle) * 800;
                    createLaser(event.clientX, event.clientY, tx, ty, '#ffffff');
                }
            }
            
            // Play sound
            playLaser();
            showToast('⚡ LASER ACTIVATED!', 800);
        }
        
        // Click bat ky dau de tao tia laser
        document.addEventListener('click', function(e) {
            var numLasers = Math.floor(Math.random() * 5) + 3;
            for (var i = 0; i < numLasers; i++) {
                var angle = Math.random() * Math.PI * 2;
                var distance = Math.random() * 400 + 100;
                var tx = e.clientX + Math.cos(angle) * distance;
                var ty = e.clientY + Math.sin(angle) * distance;
                var color = laserColors[Math.floor(Math.random() * laserColors.length)];
                createLaser(e.clientX, e.clientY, tx, ty, color);
            }
        });
        
        // ========== DRAW LOOP ==========
        function drawLasers() {
            laserCtx.clearRect(0, 0, laserCanvas.width, laserCanvas.height);
            
            for (var i = lasers.length - 1; i >= 0; i--) {
                var laser = lasers[i];
                laser.update();
                if (laser.alive) {
                    laser.draw(laserCtx);
                } else {
                    lasers.splice(i, 1);
                }
            }
            
            // Flash ngau nhien
            if (Math.random() > 0.97) {
                var flashX = Math.random() * laserCanvas.width;
                var flashY = Math.random() * laserCanvas.height;
                var flashRadius = Math.random() * 50 + 30;
                var flashColor = laserColors[Math.floor(Math.random() * laserColors.length)];
                var gradient = laserCtx.createRadialGradient(flashX, flashY, 0, flashX, flashY, flashRadius);
                gradient.addColorStop(0, flashColor + 'FF');
                gradient.addColorStop(1, flashColor + '00');
                laserCtx.fillStyle = gradient;
                laserCtx.beginPath();
                laserCtx.arc(flashX, flashY, flashRadius, 0, Math.PI * 2);
                laserCtx.fill();
            }
            
            requestAnimationFrame(drawLasers);
        }
        
        // Tao tia ban dau
        for (var i = 0; i < 20; i++) {
            createLaser();
        }
        
        drawLasers();
        
        // ========== MOUSE LASER ==========
        document.addEventListener('mousemove', function(e) {
            if (Math.random() > 0.8) {
                var angle = Math.random() * Math.PI * 2;
                var distance = Math.random() * 300 + 50;
                var tx = e.clientX + Math.cos(angle) * distance;
                var ty = e.clientY + Math.sin(angle) * distance;
                createLaser(e.clientX, e.clientY, tx, ty);
                if (lasers.length > 100) { lasers.shift(); }
            }
        });
        
        // ========== AUDIO SYSTEM ==========
        var bgAudio = document.getElementById('bg-audio');
        var currentAudio = null;
        
        function playAudio(url, button) {
            if (currentAudio) { currentAudio.pause(); currentAudio = null; }
            currentAudio = new Audio(url);
            currentAudio.loop = true;
            currentAudio.volume = 0.4;
            currentAudio.play().catch(function(e){});
            document.querySelectorAll('.audio-btn').forEach(function(btn){ btn.classList.remove('active'); });
            if (button) { button.classList.add('active'); showToast('🔊 ' + button.textContent.trim(), 1200); }
        }
        
        function playClick() {
            var audio = new Audio('/audio-click');
            audio.volume = 0.5;
            audio.play().catch(function(e){});
        }
        
        function playLaser() {
            var audio = new Audio('/audio-laser');
            audio.volume = 0.6;
            audio.play().catch(function(e){});
        }
        
        function playExplosion() {
            var audio = new Audio('/audio-explosion');
            audio.volume = 0.5;
            audio.play().catch(function(e){});
            showToast('💥 BOOM!', 500);
        }
        
        function stopAudio() {
            if (currentAudio) { currentAudio.pause(); currentAudio = null; }
            document.querySelectorAll('.audio-btn').forEach(function(btn){ btn.classList.remove('active'); });
            showToast('🔇 Da tat am thanh', 1000);
        }
        
        // ========== UPTIME ==========
        var startTime = new Date();
        setInterval(function() {
            var now = new Date();
            var diff = Math.floor((now - startTime) / 1000);
            var days = Math.floor(diff / 86400);
            var hours = Math.floor((diff % 86400) / 3600);
            var minutes = Math.floor((diff % 3600) / 60);
            var seconds = diff % 60;
            var str = '';
            if (days > 0) str += days + 'd ';
            str += hours + 'h ' + minutes + 'm ' + seconds + 's';
            document.getElementById('uptime').textContent = str;
        }, 1000);
        
        // ========== LOG ==========
        var msgs = [
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
            'SYSTEM ONLINE...',
            'HACKER DETECTED!',
            'LAUNCHING COUNTERMEASURE...',
            'LASER GRID ACTIVE...'
        ];
        var codes = ['0x7F3A9C','0xDEADBEEF','0xC0FFEE','0xBADC0DE','0xFEEDFACE','0xCAFEBABE','0xDEADCODE','0xFACEFEED','0xB105F00D','0xD15EA5E','0xBAADF00D','0xDEADC0DE'];
        var logEl = document.getElementById('hacker-log');
        var idx = 0;
        setInterval(function() {
            var msg = msgs[idx % msgs.length];
            var code = codes[Math.floor(Math.random() * codes.length)];
            var ts = new Date().toLocaleTimeString();
            var div = document.createElement('div');
            div.textContent = '[' + ts + '] ' + msg + ' ' + code;
            div.style.color = laserColors[Math.floor(Math.random() * laserColors.length)];
            div.style.opacity = '0.8';
            logEl.appendChild(div);
            logEl.scrollTop = logEl.scrollHeight;
            idx++;
            if (logEl.children.length > 25) { logEl.removeChild(logEl.firstChild); }
        }, 2000);
        
        // ========== PING ==========
        setInterval(function() {
            fetch('/ping').then(function(r){ return r.text(); }).then(function(d){
                document.getElementById('status').textContent = 'ALIVE';
                document.getElementById('status').style.color = '#00ff00';
            }).catch(function(){
                document.getElementById('status').textContent = 'OFFLINE';
                document.getElementById('status').style.color = '#ff0000';
            });
        }, 5000);
        
        // ========== STATS UPDATE ==========
        setInterval(function() {
            fetch('/status').then(function(r){ return r.json(); }).then(function(d){
                document.querySelector('.stat-hits .status-value').textContent = d.hits || 0;
                document.querySelector('.stat-dead .status-value').textContent = d.dead || 0;
                document.querySelector('.stat-errors .status-value').textContent = d.errors || 0;
            }).catch(function(e){});
        }, 10000);
        
        // ========== RESIZE ==========
        window.addEventListener('resize', function() {
            matrixCanvas.width = window.innerWidth;
            matrixCanvas.height = window.innerHeight;
            laserCanvas.width = window.innerWidth;
            laserCanvas.height = window.innerHeight;
        });
        
        // ========== AUTO PLAY ==========
        document.addEventListener('click', function first() {
            bgAudio.volume = 0.2;
            bgAudio.play().catch(function(e){});
            document.removeEventListener('click', first);
        }, { once: true });
        
        console.log('🔥 LASER SECURITY ACTIVE!');
        console.log('💀 Click anything for laser effect!');
    </script>
</body>
</html>"""
    
    def generate_full_laser_page(self):
        """Tao trang laser fullscreen"""
        return """<!DOCTYPE html>
<html>
<head><title>LASER MODE</title><meta charset="UTF-8">
<style>*{margin:0;padding:0;}body{background:#000;overflow:hidden;cursor:crosshair;}canvas{display:block;}</style>
</head>
<body>
<canvas id="laserCanvas"></canvas>
<script>
var canvas = document.getElementById('laserCanvas');
var ctx = canvas.getContext('2d');
canvas.width = window.innerWidth;
canvas.height = window.innerHeight;
var lasers = [];
var colors = ['#00ff00','#00ffff','#ff00ff','#ffff00','#ff0000','#ffffff','#ff8800','#00ff88','#ff0088','#88ff00'];
function Laser(x,y,tx,ty,c){
    this.x=x||Math.random()*canvas.width;
    this.y=y||Math.random()*canvas.height;
    this.tx=tx||Math.random()*canvas.width;
    this.ty=ty||Math.random()*canvas.height;
    this.c=c||colors[Math.floor(Math.random()*colors.length)];
    this.w=Math.random()*3+1;
    this.life=0;
    this.max=Math.random()*100+50;
    this.p=[];
}
Laser.prototype.update=function(){
    this.life++;
    if(Math.random()>0.3){
        this.p.push({
            x:this.x+(this.tx-this.x)*Math.random(),
            y:this.y+(this.ty-this.y)*Math.random(),
            vx:(Math.random()-0.5)*3,
            vy:(Math.random()-0.5)*3,
            life:0,
            max:Math.random()*30+10
        });
    }
    for(var i=this.p.length-1;i>=0;i--){
        var p=this.p[i];
        p.x+=p.vx;p.y+=p.vy;p.life++;
        if(p.life>p.max){this.p.splice(i,1);}
    }
    if(this.life>this.max){
        var idx=lasers.indexOf(this);
        if(idx>-1){lasers.splice(idx,1);}
    }
};
Laser.prototype.draw=function(){
    var progress=this.life/this.max;
    var alpha=progress<0.1?progress*10:progress>0.9?(1-progress)*10:1;
    var grad=ctx.createLinearGradient(this.x,this.y,this.tx,this.ty);
    grad.addColorStop(0,this.c+'00');
    grad.addColorStop(0.5,this.c+'FF');
    grad.addColorStop(1,this.c+'00');
    ctx.strokeStyle=grad;
    ctx.lineWidth=this.w;
    ctx.globalAlpha=alpha;
    ctx.shadowColor=this.c;
    ctx.shadowBlur=15;
    ctx.beginPath();ctx.moveTo(this.x,this.y);ctx.lineTo(this.tx,this.ty);ctx.stroke();
    ctx.shadowBlur=0;
    for(var i=0;i<this.p.length;i++){
        var p=this.p[i];
        var pa=1-(p.life/p.max);
        ctx.fillStyle=this.c;
        ctx.globalAlpha=pa*alpha;
        ctx.shadowColor=this.c;
        ctx.shadowBlur=8;
        ctx.beginPath();ctx.arc(p.x,p.y,Math.random()*2+1,0,Math.PI*2);ctx.fill();
        ctx.shadowBlur=0;
    }
    ctx.globalAlpha=1;
};
function createLaser(x,y){if(lasers.length<100){lasers.push(new Laser(x,y));}}
function draw(){
    ctx.fillStyle='rgba(0,0,0,0.05)';
    ctx.fillRect(0,0,canvas.width,canvas.height);
    for(var i=0;i<lasers.length;i++){lasers[i].update();lasers[i].draw();}
    if(Math.random()>0.95){createLaser();}
    requestAnimationFrame(draw);
}
for(var i=0;i<30;i++){createLaser();}
draw();
document.addEventListener('mousemove',function(e){
    if(Math.random()>0.4){
        var l=new Laser(e.clientX,e.clientY);
        lasers.push(l);
        if(lasers.length>100){lasers.shift();}
    }
});
document.addEventListener('click',function(e){
    for(var i=0;i<20;i++){
        var l=new Laser(e.clientX,e.clientY);
        lasers.push(l);
    }
    if(lasers.length>100){lasers.splice(0,20);}
});
window.addEventListener('resize',function(){
    canvas.width=window.innerWidth;
    canvas.height=window.innerHeight;
});
</script>
</body>
</html>"""
    
    def generate_matrix_page(self):
        """Tao trang matrix fullscreen"""
        return """<!DOCTYPE html>
<html>
<head><title>MATRIX MODE</title><meta charset="UTF-8">
<style>*{margin:0;padding:0;}body{background:#000;overflow:hidden;}canvas{display:block;}</style>
</head>
<body>
<canvas id="matrix"></canvas>
<script>
var canvas=document.getElementById('matrix');
var ctx=canvas.getContext('2d');
canvas.width=window.innerWidth;
canvas.height=window.innerHeight;
var chars='アイウエオカキクケコサシスセソタチツテトナニヌネノハヒフヘホマミムメモヤユヨラリルレロワヲン0123456789ABCDEF';
var fontSize=16;
var columns=canvas.width/fontSize;
var drops=[];
for(var i=0;i<columns;i++){drops[i]=Math.random()*-100;}
function draw(){
    ctx.fillStyle='rgba(0,0,0,0.05)';
    ctx.fillRect(0,0,canvas.width,canvas.height);
    for(var i=0;i<drops.length;i++){
        var text=chars[Math.floor(Math.random()*chars.length)];
        ctx.fillStyle=Math.random()>0.95?'#ffffff':'#00ff00';
        ctx.font=fontSize+'px monospace';
        ctx.fillText(text,i*fontSize,drops[i]*fontSize);
        if(drops[i]*fontSize>canvas.height&&Math.random()>0.975){drops[i]=0;}
        drops[i]++;
    }
}
setInterval(draw,33);
window.addEventListener('resize',function(){
    canvas.width=window.innerWidth;
    canvas.height=window.innerHeight;
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
<head><title>STATS - GARENA CHECKER</title><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<style>*{margin:0;padding:0;box-sizing:border-box;}body{font-family:'Courier New',monospace;background:#0a0a0a;color:#00ff00;padding:20px;min-height:100vh;}
.container{max-width:800px;margin:0 auto;}.title{text-align:center;font-size:2em;margin-bottom:30px;text-shadow:0 0 20px #00ff00;animation:pulse 2s infinite;cursor:pointer;}
.title:hover{text-shadow:0 0 40px #00ff00,0 0 80px #00ff00;}
@keyframes pulse{0%,100%{opacity:1;}50%{opacity:0.7;}}
.stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:20px;margin-bottom:30px;}
.stat-card{background:#111;border:1px solid #00ff00;border-radius:10px;padding:20px;text-align:center;box-shadow:0 0 20px rgba(0,255,0,0.2);transition:all 0.3s ease;cursor:pointer;}
.stat-card:hover{transform:scale(1.05);box-shadow:0 0 40px rgba(0,255,0,0.5);}
.stat-card:active{transform:scale(0.92);}
.stat-value{font-size:2.5em;font-weight:bold;}
.stat-label{font-size:0.8em;color:#666;margin-top:5px;}
.hits .stat-value{color:#00ff00;}
.dead .stat-value{color:#ff4444;}
.errors .stat-value{color:#ff9800;}
.total .stat-value{color:#00ffff;}
.back-link{display:block;text-align:center;color:#00ff00;text-decoration:none;margin-top:30px;padding:10px;border:1px solid #00ff00;border-radius:5px;transition:all 0.3s ease;}
.back-link:hover{background:#00ff00;color:#000;box-shadow:0 0 30px #00ff00;}
</style>
</head>
<body>
<div class="container">
<div class="title" onclick="this.style.transform='scale(0.95)';setTimeout(()=>this.style.transform='scale(1)',200)">📊 STATISTICS</div>
<div class="stats-grid">
<div class="stat-card hits" onclick="showToast('✅ Hits: """ + str(hits) + """')">
<div class="stat-value">""" + str(hits) + """</div><div class="stat-label">✅ HITS</div></div>
<div class="stat-card dead" onclick="showToast('❌ Dead: """ + str(dead) + """')">
<div class="stat-value">""" + str(dead) + """</div><div class="stat-label">❌ DEAD</div></div>
<div class="stat-card errors" onclick="showToast('⚠️ Errors: """ + str(errors) + """')">
<div class="stat-value">""" + str(errors) + """</div><div class="stat-label">⚠️ ERRORS</div></div>
<div class="stat-card total" onclick="showToast('📊 Total: """ + str(total) + """')">
<div class="stat-value">""" + str(total) + """</div><div class="stat-label">📊 TOTAL</div></div>
</div>
<a href="/" class="back-link">⬅ BACK TO DASHBOARD</a>
</div>
<script>
function showToast(msg){
var toast=document.createElement('div');
toast.style.cssText='position:fixed;bottom:30px;left:50%;transform:translateX(-50%);background:rgba(0,0,0,0.9);color:#00ff00;padding:15px 30px;border-radius:10px;border:1px solid #00ff00;box-shadow:0 0 30px rgba(0,255,0,0.3);font-family:Courier New,monospace;font-size:14px;z-index:999;transition:all 0.5s ease;opacity:0;';
toast.textContent=msg;
document.body.appendChild(toast);
setTimeout(function(){toast.style.opacity='1';},50);
setTimeout(function(){toast.style.opacity='0';setTimeout(function(){toast.remove();},500);},1500);
}
</script>
</body>
</html>"""
    
    def log_message(self, format, *args):
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
        print(f"[*] Click bat ky dau de thay tia laser")
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
    print("[*] Truy cap web de xem hieu ung laser hacker")
    print("[*] Click bat ky dau de thay tia laser mau sac")
    print("=" * 60)
    
    # Chay bot chinh
    run_bot()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[!] Da dung!")
        sys.exit(0)
