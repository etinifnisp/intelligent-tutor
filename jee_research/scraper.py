import os
import sys
import re
import time
import base64
import json
import random
import logging
import asyncio
import argparse
import urllib.parse
from pathlib import Path
import httpx
from bs4 import BeautifulSoup
import fitz  # PyMuPDF

# List of rotating User-Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

LAST_REQUEST_TIME = 0.0

def setup_logging(log_file: Path) -> logging.Logger:
    """Configures the logging system to output to both console and log file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)
    
    logger = logging.getLogger("jee_scraper")
    logger.setLevel(logging.INFO)
    
    if logger.handlers:
        logger.handlers.clear()
        
    formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%dT%H:%M:%S")
    
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger

async def enforce_rate_limit():
    """Enforces a 2-second rate-limiting delay between requests."""
    global LAST_REQUEST_TIME
    now = time.time()
    elapsed = now - LAST_REQUEST_TIME
    if elapsed < 2.0:
        sleep_time = 2.0 - elapsed
        await asyncio.sleep(sleep_time)
    LAST_REQUEST_TIME = time.time()

def extract_gdrive_id(url: str) -> str | None:
    """Extracts the file ID from a Google Drive URL."""
    match = re.search(r'/file/d/([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    match = re.search(r'[?&]id=([a-zA-Z0-9_-]+)', url)
    if match:
        return match.group(1)
    return None

async def resolve_download_url(client: httpx.AsyncClient, url: str, logger: logging.Logger) -> str:
    """Follows redirects manually to detect Google Drive URLs and construct direct download links."""
    curr_url = url
    for _ in range(5):  # max 5 redirects
        gdrive_id = extract_gdrive_id(curr_url)
        if gdrive_id:
            direct_url = f"https://drive.google.com/uc?export=download&id={gdrive_id}"
            logger.info(f"Resolved Google Drive ID: {gdrive_id} -> direct URL: {direct_url}")
            return direct_url
            
        await enforce_rate_limit()
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            response = await client.head(curr_url, headers=headers, timeout=10.0, follow_redirects=False)
            if response.status_code in [301, 302, 303, 307, 308]:
                location = response.headers.get("location")
                if location:
                    curr_url = urllib.parse.urljoin(curr_url, location)
                    continue
            return curr_url
        except Exception:
            try:
                response = await client.get(curr_url, headers=headers, timeout=10.0, follow_redirects=False)
                if response.status_code in [301, 302, 303, 307, 308]:
                    location = response.headers.get("location")
                    if location:
                        curr_url = urllib.parse.urljoin(curr_url, location)
                        continue
                return curr_url
            except Exception as e:
                logger.warning(f"Error resolving redirect for {curr_url}: {e}")
                return curr_url
    return curr_url

async def fetch_page(client: httpx.AsyncClient, url: str, logger: logging.Logger, referer: str = None) -> str | None:
    """Fetches web page content with headers rotating, backoff, and CAPTCHA checking."""
    await enforce_rate_limit()
    
    delays = [2, 4, 8]
    for attempt, delay in enumerate(delays):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive"
        }
        if referer:
            headers["Referer"] = referer
            
        logger.info(f"Fetching: {url} (Attempt {attempt + 1})")
        try:
            response = await client.get(url, headers=headers, timeout=20.0, follow_redirects=True)
            
            content_lower = response.text.lower()
            is_captcha = (
                response.status_code in [403, 429, 503] or
                any(kwd in content_lower for kwd in ["cf-challenge", "captcha", "recaptcha", "hcaptcha", "just a moment", "security challenge"])
            )
            if is_captcha:
                logger.warning(f"CAPTCHA or Cloudflare block detected at {url}. Skipping request to avoid hanging.")
                return None
                
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                logger.warning(f"URL {url} returned 404 Not Found. Skipping retries.")
                return None
                
            logger.warning(f"Status code {response.status_code} for {url}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.warning(f"Exception fetching {url}: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            
    logger.error(f"Failed to fetch {url} after {len(delays)} attempts.")
    return None

async def download_file(client: httpx.AsyncClient, url: str, dest: Path, logger: logging.Logger) -> bool:
    """Downloads a binary file with resume checking, rate-limiting, and backoff retries."""
    if dest.exists() and dest.stat().st_size > 10240:
        logger.info(f"Resume: File {dest.name} already exists. Skipping download.")
        return True
        
    await enforce_rate_limit()
    
    delays = [2, 4, 8]
    for attempt, delay in enumerate(delays):
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "*/*",
            "Connection": "keep-alive"
        }
        logger.info(f"Downloading PDF from: {url} (Attempt {attempt + 1})")
        try:
            response = await client.get(url, headers=headers, timeout=30.0, follow_redirects=True)
            
            content_type = response.headers.get("content-type", "").lower()
            if "html" in content_type:
                content_lower = response.text.lower()
                is_captcha = (
                    response.status_code in [403, 429, 503] or
                    any(kwd in content_lower for kwd in ["cf-challenge", "captcha", "recaptcha", "hcaptcha", "just a moment", "security challenge"])
                )
                if is_captcha:
                    logger.warning(f"CAPTCHA/Cloudflare block detected during download of {url}. Skipping.")
                    return False
            
            if response.status_code == 200 and len(response.content) > 10240:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(response.content)
                logger.info(f"Saved: {dest.name} ({len(response.content)//1024} KB)")
                return True
            elif response.status_code == 404:
                logger.warning(f"URL {url} returned 404 Not Found. Skipping retries.")
                return False
                
            logger.warning(f"Invalid response for {url}: Status {response.status_code}, size={len(response.content)}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
        except Exception as e:
            logger.warning(f"Exception downloading {url}: {e}. Retrying in {delay}s...")
            await asyncio.sleep(delay)
            
    logger.error(f"Failed to download {url} after {len(delays)} attempts.")
    return False

def parse_mathongo_desc(desc: str, default_year: int) -> tuple[int, str, int] | None:
    """Parses a MathonGo paper description to extract (year, session, shift)."""
    year_match = re.search(r'\b(201[5-9]|202[0-5])\b', desc)
    year = int(year_match.group(1)) if year_match else default_year
    
    desc_lower = desc.lower()
    
    # Extract session
    # Feb -> S1, Mar -> S2, Jul -> S3, Aug -> S4 (for 2021)
    # Jan/Feb/Jun -> S1, Apr/Jul/Sep -> S2 (for other years)
    session = "S1"
    if year == 2021:
        if "feb" in desc_lower:
            session = "S1"
        elif "mar" in desc_lower:
            session = "S2"
        elif "jul" in desc_lower:
            session = "S3"
        elif "aug" in desc_lower:
            session = "S4"
        elif "sep" in desc_lower:
            session = "S4"
    else:
        if any(m in desc_lower for m in ["apr", "jul", "sep", "aug"]):
            session = "S2"
        elif any(m in desc_lower for m in ["jan", "feb", "jun"]):
            session = "S1"
            
    shift = 1
    shift_match = re.search(r'shift\s*(\d+)', desc_lower)
    if shift_match:
        shift = int(shift_match.group(1))
    elif "evening" in desc_lower:
        shift = 2
    elif "morning" in desc_lower:
        shift = 1
        
    return year, session, shift

def find_allen_urls(html: str, target_years: list[int]) -> list[str]:
    """Finds year-specific URLs on the main Allen page."""
    soup = BeautifulSoup(html, 'html.parser')
    urls = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        for year in target_years:
            if str(year) in href and any(kw in href for kw in ["question-paper", "question-papers", "answer-key"]):
                full_url = href if href.startswith("http") else f"https://allen.in/{href.lstrip('/')}"
                urls.append(full_url)
    return list(set(urls))

def parse_allen_payloads(html: str, target_year: int, logger: logging.Logger) -> dict:
    """Parses Allen's base64 actions and groups subject PDFs by date and shift."""
    matches = re.findall(r'data-action="([A-Za-z0-9+/=]+)"', html)
    if not matches:
        matches = re.findall(r'data-action=\\?"([A-Za-z0-9+/=]+)\\?"', html)
        
    groups = {}
    for m in matches:
        try:
            decoded = base64.b64decode(m).decode('utf-8')
            payload = json.loads(decoded)
            if payload.get("type") == "DOWNLOAD_FILE":
                data = payload.get("data", {})
                filename = data.get("filename", "")
                uri = data.get("uri", "")
                if not filename or not uri or not uri.endswith(".pdf"):
                    continue
                    
                filename_lower = filename.lower()
                
                subject = None
                if "physic" in filename_lower:
                    subject = "Physics"
                elif "chemist" in filename_lower:
                    subject = "Chemistry"
                elif "math" in filename_lower:
                    subject = "Mathematics"
                    
                if not subject:
                    continue
                    
                shift = 1
                if "evening" in filename_lower:
                    shift = 2
                elif "morning" in filename_lower:
                    shift = 1
                    
                date_match = re.search(r'\b(\d{4})\b', filename)
                if not date_match:
                    date_match = re.search(r'^(\d{4})', filename)
                if not date_match:
                    date_match = re.search(r'(\d{4})', uri)
                    
                if not date_match:
                    continue
                    
                date_str = date_match.group(1)
                
                session = "S1"
                uri_lower = uri.lower()
                if any(m in uri_lower or m in filename_lower for m in ["apr", "april", "jul", "july", "sep", "sept", "aug"]):
                    session = "S2"
                elif any(m in uri_lower or m in filename_lower for m in ["jan", "january", "feb", "february", "jun", "june"]):
                    session = "S1"
                    
                group_key = (target_year, session, date_str, shift)
                if group_key not in groups:
                    groups[group_key] = {}
                groups[group_key][subject] = uri
        except Exception:
            pass
            
    return groups

async def merge_allen_group(client: httpx.AsyncClient, key: tuple, subjects: dict, dest: Path, logger: logging.Logger, temp_dir: Path) -> bool:
    """Downloads shift subjects separately and merges them using PyMuPDF (fitz)."""
    year, session, date_str, shift = key
    logger.info(f"Merging subjects for JEE Main {year} S{session} Shift {shift} (Date: {date_str})")
    
    downloaded_paths = []
    subject_order = ["Physics", "Chemistry", "Mathematics"]
    
    for sub in subject_order:
        if sub in subjects:
            uri = subjects[sub]
            temp_file = temp_dir / f"{year}_{session}_{date_str}_shift{shift}_{sub}.pdf"
            success = await download_file(client, uri, temp_file, logger)
            if success and temp_file.exists():
                downloaded_paths.append(temp_file)
                
    if not downloaded_paths:
        logger.warning(f"No subjects successfully downloaded for JEE Main {year} S{session} Shift {shift}.")
        return False
        
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        
        doc = fitz.open()
        for p in downloaded_paths:
            with fitz.open(str(p)) as sub_doc:
                doc.insert_pdf(sub_doc)
        doc.save(str(dest))
        doc.close()
        logger.info(f"Successfully created merged PDF: {dest}")
        
        # Clean up temp files
        for p in downloaded_paths:
            try:
                p.unlink()
            except Exception:
                pass
        return True
    except Exception as e:
        logger.error(f"Error merging PDFs for {dest.name}: {e}")
        for p in downloaded_paths:
            try:
                p.unlink()
            except Exception:
                pass
        return False

async def scrape_jeeadv(client: httpx.AsyncClient, years: list[int], adv_dir: Path, logger: logging.Logger) -> int:
    """Scrapes JEE Advanced papers from official archive page, falling back to direct URLs."""
    logger.info("Starting official JEE Advanced scraping from jeeadv.ac.in/archive.html")
    download_count = 0
    
    html = await fetch_page(client, "https://jeeadv.ac.in/archive.html", logger)
    if html:
        soup = BeautifulSoup(html, "html.parser")
        links = soup.find_all("a", href=True)
        logger.info(f"Found {len(links)} links on jeeadv.ac.in/archive.html")
        
        for link in links:
            href = link["href"]
            for year in years:
                for paper in [1, 2]:
                    if str(year) in href and f"_{paper}" in href and href.endswith(".pdf"):
                        if year >= 2019 and "english" not in href.lower():
                            continue
                        full_url = href if href.startswith("http") else f"https://jeeadv.ac.in/{href.lstrip('/')}"
                        filename = f"JEE_ADV_{year}_P{paper}.pdf"
                        dest_path = adv_dir / filename
                        
                        if dest_path.exists() and dest_path.stat().st_size > 10240:
                            continue
                            
                        resolved_url = await resolve_download_url(client, full_url, logger)
                        success = await download_file(client, resolved_url, dest_path, logger)
                        if success:
                            download_count += 1
                            
    # Fallback to direct URL constructs if papers are missing
    for year in years:
        for paper in [1, 2]:
            filename = f"JEE_ADV_{year}_P{paper}.pdf"
            dest_path = adv_dir / filename
            if not dest_path.exists() or dest_path.stat().st_size <= 10240:
                logger.info(f"Direct URL fallback for JEE Advanced {year} Paper {paper}")
                if year >= 2019:
                    direct_url = f"https://jeeadv.ac.in/past_qps/{year}_{paper}_English.pdf"
                else:
                    direct_url = f"https://jeeadv.ac.in/past_qps/{year}_{paper}.pdf"
                    
                resolved_url = await resolve_download_url(client, direct_url, logger)
                success = await download_file(client, resolved_url, dest_path, logger)
                if success:
                    download_count += 1
                    
    return download_count

async def scrape_jeemain(client: httpx.AsyncClient, years: list[int], main_dir: Path, logger: logging.Logger, temp_dir: Path) -> int:
    """Scrapes JEE Main papers from official page check, falling back to MathonGo and Allen mirrors."""
    logger.info("Starting JEE Main scraping...")
    download_count = 0
    
    # Official NTA downloads landing page check
    logger.info("Checking nta.ac.in/Downloads...")
    nta_html = await fetch_page(client, "https://nta.ac.in/Downloads", logger)
    if nta_html:
        logger.info("nta.ac.in/Downloads fetched. Direct paper links are not exposed on this landing page. Moving to fallback mirrors.")
        
    # MathonGo Fallback
    logger.info("Checking MathonGo previous year question papers page...")
    mathongo_urls = [
        "https://mathongo.com/jee-main-previous-year-question-papers",
        "https://www.mathongo.com/iit-jee/jee-main-previous-year-question-paper"
    ]
    mathongo_html = None
    for m_url in mathongo_urls:
        mathongo_html = await fetch_page(client, m_url, logger)
        if mathongo_html:
            logger.info(f"Successfully fetched MathonGo page from: {m_url}")
            break
            
    if mathongo_html:
        soup = BeautifulSoup(mathongo_html, "html.parser")
        for h3 in soup.find_all('h3'):
            title = h3.get_text(strip=True)
            if "JEE Main" not in title or "Previous Year" not in title:
                continue
                
            year_match = re.search(r'\b(201[5-9]|202[0-5])\b', title)
            if not year_match:
                continue
            year = int(year_match.group(1))
            
            if year not in years:
                continue
                
            logger.info(f"Scraping MathonGo section: {title} (Year: {year})")
            
            sibling = h3.next_sibling
            while sibling:
                if sibling.name in ['h2', 'h3']:
                    break
                table = None
                if sibling.name == 'table':
                    table = sibling
                elif sibling.name == 'figure':
                    table = sibling.find('table')
                    
                if table:
                    rows = table.find_all('tr')
                    for row in rows[1:]:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            paper_name = cols[1].get_text(strip=True)
                            a = cols[2].find('a', href=True)
                            if a:
                                parsed = parse_mathongo_desc(paper_name, year)
                                if parsed:
                                    pyear, psession, pshift = parsed
                                    if pyear == year:
                                        filename = f"JEE_MAIN_{pyear}_{psession}_Shift{pshift}.pdf"
                                        dest_path = main_dir / filename
                                        
                                        if dest_path.exists() and dest_path.stat().st_size > 10240:
                                            continue
                                            
                                        resolved_url = await resolve_download_url(client, a['href'], logger)
                                        success = await download_file(client, resolved_url, dest_path, logger)
                                        if success:
                                            download_count += 1
                sibling = sibling.next_sibling
                
    # Allen Fallback
    logger.info("Checking Allen previous year papers page...")
    allen_main_url = "https://allen.in/jee-main/previous-year-papers"
    allen_html = await fetch_page(client, allen_main_url, logger)
    
    allen_year_urls = []
    if allen_html:
        allen_year_urls = find_allen_urls(allen_html, years)
        logger.info(f"Found {len(allen_year_urls)} year URLs on Allen main page.")
        
    # Standard fallback URLs for Allen
    default_allen_urls = {
        2024: [
            "https://www.allen.in/jee-main/question-papers-2024",
            "https://www.allen.in/jee-main/january-2024-question-paper-with-solutions",
            "https://www.allen.in/jee-main/april-2024-question-paper-with-solutions"
        ],
        2023: ["https://www.allen.in/jee-main/answer-key-2023"],
        2022: ["https://www.allen.in/jee-main/question-paper-2022"],
        2021: ["https://www.allen.in/jee-main/question-paper-2021"],
        2020: ["https://www.allen.in/jee-main/question-paper-2020"]
    }
    for year in years:
        if year in default_allen_urls:
            allen_year_urls.extend(default_allen_urls[year])
            
    allen_year_urls = list(set(allen_year_urls))
    
    for allen_url in allen_year_urls:
        year_match = re.search(r'\b(201[5-9]|202[0-5])\b', allen_url)
        if not year_match:
            continue
        year = int(year_match.group(1))
        if year not in years:
            continue
            
        logger.info(f"Fetching Allen page: {allen_url} for Year {year}")
        page_html = await fetch_page(client, allen_url, logger)
        if page_html:
            groups = parse_allen_payloads(page_html, year, logger)
            logger.info(f"Parsed {len(groups)} shift groups from {allen_url}")
            for key, subjects in groups.items():
                pyear, psession, pdate_str, pshift = key
                filename = f"JEE_MAIN_{pyear}_{psession}_Shift{pshift}.pdf"
                dest_path = main_dir / filename
                
                if dest_path.exists() and dest_path.stat().st_size > 10240:
                    continue
                    
                success = await merge_allen_group(client, key, subjects, dest_path, logger, temp_dir)
                if success:
                    download_count += 1
                    
    return download_count

async def main_async() -> None:
    parser = argparse.ArgumentParser(description="Robust JEE Question Paper Scraper.")
    parser.add_argument("--years", type=str, default="2018-2024", help="Year range, e.g., 2018-2024")
    parser.add_argument("--exams", type=str, default="both", choices=["main", "advanced", "both"], help="Exams: main, advanced, both")
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent
    log_dir = project_root / "logs"
    scraper_log = log_dir / "scraper.log"
    
    logger = setup_logging(scraper_log)
    logger.info("=== JEE SCRAPER EXECUTION START ===")
    
    try:
        if "-" in args.years:
            start_year, end_year = map(int, args.years.split("-"))
        else:
            start_year = end_year = int(args.years)
    except ValueError:
        logger.warning(f"Invalid year range: {args.years}. Defaulting to 2018-2024.")
        start_year, end_year = 2018, 2024
        
    years = list(range(start_year, end_year + 1))
    logger.info(f"Targeting years: {years}")
    logger.info(f"Targeting exams: {args.exams}")
    
    papers_dir = project_root / "papers"
    main_dir = papers_dir / "main"
    adv_dir = papers_dir / "advanced"
    temp_dir = papers_dir / "tmp"
    
    main_dir.mkdir(parents=True, exist_ok=True)
    adv_dir.mkdir(parents=True, exist_ok=True)
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    count_main = 0
    count_adv = 0
    
    async with httpx.AsyncClient(follow_redirects=True) as client:
        if args.exams in ["advanced", "both"]:
            count_adv = await scrape_jeeadv(client, years, adv_dir, logger)
            
        if args.exams in ["main", "both"]:
            count_main = await scrape_jeemain(client, years, main_dir, logger, temp_dir)
            
    # Clean up temp folder
    try:
        if temp_dir.exists():
            for f in temp_dir.glob("*"):
                f.unlink()
            temp_dir.rmdir()
    except Exception as e:
        logger.warning(f"Error cleaning up temp directory {temp_dir}: {e}")
        
    logger.info("=== SCRAPING SUMMARY ===")
    logger.info(f"JEE Main papers downloaded/merged: {count_main}")
    logger.info(f"JEE Advanced papers downloaded: {count_adv}")
    logger.info("=== JEE SCRAPER EXECUTION SUCCESSFUL ===")

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main_async())
