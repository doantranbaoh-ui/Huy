#!/usr/bin/env python3
import json, os, time, uuid, hashlib, logging, re, secrets
from datetime import datetime, timedelta
import telebot
from telebot import types
from flask import Flask, request, jsonify

# ========== CONFIG ==========
BOT_TOKEN = "6320148381:AAHKLMaGycWIv8sxdBU6sAmgOPn2XlqTIx0"
CHAT_ID = "-1003925717296"
ADMIN_IDS = [5736655322]
DB_FILE = "keys.json"
BAN_FILE = "bans.json"
CONFIG_FILE = "config.json"
LOG_FILE = "bot.log"

# ========== FLASK APP ==========
app = Flask(__name__)

@app.route('/')
def home():
    return "🤖 Bot UnbndSDK Online - Admin: 5736655322", 200

@app.route('/health')
def health():
    return {
        "status": "ok",
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "server_time": datetime.now().isoformat()
    }, 200

@app.route('/stats')
def stats():
    return {
        "total_keys": len(db.get("keys", {})),
        "approved": len(db.get("approved", {})),
        "kicked": len(db.get("kicked", {})),
        "maintenance": config.get("maintenance", False),
        "server_time": datetime.now().isoformat()
    }, 200

# ========== API ENDPOINTS ==========
@app.route('/api/genuid', methods=['GET'])
def api_genuid():
    """Generate random UID for client"""
    new_uid = secrets.token_hex(16)
    return jsonify({
        "status": "success",
        "uid": new_uid,
        "length": len(new_uid),
        "server_time": datetime.now().isoformat(),
        "timestamp": int(time.time())
    }), 200

@app.route('/api/check', methods=['POST'])
def api_check():
    data = request.get_json() or {}
    uid = str(data.get('uid', ''))
    key = data.get('key', '')
    device = data.get('device', 'Unknown')
    ip = request.remote_addr
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if not uid or not key:
        return jsonify({
            "status": "error",
            "message": "Missing uid or key",
            "code": 1001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    # Check banned
    if is_banned(uid, ip, device):
        return jsonify({
            "status": "banned",
            "message": "UID/IP/Device banned",
            "code": 1002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check key exists
    if "keys" not in db or key not in db["keys"]:
        return jsonify({
            "status": "invalid",
            "message": "Key not found",
            "code": 1003,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    k = db["keys"][key]
    
    # Check key used on other device
    if k.get("used", False) and k.get("udid") and k.get("udid") != uid:
        return jsonify({
            "status": "used_other",
            "message": "Key used on another device",
            "code": 1004,
            "registered_device": k.get("device", "Unknown"),
            "registered_at": k.get("activated_at", "Unknown"),
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check max activations
    if k.get("activations", 0) >= k.get("max_activations", 1):
        return jsonify({
            "status": "limit",
            "message": "Max activations reached",
            "code": 1005,
            "activations": k.get("activations", 0),
            "max": k.get("max_activations", 1),
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check expiry
    try:
        exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
        if now > exp:
            # Tính số ngày đã hết hạn
            days_expired = (now - exp).days
            return jsonify({
                "status": "expired",
                "message": "Key expired",
                "code": 1006,
                "expired_at": k["expires"],
                "expired_date": exp.strftime("%d/%m/%Y"),
                "expired_time": exp.strftime("%H:%M:%S"),
                "days_expired": days_expired,
                "server_time": now_str,
                "timestamp": int(time.time())
            }), 200
        else:
            # Tính số ngày còn lại
            days_remaining = (exp - now).days
            hours_remaining = (exp - now).seconds // 3600
            minutes_remaining = ((exp - now).seconds % 3600) // 60
            return jsonify({
                "status": "valid",
                "message": "Key valid",
                "code": 0,
                "type": k.get("type", "unknown"),
                "prefix": k.get("prefix", "unknown"),
                "created": k.get("created"),
                "expires": k.get("expires"),
                "expiry_date": exp.strftime("%d/%m/%Y"),
                "expiry_time": exp.strftime("%H:%M:%S"),
                "days_remaining": days_remaining,
                "hours_remaining": hours_remaining,
                "minutes_remaining": minutes_remaining,
                "total_hours_remaining": int((exp - now).total_seconds() // 3600),
                "activations": k.get("activations", 0),
                "max": k.get("max_activations", 1),
                "used": k.get("used", False),
                "device": k.get("device"),
                "first_activation": k.get("activated_at"),
                "last_check": now_str,
                "server_time": now_str,
                "timestamp": int(time.time())
            }), 200
    except Exception as e:
        return jsonify({
            "status": "valid",
            "message": "Key valid (expiry parse error)",
            "code": 0,
            "type": k.get("type", "unknown"),
            "expires": k.get("expires"),
            "activations": k.get("activations", 0),
            "max": k.get("max_activations", 1),
            "used": k.get("used", False),
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check maintenance
    if config.get("maintenance", False):
        return jsonify({
            "status": "maintenance",
            "message": "Server maintenance",
            "code": 1007,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200

@app.route('/api/activate', methods=['POST'])
def api_activate():
    data = request.get_json() or {}
    uid = str(data.get('uid', ''))
    key = data.get('key', '')
    device = data.get('device', 'Unknown')
    ip = request.remote_addr
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if not uid or not key:
        return jsonify({
            "status": "error",
            "message": "Missing uid or key",
            "code": 2001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    # Check banned
    if is_banned(uid, ip, device):
        return jsonify({
            "status": "banned",
            "message": "UID/IP/Device banned",
            "code": 2002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check key exists
    if "keys" not in db or key not in db["keys"]:
        return jsonify({
            "status": "invalid",
            "message": "Key not found",
            "code": 2003,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    k = db["keys"][key]
    
    # Check key used on other device
    if k.get("used", False) and k.get("udid") and k.get("udid") != uid:
        return jsonify({
            "status": "used_other",
            "message": "Key used on another device",
            "code": 2004,
            "registered_device": k.get("device", "Unknown"),
            "registered_at": k.get("activated_at", "Unknown"),
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check max activations
    if k.get("activations", 0) >= k.get("max_activations", 1):
        return jsonify({
            "status": "limit",
            "message": "Max activations reached",
            "code": 2005,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check expiry
    try:
        exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
        if now > exp:
            days_expired = (now - exp).days
            return jsonify({
                "status": "expired",
                "message": "Key expired",
                "code": 2006,
                "expired_at": k["expires"],
                "expired_date": exp.strftime("%d/%m/%Y"),
                "expired_time": exp.strftime("%H:%M:%S"),
                "days_expired": days_expired,
                "server_time": now_str,
                "timestamp": int(time.time())
            }), 200
    except:
        pass
    
    # Check maintenance
    if config.get("maintenance", False):
        return jsonify({
            "status": "maintenance",
            "message": "Server maintenance",
            "code": 2007,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Already activated by this UID
    if k.get("used", False) and k.get("udid") == uid:
        return jsonify({
            "status": "already_active",
            "message": "Key already activated on this device",
            "code": 2008,
            "expires": k.get("expires"),
            "activated_at": k.get("activated_at"),
            "activation_date": datetime.strptime(k.get("activated_at", now_str), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y") if k.get("activated_at") else None,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Activate key
    k["used"] = True
    k["udid"] = uid
    k["device"] = device
    k["ip"] = ip
    k["activations"] = k.get("activations", 0) + 1
    k["activated_at"] = now_str
    
    if "approved" not in db:
        db["approved"] = {}
    if "stats" not in db:
        db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
    
    db["approved"][uid] = {
        "approved_by": "api",
        "time": now_str,
        "key": key,
        "device": device,
        "ip": ip
    }
    db["stats"]["total_approved"] = db["stats"].get("total_approved", 0) + 1
    
    log(f"API ACTIVATE: {key} by {uid} | Device: {device} | IP: {ip} | Time: {now_str}")
    save_db()
    
    try:
        exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
        days_remaining = (exp - now).days
    except:
        days_remaining = None
    
    return jsonify({
        "status": "success",
        "message": "Key activated",
        "code": 0,
        "expires": k.get("expires"),
        "expiry_date": exp.strftime("%d/%m/%Y") if 'exp' in locals() else None,
        "expiry_time": exp.strftime("%H:%M:%S") if 'exp' in locals() else None,
        "days_remaining": days_remaining,
        "activations": k.get("activations", 0),
        "max": k.get("max_activations", 1),
        "activated_at": k.get("activated_at"),
        "activation_date": now.strftime("%d/%m/%Y"),
        "activation_time": now.strftime("%H:%M:%S"),
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/verify', methods=['POST'])
def api_verify():
    data = request.get_json() or {}
    uid = str(data.get('uid', ''))
    key = data.get('key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if not uid:
        return jsonify({
            "status": "error",
            "message": "Missing uid",
            "code": 3001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    # Check banned
    if is_banned(uid):
        return jsonify({
            "status": "banned",
            "message": "UID banned",
            "code": 3002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    # Check approved
    if "approved" not in db or uid not in db["approved"]:
        return jsonify({
            "status": "unapproved",
            "message": "UID not approved",
            "code": 3003,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    info = db["approved"][uid]
    
    # Check key if provided
    if key and "keys" in db and key in db["keys"]:
        k = db["keys"][key]
        try:
            exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
            if now > exp:
                days_expired = (now - exp).days
                return jsonify({
                    "status": "expired",
                    "message": "Key expired",
                    "code": 3004,
                    "expired_at": k["expires"],
                    "expired_date": exp.strftime("%d/%m/%Y"),
                    "expired_time": exp.strftime("%H:%M:%S"),
                    "days_expired": days_expired,
                    "server_time": now_str,
                    "timestamp": int(time.time())
                }), 200
            else:
                days_remaining = (exp - now).days
        except:
            days_remaining = None
    else:
        days_remaining = None
    
    return jsonify({
        "status": "approved",
        "message": "UID approved",
        "code": 0,
        "time": info.get("time"),
        "approved_date": datetime.strptime(info.get("time", now_str), "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y") if info.get("time") else None,
        "approved_time": datetime.strptime(info.get("time", now_str), "%Y-%m-%d %H:%M:%S").strftime("%H:%M:%S") if info.get("time") else None,
        "by": info.get("approved_by"),
        "key": info.get("key"),
        "device": info.get("device"),
        "days_remaining": days_remaining,
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/heartbeat', methods=['POST'])
def api_heartbeat():
    data = request.get_json() or {}
    uid = str(data.get('uid', ''))
    key = data.get('key', '')
    device = data.get('device', 'Unknown')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if not uid or not key:
        return jsonify({
            "status": "error",
            "message": "Missing uid or key",
            "code": 6001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "keys" not in db or key not in db["keys"]:
        return jsonify({
            "status": "invalid",
            "message": "Key not found",
            "code": 6002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    k = db["keys"][key]
    
    if k.get("udid") != uid:
        return jsonify({
            "status": "mismatch",
            "message": "UID does not match key owner",
            "code": 6003,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    try:
        exp = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
        if now > exp:
            days_expired = (now - exp).days
            return jsonify({
                "status": "expired",
                "message": "Key expired",
                "code": 6004,
                "expired_at": k["expires"],
                "expired_date": exp.strftime("%d/%m/%Y"),
                "expired_time": exp.strftime("%H:%M:%S"),
                "days_expired": days_expired,
                "server_time": now_str,
                "timestamp": int(time.time())
            }), 200
        else:
            days_remaining = (exp - now).days
            hours_remaining = (exp - now).seconds // 3600
            minutes_remaining = ((exp - now).seconds % 3600) // 60
            time_remaining = str(exp - now)
    except:
        days_remaining = None
        hours_remaining = None
        minutes_remaining = None
        time_remaining = "Unknown"
    
    # Update last seen
    k["last_seen"] = now_str
    k["last_device"] = device
    k["last_check"] = now_str
    save_db()
    
    return jsonify({
        "status": "alive",
        "message": "Heartbeat received",
        "code": 0,
        "expires": k.get("expires"),
        "expiry_date": exp.strftime("%d/%m/%Y") if 'exp' in locals() and 'exp' in vars() else None,
        "expiry_time": exp.strftime("%H:%M:%S") if 'exp' in locals() and 'exp' in vars() else None,
        "days_remaining": days_remaining,
        "hours_remaining": hours_remaining,
        "minutes_remaining": minutes_remaining,
        "time_remaining": time_remaining,
        "last_seen": now_str,
        "last_seen_date": now.strftime("%d/%m/%Y"),
        "last_seen_time": now.strftime("%H:%M:%S"),
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/kick', methods=['POST'])
def api_kick():
    data = request.get_json() or {}
    uid = str(data.get('uid', ''))
    admin_key = data.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    if not uid:
        return jsonify({
            "status": "error",
            "message": "Missing uid",
            "code": 9002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "kicked" not in db:
        db["kicked"] = {}
    if "stats" not in db:
        db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
    
    db["kicked"][uid] = {
        "time": now_str,
        "by": "api",
        "reason": "API kick"
    }
    if "approved" in db:
        db["approved"].pop(uid, None)
    db["stats"]["total_kicked"] = db["stats"].get("total_kicked", 0) + 1
    
    log(f"API KICK: {uid} | Time: {now_str}")
    save_db()
    
    return jsonify({
        "status": "success",
        "message": f"UID {uid} kicked",
        "code": 0,
        "kicked_at": now_str,
        "kicked_date": now.strftime("%d/%m/%Y"),
        "kicked_time": now.strftime("%H:%M:%S"),
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/ban', methods=['POST'])
def api_ban():
    data = request.get_json() or {}
    target = data.get('target', '')
    reason = data.get('reason', 'API ban')
    admin_key = data.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    if not target:
        return jsonify({
            "status": "error",
            "message": "Missing target",
            "code": 9002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "banned_uids" not in bans:
        bans["banned_uids"] = []
    
    bans["banned_uids"].append({
        "uid": target,
        "reason": reason,
        "time": now_str,
        "banned_date": now.strftime("%d/%m/%Y"),
        "banned_time": now.strftime("%H:%M:%S")
    })
    save_bans()
    log(f"API BAN: {target} | Reason: {reason} | Time: {now_str}")
    
    return jsonify({
        "status": "success",
        "message": f"Target {target} banned",
        "code": 0,
        "banned_at": now_str,
        "banned_date": now.strftime("%d/%m/%Y"),
        "banned_time": now.strftime("%H:%M:%S"),
        "reason": reason,
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/unban', methods=['POST'])
def api_unban():
    data = request.get_json() or {}
    target = data.get('target', '')
    admin_key = data.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    if not target:
        return jsonify({
            "status": "error",
            "message": "Missing target",
            "code": 9002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "banned_uids" not in bans:
        bans["banned_uids"] = []
    bans["banned_uids"] = [x for x in bans["banned_uids"] if (x.get("uid") if isinstance(x, dict) else x) != target]
    save_bans()
    log(f"API UNBAN: {target} | Time: {now_str}")
    
    return jsonify({
        "status": "success",
        "message": f"Target {target} unbanned",
        "code": 0,
        "unbanned_at": now_str,
        "unbanned_date": now.strftime("%d/%m/%Y"),
        "unbanned_time": now.strftime("%H:%M:%S"),
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

@app.route('/api/list', methods=['GET'])
def api_list():
    admin_key = request.args.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    # Enrich keys with time info
    keys_info = []
    for k, v in list(db.get("keys", {}).items())[-50:]:
        key_info = {
            "key": k[:20] + "...",
            "type": v.get("type"),
            "used": v.get("used", False),
            "expires": v.get("expires"),
            "activations": v.get("activations", 0),
            "max": v.get("max_activations", 1)
        }
        if v.get("expires"):
            try:
                exp = datetime.strptime(v["expires"], "%Y-%m-%d %H:%M:%S")
                if now > exp:
                    key_info["status"] = "expired"
                    key_info["days_expired"] = (now - exp).days
                else:
                    key_info["status"] = "active"
                    key_info["days_remaining"] = (exp - now).days
            except:
                key_info["status"] = "unknown"
        keys_info.append(key_info)
    
    return jsonify({
        "status": "success",
        "code": 0,
        "server_time": now_str,
        "timestamp": int(time.time()),
        "keys_count": len(db.get("keys", {})),
        "approved_count": len(db.get("approved", {})),
        "kicked_count": len(db.get("kicked", {})),
        "keys": keys_info,
        "approved": list(db.get("approved", {}).keys())[-50:],
        "kicked": list(db.get("kicked", {}).keys())[-50:],
        "banned": bans.get("banned_uids", [])
    }), 200

@app.route('/api/keyinfo', methods=['POST'])
def api_keyinfo():
    data = request.get_json() or {}
    key = data.get('key', '')
    admin_key = data.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    if not key:
        return jsonify({
            "status": "error",
            "message": "Missing key",
            "code": 4001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "keys" not in db or key not in db["keys"]:
        return jsonify({
            "status": "not_found",
            "message": "Key not found",
            "code": 4002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    k = db["keys"][key]
    
    # Calculate time info
    time_info = {}
    if k.get("created"):
        time_info["created"] = k["created"]
        try:
            created_dt = datetime.strptime(k["created"], "%Y-%m-%d %H:%M:%S")
            time_info["created_date"] = created_dt.strftime("%d/%m/%Y")
            time_info["created_time"] = created_dt.strftime("%H:%M:%S")
            time_info["age_days"] = (now - created_dt).days
        except:
            pass
    
    if k.get("expires"):
        time_info["expires"] = k["expires"]
        try:
            exp_dt = datetime.strptime(k["expires"], "%Y-%m-%d %H:%M:%S")
            time_info["expiry_date"] = exp_dt.strftime("%d/%m/%Y")
            time_info["expiry_time"] = exp_dt.strftime("%H:%M:%S")
            if now > exp_dt:
                time_info["status"] = "expired"
                time_info["days_expired"] = (now - exp_dt).days
            else:
                time_info["status"] = "active"
                time_info["days_remaining"] = (exp_dt - now).days
                time_info["hours_remaining"] = (exp_dt - now).seconds // 3600
        except:
            time_info["status"] = "unknown"
    
    if k.get("activated_at"):
        time_info["activated_at"] = k["activated_at"]
        try:
            act_dt = datetime.strptime(k["activated_at"], "%Y-%m-%d %H:%M:%S")
            time_info["activated_date"] = act_dt.strftime("%d/%m/%Y")
            time_info["activated_time"] = act_dt.strftime("%H:%M:%S")
        except:
            pass
    
    if k.get("last_seen"):
        time_info["last_seen"] = k["last_seen"]
        try:
            last_dt = datetime.strptime(k["last_seen"], "%Y-%m-%d %H:%M:%S")
            time_info["last_seen_date"] = last_dt.strftime("%d/%m/%Y")
            time_info["last_seen_time"] = last_dt.strftime("%H:%M:%S")
            time_info["idle_hours"] = (now - last_dt).total_seconds() // 3600
        except:
            pass
    
    return jsonify({
        "status": "success",
        "code": 0,
        "server_time": now_str,
        "timestamp": int(time.time()),
        "key": key,
        "type": k.get("type"),
        "prefix": k.get("prefix"),
        "used": k.get("used", False),
        "udid": k.get("udid"),
        "device": k.get("device"),
        "ip": k.get("ip"),
        "activations": k.get("activations", 0),
        "max_activations": k.get("max_activations", 1),
        "time_info": time_info
    }), 200

@app.route('/api/revoke', methods=['POST'])
def api_revoke():
    data = request.get_json() or {}
    key = data.get('key', '')
    admin_key = data.get('admin_key', '')
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    
    if admin_key != str(BOT_TOKEN.split(':')[0]):
        return jsonify({
            "status": "error",
            "message": "Invalid admin key",
            "code": 9001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 403
    
    if not key:
        return jsonify({
            "status": "error",
            "message": "Missing key",
            "code": 5001,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 400
    
    if "keys" not in db or key not in db["keys"]:
        return jsonify({
            "status": "not_found",
            "message": "Key not found",
            "code": 5002,
            "server_time": now_str,
            "timestamp": int(time.time())
        }), 200
    
    k = db["keys"][key]
    k["used"] = False
    k["udid"] = None
    k["device"] = None
    k["ip"] = None
    k["activations"] = 0
    k["activated_at"] = None
    k["last_seen"] = None
    
    log(f"API REVOKE: {key} | Time: {now_str}")
    save_db()
    
    return jsonify({
        "status": "success",
        "message": f"Key {key} revoked",
        "code": 0,
        "revoked_at": now_str,
        "revoked_date": now.strftime("%d/%m/%Y"),
        "revoked_time": now.strftime("%H:%M:%S"),
        "server_time": now_str,
        "timestamp": int(time.time())
    }), 200

# ========== LOGGING ==========
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ========== DB FUNCTIONS ==========
def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Load {path} error: {e}")
    return default

def save_json(path, data):
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"Save {path} error: {e}")

db = load_json(DB_FILE, {
    "keys": {},
    "approved": {},
    "kicked": {},
    "logs": [],
    "devices": {},
    "stats": {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
})
bans = load_json(BAN_FILE, {"banned_ips": [], "banned_uids": [], "banned_devices": []})
config = load_json(CONFIG_FILE, {
    "auto_approve": True,
    "key_expiry_days": 30,
    "max_devices_per_key": 1,
    "notify_admin": True,
    "maintenance": False
})

def save_db():
    save_json(DB_FILE, db)

def save_bans():
    save_json(BAN_FILE, bans)

def save_config():
    save_json(CONFIG_FILE, config)

def log(msg):
    ts = time.strftime('%Y-%m-%d %H:%M:%S')
    entry = f"[{ts}] {msg}"
    if "logs" not in db:
        db["logs"] = []
    db["logs"].append(entry)
    db["logs"] = db["logs"][-500:]
    logger.info(msg)
    save_db()

def is_admin(uid):
    return uid in ADMIN_IDS

def is_banned(uid, ip=None, device=None):
    banned_uids = [x.get("uid") if isinstance(x, dict) else x for x in bans.get("banned_uids", [])]
    banned_ips = [x.get("ip") if isinstance(x, dict) else x for x in bans.get("banned_ips", [])]
    banned_devices = [x.get("device") if isinstance(x, dict) else x for x in bans.get("banned_devices", [])]
    return uid in banned_uids or (ip and ip in banned_ips) or (device and device in banned_devices)

def gen_key(prefix, ktype, days=30):
    code = hashlib.sha256(f"{uuid.uuid4()}{time.time()}".encode()).hexdigest()[:24]
    k = f"{prefix}-{ktype}-{code}"
    exp = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")
    if "keys" not in db:
        db["keys"] = {}
    if "stats" not in db:
        db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
    db["keys"][k] = {
        "type": ktype,
        "prefix": prefix,
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "expires": exp,
        "used": False,
        "udid": None,
        "device": None,
        "ip": None,
        "activations": 0,
        "max_activations": config.get("max_devices_per_key", 1),
        "last_seen": None,
        "last_device": None,
        "last_check": None
    }
    db["stats"]["total_keys"] += 1
    save_db()
    return k

# ========== BOT ==========
bot = telebot.TeleBot(BOT_TOKEN, threaded=False, skip_pending=True)

# ========== HANDLERS ==========
@bot.message_handler(commands=['start'])
def cmd_start(msg):
    uid = msg.from_user.id
    bot.reply_to(msg, f"👋 Chào mừng!\n👤 ID của bạn: `{uid}`\nGửi key để kích hoạt hoặc dùng /help để xem lệnh.", parse_mode="Markdown")

@bot.message_handler(commands=['help'])
def cmd_help(msg):
    is_adm = is_admin(msg.from_user.id)
    user_cmds = "👤 Lệnh User:\n/start - Khởi động\n/id - Xem ID\n/help - Trợ giúp"
    admin_cmds = (
        "\n\n🔧 Admin:\n"
        "/genkey <số> <loại> [prefix] [ngày] - Tạo key\n"
        "/genkeybulk <số> <loại> <prefix> [ngày] [file] - Tạo hàng loạt\n"
        "/approve <UID> [ghi chú] - Duyệt UID\n"
        "/unapprove <UID> - Hủy duyệt\n"
        "/kick <UID> [lý do] - Kick\n"
        "/ban <UID/IP> [lý do] - Ban\n"
        "/unban <UID/IP> - Gỡ ban\n"
        "/list - DS gần đây\n"
        "/listall - Xuất file tất cả\n"
        "/info <UID/Key> - Chi tiết\n"
        "/stats - Thống kê\n"
        "/logs [số] - Xem logs\n"
        "/clearlogs - Xóa logs\n"
        "/config <key> <value> - Cấu hình\n"
        "/broadcast <nội dung> - Gửi mass\n"
        "/backup - Backup DB\n"
        "/restore <timestamp> - Restore DB\n"
        "/maintenance - Bật/tắt bảo trì"
    )
    bot.reply_to(msg, user_cmds + (admin_cmds if is_adm else ""), parse_mode="Markdown")

@bot.message_handler(commands=['id'])
def cmd_id(msg):
    bot.reply_to(msg, f"👤 User ID: `{msg.from_user.id}`\n💬 Chat ID: `{msg.chat.id}`", parse_mode="Markdown")

@bot.message_handler(commands=['genkey'])
def cmd_genkey(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        bot.reply_to(msg, "📌 Cú pháp: /genkey <số> <loại> [prefix] [ngày]")
        return
    try:
        num = int(parts[1])
        ktype = parts[2]
        prefix = parts[3] if len(parts) > 3 else "hake"
        days = int(parts[4]) if len(parts) > 4 else config.get("key_expiry_days", 30)
        keys = [gen_key(prefix, ktype, days) for _ in range(num)]
        log(f"ADMIN {msg.from_user.id} GEN {num} KEY")
        bot.reply_to(msg, "\n".join([f"`{k}`" for k in keys]), parse_mode="Markdown")
    except Exception as e:
        logger.error(f"genkey error: {e}")
        bot.reply_to(msg, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['genkeybulk'])
def cmd_genkeybulk(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 4:
        bot.reply_to(msg, "📌 Cú pháp: /genkeybulk <số> <loại> <prefix> [ngày] [file]")
        return
    try:
        num = int(parts[1])
        ktype = parts[2]
        prefix = parts[3]
        days = int(parts[4]) if len(parts) > 4 else 30
        filename = parts[5] if len(parts) > 5 else f"keys_{int(time.time())}.txt"
        keys = [gen_key(prefix, ktype, days) for _ in range(num)]
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("\n".join(keys))
        log(f"ADMIN BULK GEN {num} KEY -> {filename}")
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f, caption=f"📁 {num} keys")
        os.remove(filename)
    except Exception as e:
        logger.error(f"genkeybulk error: {e}")
        bot.reply_to(msg, f"❌ Lỗi: {e}")

@bot.message_handler(commands=['approve'])
def cmd_approve(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /approve <UID> [ghi chú]")
        return
    note = " ".join(parts[2:]) if len(parts) > 2 else ""
    if "approved" not in db:
        db["approved"] = {}
    db["approved"][parts[1]] = {
        "approved_by": str(msg.from_user.id),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": note
    }
    log(f"ADMIN APPROVE: {parts[1]}")
    save_db()
    bot.reply_to(msg, f"✅ Đã duyệt: `{parts[1]}`", parse_mode="Markdown")

@bot.message_handler(commands=['unapprove'])
def cmd_unapprove(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /unapprove <UID>")
        return
    if "approved" not in db:
        db["approved"] = {}
    db["approved"].pop(parts[1], None)
    log(f"ADMIN UNAPPROVE: {parts[1]}")
    save_db()
    bot.reply_to(msg, f"🚫 Đã hủy duyệt: `{parts[1]}`", parse_mode="Markdown")

@bot.message_handler(commands=['kick'])
def cmd_kick(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /kick <UID> [lý do]")
        return
    reason = " ".join(parts[2:]) if len(parts) > 2 else "No reason"
    if "kicked" not in db:
        db["kicked"] = {}
    if "stats" not in db:
        db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
    db["kicked"][parts[1]] = {
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "by": str(msg.from_user.id),
        "reason": reason
    }
    if "approved" in db:
        db["approved"].pop(parts[1], None)
    db["stats"]["total_kicked"] = db["stats"].get("total_kicked", 0) + 1
    log(f"ADMIN KICK: {parts[1]} - {reason}")
    save_db()
    bot.reply_to(msg, f"❌ Đã kick: `{parts[1]}`\n📝 Lý do: {reason}", parse_mode="Markdown")

@bot.message_handler(commands=['ban'])
def cmd_ban(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /ban <UID/IP/Device> [lý do]")
        return
    target = parts[1]
    reason = " ".join(parts[2:]) if len(parts) > 2 else "Banned by admin"
    if '.' in target and re.match(r'^[\d.:]+$', target):
        if "banned_ips" not in bans:
            bans["banned_ips"] = []
        bans["banned_ips"].append({"ip": target, "reason": reason, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    else:
        if "banned_uids" not in bans:
            bans["banned_uids"] = []
        bans["banned_uids"].append({"uid": target, "reason": reason, "time": time.strftime("%Y-%m-%d %H:%M:%S")})
    save_bans()
    log(f"ADMIN BAN: {target}")
    bot.reply_to(msg, f"🔨 Đã ban: `{target}`", parse_mode="Markdown")

@bot.message_handler(commands=['unban'])
def cmd_unban(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /unban <UID/IP>")
        return
    target = parts[1]
    if "banned_uids" not in bans:
        bans["banned_uids"] = []
    if "banned_ips" not in bans:
        bans["banned_ips"] = []
    bans["banned_uids"] = [x for x in bans["banned_uids"] if (x.get("uid") if isinstance(x, dict) else x) != target]
    bans["banned_ips"] = [x for x in bans["banned_ips"] if (x.get("ip") if isinstance(x, dict) else x) != target]
    save_bans()
    log(f"ADMIN UNBAN: {target}")
    bot.reply_to(msg, f"🔓 Đã gỡ ban: `{target}`", parse_mode="Markdown")

@bot.message_handler(commands=['list'])
def cmd_list(msg):
    if "approved" not in db:
        db["approved"] = {}
    if "keys" not in db:
        db["keys"] = {}
    if "kicked" not in db:
        db["kicked"] = {}
    if "stats" not in db:
        db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
    
    approved = list(db["approved"].keys())[-20:]
    keys = list(db["keys"].keys())[-20:]
    kicked = list(db["kicked"].keys())[-10:]
    
    resp = f"📊 Stats: {db['stats'].get('total_keys', 0)} keys | {db['stats'].get('total_approved', 0)} approved | {db['stats'].get('total_kicked', 0)} kicked\n\n"
    resp += "✅ Approved:\n" + ("\n".join([f"- `{u}`" for u in approved]) or "None")
    resp += "\n\n🔑 Keys (gần đây):\n" + ("\n".join([f"- `{k[:40]}...`" for k in keys]) or "None")
    resp += "\n\n❌ Kicked:\n" + ("\n".join([f"- `{u}`" for u in kicked]) or "None")
    bot.reply_to(msg, resp, parse_mode="Markdown")

@bot.message_handler(commands=['listall'])
def cmd_listall(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    if "keys" not in db:
        db["keys"] = {}
    keys = "\n".join([f"{k}: used={v.get('used', False)}, exp={v.get('expires','N/A')}" for k, v in db["keys"].items()])
    filename = f"all_keys_{int(time.time())}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(keys)
    with open(filename, 'rb') as f:
        bot.send_document(msg.chat.id, f)
    os.remove(filename)

@bot.message_handler(commands=['info'])
def cmd_info(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /info <UID/Key>")
        return
    target = parts[1]
    if "approved" not in db:
        db["approved"] = {}
    if "keys" not in db:
        db["keys"] = {}
    
    if target in db["approved"]:
        info = db["approved"][target]
        bot.reply_to(
            msg,
            f"👤 UID: `{target}`\n⏰ Duyệt: {info.get('time')}\n👤 Bởi: {info.get('approved_by')}\n📝 Ghi chú: {info.get('note','N/A')}",
            parse_mode="Markdown"
        )
    elif target in db["keys"]:
        k = db["keys"][target]
        bot.reply_to(
            msg,
            f"🔑 Key: `{target[:40]}...`\n📌 Loại: {k.get('type','N/A')}\n✅ Đã dùng: {k.get('used', False)}\n📅 Hết hạn: {k.get('expires','N/A')}\n🔢 Kích hoạt: {k.get('activations',0)}/{k.get('max_activations',1)}",
            parse_mode="Markdown"
        )
    else:
        bot.reply_to(msg, "❌ Không tìm thấy.")

@bot.message_handler(commands=['stats'])
def cmd_stats(msg):
    if "keys" not in db:
        db["keys"] = {}
    total = len(db["keys"])
    used = sum(1 for v in db["keys"].values() if v.get("used", False))
    active = 0
    expired = 0
    for v in db["keys"].values():
        if v.get("used", False):
            try:
                exp = datetime.strptime(v["expires"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp:
                    expired += 1
                else:
                    active += 1
            except:
                active += 1
    if "approved" not in db:
        db["approved"] = {}
    if "kicked" not in db:
        db["kicked"] = {}
    bot.reply_to(
        msg,
        f"📊 Thống kê:\n"
        f"🔑 Tổng: {total}\n"
        f"✅ Đã dùng: {used}\n"
        f"🟢 Còn hạn: {active}\n"
        f"🔴 Hết hạn: {expired}\n"
        f"👤 Approved: {len(db['approved'])}\n"
        f"❌ Kicked: {len(db['kicked'])}"
    )

@bot.message_handler(commands=['logs'])
def cmd_logs(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    n = int(parts[1]) if len(parts) > 1 else 20
    if "logs" not in db:
        db["logs"] = []
    logs = db["logs"][-n:]
    text = "\n".join(logs) or "No logs"
    if len(text) > 4000:
        filename = f"logs_{int(time.time())}.txt"
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(text)
        with open(filename, 'rb') as f:
            bot.send_document(msg.chat.id, f)
        os.remove(filename)
    else:
        bot.reply_to(msg, f"📜 Logs ({n}):\n```\n{text}\n```", parse_mode="Markdown")

@bot.message_handler(commands=['clearlogs'])
def cmd_clearlogs(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    db["logs"] = []
    save_db()
    bot.reply_to(msg, "🗑️ Đã xóa logs.")

@bot.message_handler(commands=['config'])
def cmd_config_cmd(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 3:
        bot.reply_to(
            msg,
            f"⚙️ Config hiện tại:\n```\n{json.dumps(config, indent=2, ensure_ascii=False)}\n```\n"
            f"📌 /config <key> <value>",
            parse_mode="Markdown"
        )
        return
    key, val = parts[1], parts[2]
    if key in ["auto_approve", "notify_admin", "maintenance"]:
        config[key] = val.lower() in ["true", "1", "yes", "on"]
    elif key in ["key_expiry_days", "max_devices_per_key"]:
        config[key] = int(val)
    else:
        config[key] = val
    save_config()
    log(f"CONFIG UPDATE: {key}={val}")
    bot.reply_to(msg, f"✅ Cập nhật: `{key} = {val}`", parse_mode="Markdown")

@bot.message_handler(commands=['broadcast'])
def cmd_broadcast(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    text = msg.text[len("/broadcast "):]
    if not text:
        bot.reply_to(msg, "📌 Cú pháp: /broadcast <nội dung>")
        return
    count = 0
    if "approved" not in db:
        db["approved"] = {}
    for uid in set(list(db["approved"].keys()) + [str(x) for x in ADMIN_IDS]):
        try:
            bot.send_message(int(uid), f"📢 Thông báo:\n{text}")
            count += 1
        except Exception as e:
            logger.error(f"Broadcast to {uid} failed: {e}")
    bot.reply_to(msg, f"✅ Đã gửi tới {count} người.")

@bot.message_handler(commands=['backup'])
def cmd_backup(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    ts = int(time.time())
    for f in [DB_FILE, BAN_FILE, CONFIG_FILE]:
        if os.path.exists(f):
            os.system(f"cp {f} {f}.{ts}.bak")
    bot.reply_to(msg, f"💾 Backup hoàn tất: `*.{ts}.bak`", parse_mode="Markdown")

@bot.message_handler(commands=['restore'])
def cmd_restore(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    parts = msg.text.split()
    if len(parts) < 2:
        bot.reply_to(msg, "📌 Cú pháp: /restore <timestamp>")
        return
    ts = parts[1]
    for f in [DB_FILE, BAN_FILE, CONFIG_FILE]:
        bak = f"{f}.{ts}.bak"
        if os.path.exists(bak):
            os.system(f"cp {bak} {f}")
    global db, bans, config
    db = load_json(DB_FILE, db)
    bans = load_json(BAN_FILE, bans)
    config = load_json(CONFIG_FILE, config)
    bot.reply_to(msg, "🔄 Restore hoàn tất.")

@bot.message_handler(commands=['maintenance'])
def cmd_maintenance(msg):
    if not is_admin(msg.from_user.id):
        bot.reply_to(msg, "❌ Bạn không phải admin!")
        return
    config["maintenance"] = not config.get("maintenance", False)
    save_config()
    status = "BẬT" if config["maintenance"] else "TẮT"
    log(f"MAINTENANCE {status}")
    bot.reply_to(msg, f"🔧 Maintenance: {status}")

@bot.message_handler(func=lambda m: True)
def handle_all(msg):
    try:
        uid = str(msg.from_user.id)
        text = msg.text.strip() if msg.text else ""
        
        if is_banned(uid):
            bot.reply_to(msg, "⛔ Bạn đã bị cấm sử dụng bot.")
            return
        
        if config.get("maintenance", False) and not is_admin(msg.from_user.id):
            bot.reply_to(msg, "🔧 Bot đang bảo trì. Vui lòng thử lại sau.")
            return
        
        if text.startswith('/'):
            return
        
        # Dylib auto-approve
        if "#KichHoat" in text or "#Start" in text or "#YeuCau" in text:
            device_uid = None
            for part in text.split():
                if part.startswith("UID:") or part.startswith("UDID:"):
                    device_uid = part.split(":", 1)[1]
            if device_uid:
                if not config.get("auto_approve", True):
                    bot.reply_to(msg, "⏳ Chờ admin duyệt...")
                    if config.get("notify_admin", True):
                        for admin in ADMIN_IDS:
                            try:
                                bot.send_message(admin, f"📋 Yêu cầu duyệt:\nUID: `{device_uid}`\nUser: {uid}", parse_mode="Markdown")
                            except:
                                pass
                    return
                if "approved" not in db:
                    db["approved"] = {}
                db["approved"][device_uid] = {
                    "approved_by": "auto",
                    "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "telegram_uid": uid
                }
                log(f"AUTO APPROVE: {device_uid}")
                save_db()
                bot.reply_to(msg, f"✅ Đã duyệt UID: `{device_uid}`", parse_mode="Markdown")
                return
        
        # Key activation
        if '-' in text and len(text) > 10:
            if "kicked" not in db:
                db["kicked"] = {}
            if text in db["kicked"]:
                bot.reply_to(msg, "❌ Key đã bị thu hồi.")
                return
            
            if "keys" not in db:
                db["keys"] = {}
            if text not in db["keys"]:
                bot.reply_to(msg, "❌ Key không hợp lệ hoặc không tồn tại.")
                return
            
            key = db["keys"][text]
            
            if key.get("used", False):
                if key.get("udid") and key["udid"] != uid:
                    bot.reply_to(msg, "❌ Key đã được kích hoạt trên thiết bị khác.")
                    return
                bot.reply_to(msg, "ℹ️ Key đã kích hoạt trước đó.")
                return
            
            if key.get("activations", 0) >= key.get("max_activations", 1):
                bot.reply_to(msg, "❌ Key đã đạt giới hạn thiết bị.")
                return
            
            try:
                exp = datetime.strptime(key["expires"], "%Y-%m-%d %H:%M:%S")
                if datetime.now() > exp:
                    bot.reply_to(msg, "❌ Key đã hết hạn.")
                    return
            except:
                pass
            
            key["used"] = True
            key["udid"] = uid
            key["device"] = "Telegram"
            key["ip"] = msg.from_user.username or "unknown"
            key["activations"] = key.get("activations", 0) + 1
            key["activated_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            if "approved" not in db:
                db["approved"] = {}
            if "stats" not in db:
                db["stats"] = {"total_keys": 0, "total_approved": 0, "total_kicked": 0}
            db["approved"][uid] = {
                "approved_by": "auto",
                "time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "key": text
            }
            db["stats"]["total_approved"] = db["stats"].get("total_approved", 0) + 1
            log(f"KEY ACTIVE: {text} by {uid}")
            save_db()
            
            bot.reply_to(
                msg,
                f"✅ Key kích hoạt thành công!\n"
                f"📅 Hết hạn: `{key['expires']}`\n"
                f"🔢 Lượt kích hoạt: {key['activations']}/{key['max_activations']}",
                parse_mode="Markdown"
            )
            return
        
        bot.reply_to(msg, "❓ Không hiểu lệnh. Dùng /help để xem hướng dẫn.")
    
    except Exception as e:
        logger.error(f"Handle error: {e}")
        bot.reply_to(msg, "⚠️ Đã xảy ra lỗi. Vui lòng thử lại.")

# ========== RUN ==========
if __name__ == "__main__":
    print("🤖 Bot UnbndSDK Online - Admin: 5736655322")
    log("BOT ONLINE")
    
    import threading
    def run_bot():
        while True:
            try:
                bot.infinity_polling(timeout=60, long_polling_timeout=30)
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
    
    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, threaded=True)
