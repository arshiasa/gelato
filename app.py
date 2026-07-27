import os
import json
import threading
import time
import datetime
import urllib.request
from flask import Flask, jsonify
from flask_cors import CORS

app = Flask(__name__)
# Enable CORS so your GitHub Pages website can fetch from this server
CORS(app)

BRANCHES = {
    'Shahrak Gharb (شهرک غرب)': 'http://order.gelatohouse.ir/order/gelatohouse',
    'Velenjak (ولنجک)': 'http://order.gelatohouse.ir/order/gelato-house'
}

TARGET_KEYWORD = 'پشن'
VALIDATION_KEYWORD = 'ژلاتو'

# Global in-memory cache for status
status_cache = {
    "status": {},
    "errors": {},
    "last_checked": None
}

def check_branch_online(url):
    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fa,en;q=0.9'
        }
    )
    try:
        # Since this runs inside Iran (ArvanCloud), direct connection works without proxies
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            if VALIDATION_KEYWORD not in html:
                raise Exception("Validation keyword missing")
            return TARGET_KEYWORD in html, len(html)
    except Exception as e:
        print(f"Error fetching {url}: {e}")
        return None, 0

def send_telegram_alert(message):
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_ids_str = os.getenv('TELEGRAM_CHAT_ID')
    if not bot_token or not chat_ids_str:
        print("Telegram env variables missing, skipping alert.")
        return
    
    chat_ids = [c.strip() for c in chat_ids_str.split(',') if c.strip()]
    for chat_id in chat_ids:
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML'
        }).encode('utf-8')
        req = urllib.request.Request(
            telegram_url, 
            data=payload, 
            headers={'Content-Type': 'application/json'}
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                pass
        except Exception as e:
            print(f"Failed to send Telegram alert to {chat_id}: {e}")

def monitor_loop():
    global status_cache
    print("Starting background Gelato monitoring loop...")
    while True:
        current_status = {}
        current_errors = {}
        changes = []
        summary_lines = []
        
        for branch_name, branch_url in BRANCHES.items():
            is_avail, _ = check_branch_online(branch_url)
            
            if is_avail is None:
                current_errors[branch_name] = "timeout"
                # Fallback to last known cache status or False
                current_status[branch_name] = status_cache["status"].get(branch_name, False)
                icon = "⚠️"
                summary_lines.append(f"{icon} <b>{branch_name}</b>: خطا در به‌روزرسانی (استفاده از کش)")
            else:
                current_status[branch_name] = is_avail
                prev_avail = status_cache["status"].get(branch_name)
                
                # If availability state changed, alert
                if prev_avail is not None and prev_avail != is_avail:
                    changes.append((branch_name, is_avail))
                
                icon = "🟢" if is_avail else "🔴"
                summary_lines.append(f"{icon} <b>{branch_name}</b>: {'<b>موجود (Available)</b>' if is_avail else 'ناموجود (Out of stock)'}\n🔗 <a href='{branch_url}'>سفارش آنلاین</a>")
        
        # Update global cache
        status_cache = {
            "status": current_status,
            "errors": current_errors,
            "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }
        
        if changes:
            alert_msg = "🍧 <b>Gelato House Passion Fruit Update</b> 🍧\n\n"
            alert_msg += "پشن فروت در شعبه‌های ژلاتو هاوس:\n\n"
            alert_msg += "\n\n".join(summary_lines)
            send_telegram_alert(alert_msg)
            
        # Sleep for 5 minutes
        time.sleep(300)

# Endpoint to fetch live status
@app.route('/api/status')
def get_status():
    return jsonify(status_cache)

# Homepage fallback to serve index.html directly if they host the frontend on Arvan too
@app.route('/')
def home():
    try:
        with open('index.html', 'r', encoding='utf-8') as f:
            return f.read()
    except Exception:
        return "Gelato House Monitor API is Running!"

if __name__ == '__main__':
    # Start background loop as daemon thread
    t = threading.Thread(target=monitor_loop, daemon=True)
    t.start()
    
    # ArvanCloud binds to PORT env variable
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
