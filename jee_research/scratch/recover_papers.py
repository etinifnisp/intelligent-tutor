import os
import re
import time
import httpx
from pathlib import Path
import random

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0"
]

def extract_gdrive_id(url: str) -> str | None:
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

def resolve_download_url(url: str) -> str:
    curr_url = url
    headers = {"User-Agent": random.choice(USER_AGENTS)}
    try:
        # Follow redirects
        with httpx.Client(follow_redirects=True) as client:
            resp = client.head(curr_url, headers=headers, timeout=15.0)
            gdrive_id = extract_gdrive_id(str(resp.url))
            if gdrive_id:
                return f"https://drive.google.com/uc?export=download&id={gdrive_id}"
            
            # If head failed to show drive URL, try get
            resp2 = client.get(curr_url, headers=headers, timeout=15.0)
            gdrive_id = extract_gdrive_id(str(resp2.url))
            if gdrive_id:
                return f"https://drive.google.com/uc?export=download&id={gdrive_id}"
            return str(resp2.url)
    except Exception as e:
        print(f"Error resolving redirect for {url}: {e}")
        return url

def download_file(url: str, dest: Path) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    headers = {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "*/*",
        "Connection": "keep-alive"
    }
    
    # Try direct download first
    try:
        with httpx.Client(follow_redirects=True) as client:
            print(f"Downloading from resolved URL: {url}")
            resp = client.get(url, headers=headers, timeout=40.0)
            if resp.status_code == 200 and len(resp.content) > 10240:
                dest.write_bytes(resp.content)
                print(f"Saved: {dest.name} ({len(resp.content)//1024} KB)")
                return True
            else:
                print(f"Invalid response for {url}: Status {resp.status_code}, size={len(resp.content)}")
    except Exception as e:
        print(f"Exception downloading {url}: {e}")
    return False

# Target 5 papers that we found on MathonGo
targets = [
    # (year, MMDD, shift, mathongo_link)
    ("2021", "0722", "1", "https://links.mathongo.com/xwCd"),
    ("2021", "0901", "2", "https://links.mathongo.com/iwUM"),
    ("2018", "0408", "1", "https://links.mathongo.com/QME"),
    ("2017", "0402", "1", "https://links.mathongo.com/Fwwk"),
    ("2016", "0403", "1", "https://links.mathongo.com/YBo")
]

project_root = Path(__file__).resolve().parent.parent
output_dir = project_root / "papers" / "Mains"

recovered_count = 0

for year, mmdd, shift, link in targets:
    filename = f"JEE_MAIN_{year}_{mmdd}_Shift{shift}.pdf"
    dest_path = output_dir / year / filename
    print(f"\n--- Recovering: {filename} ---")
    print(f"Source Link: {link}")
    
    resolved = resolve_download_url(link)
    print(f"Resolved URL: {resolved}")
    
    success = download_file(resolved, dest_path)
    if success:
        recovered_count += 1
    else:
        print(f"Failed to recover: {filename}")
    time.sleep(2.0)

print(f"\n====================================")
print(f"RECOVERY SUMMARY: {recovered_count} of {len(targets)} files successfully recovered.")
print(f"====================================")
