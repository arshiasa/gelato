import os
import sys
import json
import argparse
import urllib.request
import urllib.parse
import datetime

# Set UTF-8 encoding for standard output
sys.stdout.reconfigure(encoding='utf-8')

STATE_FILE = 'state.json'

BRANCHES = {
    'Shahrak Gharb (شهرک غرب)': 'http://order.gelatohouse.ir/order/gelatohouse',
    'Velenjak (ولنجک)': 'http://order.gelatohouse.ir/order/gelato-house'
}

TARGET_KEYWORD = 'پشن'
VALIDATION_KEYWORD = 'ژلاتو'

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if "status" in data:
                    return data["status"]
                return data
        except Exception as e:
            print(f"Error loading state.json: {e}")
    return {}

def save_state(state):
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"Error saving state.json: {e}")

def get_iranian_proxies():
    url = "https://proxylist.geonode.com/api/proxy-list?country=IR&protocols=http,https&limit=50&sort_by=lastChecked&sort_type=desc"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return [f"http://{p['ip']}:{p['port']}" for p in data.get('data', [])]
    except Exception as e:
        print(f"Failed to fetch proxies: {e}")
        return []

def check_branch_online(url, local_file=None, proxy=None):
    if local_file and os.path.exists(local_file):
        with open(local_file, 'r', encoding='utf-8', errors='ignore') as f:
            html = f.read()
        return TARGET_KEYWORD in html, len(html)

    req = urllib.request.Request(
        url,
        headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fa,en;q=0.9'
        }
    )
    
    opener = urllib.request.build_opener()
    if proxy:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({'http': proxy, 'https': proxy}))

    try:
        with opener.open(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            if VALIDATION_KEYWORD not in html:
                raise Exception("Fake proxy block page detected (missing validation keyword)")
            return TARGET_KEYWORD in html, len(html)
    except Exception as e:
        return None, 0

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

def run_check(bot_token=None, chat_ids=None, force_notify=False, mock_files=False):
    bot_token = bot_token or os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not chat_ids and os.getenv('TELEGRAM_CHAT_ID'):
        chat_ids = [c.strip() for c in os.getenv('TELEGRAM_CHAT_ID').split(',') if c.strip()]

    previous_state = load_state()
    current_state = {}
    changes = []
    summary_lines = []

    print("Checking Gelato House Passion Fruit availability...")
    
    proxies = []
    if not mock_files:
        print("Fetching free Iranian proxies...")
        proxies = get_iranian_proxies()
        print(f"Found {len(proxies)} proxies.")

    working_proxy = None

    for branch_name, branch_url in BRANCHES.items():
        mock_file = None
        if mock_files:
            if 'Shahrak' in branch_name:
                mock_file = 'd60b82ab-3578-4ef5-b6e7-d11a7f8a2e4a.htm'
            else:
                mock_file = '055ac9b8-3dc6-4b91-90ef-e10ecfb8d6f0.htm'

        is_available, html_len = None, 0
        
        if mock_files:
            is_available, html_len = check_branch_online(branch_url, local_file=mock_file)
        else:
            proxies_to_test = []
            if working_proxy:
                proxies_to_test.append(working_proxy)
            proxies_to_test.append(None) # Always try direct connection
            for p in proxies:
                if p not in proxies_to_test:
                    proxies_to_test.append(p)
                    
            for proxy in proxies_to_test:
                is_available, html_len = check_branch_online(branch_url, proxy=proxy)
                if is_available is not None:
                    if proxy and proxy != working_proxy:
                        print(f"✅ Bypassed firewall using proxy {proxy}")
                    working_proxy = proxy
                    break

        if is_available is None:
            print(f"[{branch_name}] ⚠️ Could not check branch (All proxies failed/Timeout).")
            continue

        status_str = "Available (موجود)" if is_available else "Not Available (ناموجود)"
        icon = "🟢" if is_available else "🔴"
        print(f"[{branch_name}] {icon} {status_str} (HTML size: {html_len} bytes)")

        current_state[branch_name] = is_available
        prev_available = previous_state.get(branch_name)

        if prev_available != is_available:
            changes.append((branch_name, is_available))

        summary_lines.append(f"{icon} <b>{branch_name}</b>: {'<b>موجود (Available)</b>' if is_available else 'ناموجود (Out of stock)'}\n🔗 <a href='{branch_url}'>سفارش آنلاین</a>")

    save_data = {
        "status": current_state,
        "last_checked": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }
    save_state(save_data)

    if changes or force_notify:
        alert_msg = "🍧 <b>Gelato House Passion Fruit Update</b> 🍧\n\n"
        alert_msg += "پشن فروت در شعبه‌های ژلاتو هاوس:\n\n"
        alert_msg += "\n\n".join(summary_lines)

        print("\n--- Sending Notification ---")
        send_telegram_alert(bot_token, chat_ids, alert_msg)
    else:
        print("\nNo status changes detected. Skipping Telegram alert.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Gelato House Availability Checker')
    parser.add_argument('--token', default=os.getenv('TELEGRAM_BOT_TOKEN'), help='Telegram Bot Token')
    parser.add_argument('--chats', nargs='+', default=None, help='Telegram Chat IDs')
    parser.add_argument('--force-notify', action='store_true', help='Force send notification regardless of state change')
    parser.add_argument('--mock', action='store_true', help='Use offline mock HTML files for testing')

    args = parser.parse_args()
    run_check(bot_token=args.token, chat_ids=args.chats, force_notify=args.force_notify, mock_files=args.mock)
