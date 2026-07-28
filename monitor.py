import os
import sys
import json
import argparse
import urllib.request
import datetime

# Set UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

STATE_FILE = 'state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "status" in data:
                    return data
                return {"status": data, "errors": {}}
        except Exception as e:
            print(f"Error loading state.json: {e}")
    return {"status": {}, "errors": {}}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state.json: {e}")

def send_telegram_alert(bot_token, chat_ids, message):
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN environment variable or --token is missing.")
        return False

    if isinstance(chat_ids, str):
        chat_ids = [c.strip() for c in chat_ids.split(',') if c.strip()]
    
    if not chat_ids:
        env_chats = os.getenv('TELEGRAM_CHAT_ID')
        if env_chats:
            chat_ids = [c.strip() for c in env_chats.split(',') if c.strip()]

    if not chat_ids:
        print("Error: TELEGRAM_CHAT_ID environment variable or --chats is missing.")
        return False

    success_count = 0
    for chat_id in chat_ids:
        telegram_url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = json.dumps({
            'chat_id': chat_id,
            'text': message,
            'parse_mode': 'HTML',
            'disable_web_page_preview': False
        }).encode('utf-8')

        req = urllib.request.Request(
            telegram_url,
            data=payload,
            headers={'Content-Type': 'application/json'}
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                res_data = json.loads(resp.read().decode('utf-8'))
                print(f"Telegram alert sent to {chat_id}:", res_data.get('ok'))
                if res_data.get('ok'):
                    success_count += 1
        except urllib.error.HTTPError as e:
            body = e.read().decode('utf-8', errors='ignore')
            print(f"HTTP Error sending to {chat_id} ({e.code}): {body}")
        except Exception as e:
            print(f"Error sending Telegram notification to {chat_id}: {e}")

    return success_count > 0

def run_check(bot_token=None, chat_ids=None, force_notify=False):
    bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not chat_ids and os.getenv('TELEGRAM_CHAT_ID'):
        chat_ids = [c.strip() for c in os.getenv('TELEGRAM_CHAT_ID').split(',') if c.strip()]

    previous_data = load_state()
    previous_status = previous_data.get("status", {})

    arvan_worker_url = os.getenv('ARVAN_WORKER_URL')
    if not arvan_worker_url:
        print("Error: ARVAN_WORKER_URL env variable is not set!")
        sys.exit(1)

    # Branches to check by querying their specific sub-urls on the worker
    branches = [
        ('Shahrak Gharb (شهرک غرب)', 'شهرک غرب', '/order/gelatohouse'),
        ('Velenjak (ولنجک)', 'ولنجک', '/order/gelato-house')
    ]

    current_status = {}
    current_errors = {}
    changes = []
    summary_lines = []

    print("Checking Gelato House Passion Fruit availability via Arvan Worker sub-URLs...")

    for json_key, display_name, branch_path in branches:
        target_url = arvan_worker_url.rstrip('/') + branch_path + "?json=true"
        branch_url = "http://order.gelatohouse.ir" + branch_path
        print(f"Fetching: {target_url}")
        
        req = urllib.request.Request(
            target_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )

        data = None
        last_exception = None

        for attempt in range(2):
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    break
            except Exception as e:
                last_exception = e
                print(f"[{display_name}] Attempt {attempt + 1} failed: {e}")
                if attempt == 0:
                    import time
                    time.sleep(2)

        if data:
            is_available = data.get("available", False)
            error = data.get("error")
            
            if error:
                print(f"[{display_name}] ⚠️ Worker reported error: {error}")
                current_status[json_key] = previous_status.get(json_key, False)
                current_errors[json_key] = error
                
                icon = "⚠️"
                summary_lines.append(f"{icon} <b>{display_name}</b>: خطا در به‌روزرسانی ({error})\n🔗 <a href='{branch_url}'>مشاهده منو ↗</a>")
            else:
                status_str = "Available (موجود)" if is_available else "Not Available (ناموجود)"
                icon = "🌸" if is_available else "💤"
                print(f"[{display_name}] {icon} {status_str}")
                
                current_status[json_key] = is_available
                prev_available = previous_status.get(json_key)
                
                if prev_available != is_available:
                    changes.append((display_name, is_available))
                    
                status_text = "<b>موجود و آماده سفارش! 🎉</b>" if is_available else "<b>فعلاً ناموجوده 😴</b>"
                btn_text = "ثبت سفارش ⚡" if is_available else "مشاهده منو ↗"
                summary_lines.append(f"{icon} <b>{display_name}</b>: {status_text}\n🔗 <a href='{branch_url}'>{btn_text}</a>")
        else:
            print(f"[{display_name}] ⚠️ Connection to worker failed: {last_exception}")
            current_status[json_key] = previous_status.get(json_key, False)
            current_errors[json_key] = str(last_exception)
            
            icon = "⚠️"
            summary_lines.append(f"{icon} <b>{display_name}</b>: خطا در ارتباط با پروکسی ({last_exception})\n🔗 <a href='{branch_url}'>مشاهده منو ↗</a>")

    # Save to local file system
    save_data = {
        "status": current_status,
        "errors": current_errors,
        "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    save_state(save_data)

    if changes or force_notify:
        alert_msg = "🍧 <b>پایش‌گر پشن فروت ژلاتو هاوس</b> 💛\n\n"
        alert_msg += "سلام! پشن‌کوچولو وضعیت جدید رو گزارش می‌ده: 🥭✨\n\n"
        alert_msg += "\n\n".join(summary_lines)

        print("\n--- Sending Notification ---")
        send_telegram_alert(bot_token, chat_ids, alert_msg)
    else:
        print("\nNo status changes detected. Skipping Telegram alert.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gelato House Status Synchronizer')
    parser.add_argument('--token', default=os.getenv('TELEGRAM_BOT_TOKEN'), help='Telegram Bot Token')
    parser.add_argument('--chats', nargs='+', default=None, help='Telegram Chat IDs')
    parser.add_argument('--force-notify', action='store_true', help='Force send notification regardless of state change')

    args = parser.parse_args()
    run_check(bot_token=args.token, chat_ids=args.chats, force_notify=args.force_notify)
