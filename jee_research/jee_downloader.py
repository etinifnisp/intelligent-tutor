"""
JEE Mains & Advanced — Complete Paper Downloader
=================================================
Downloads all JEE Advanced papers (direct PDF) and JEE Mains papers (scraped from Vedantu).

Usage:
    pip install requests beautifulsoup4 playwright
    playwright install chromium

    # Download everything:
    python jee_downloader.py

    # Download only Advanced:
    python jee_downloader.py --only-advanced

    # Download only Mains:
    python jee_downloader.py --only-mains

    # Dry run (print links without downloading):
    python jee_downloader.py --dry-run

Output folder structure:
    JEE_Papers/
    ├── Advanced/
    │   ├── 2016/
    │   │   ├── JEE_Advanced_2016_Paper1_English.pdf
    │   │   └── JEE_Advanced_2016_Paper2_English.pdf
    │   ├── 2017/ ...
    │   └── AAT/
    │       ├── JEE_Advanced_AAT_2016.pdf
    │       └── ...
    └── Mains/
        ├── 2016/
        │   └── JEE_Main_2016.pdf
        ├── 2024/
        │   ├── Session1_Jan/
        │   │   ├── JEE_Main_2024_Jan27_Shift1.pdf
        │   │   └── ...
        │   └── Session2_Apr/
        │       └── ...
        └── ...
"""

import os
import re
import time
import argparse
import requests
from pathlib import Path
from urllib.parse import urljoin

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OUTPUT_DIR = Path("JEE_Papers")
DELAY_BETWEEN_REQUESTS = 1.5   # seconds — be polite to servers
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/pdf,text/html,*/*",
}

# ─────────────────────────────────────────────
# PART 1: JEE ADVANCED — DIRECT PDF LINKS
# Source: jeeadv.ac.in/archive.html (official)
# ─────────────────────────────────────────────
JEE_ADVANCED_PAPERS = {
    # year: { label: url }
    2016: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2016_1.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2016_2.pdf",
    },
    2017: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2017_1.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2017_2.pdf",
    },
    2018: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2018_1.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2018_2.pdf",
    },
    2019: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2019_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2019_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2019_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2019_2_Hindi.pdf",
    },
    2020: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2020_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2020_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2020_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2020_2_Hindi.pdf",
    },
    2021: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2021_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2021_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2021_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2021_2_Hindi.pdf",
    },
    2022: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2022_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2022_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2022_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2022_2_Hindi.pdf",
    },
    2023: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2023_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2023_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2023_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2023_2_Hindi.pdf",
    },
    2024: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2024_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2024_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2024_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2024_2_Hindi.pdf",
    },
    2025: {
        "Paper1_English": "https://jeeadv.ac.in/past_qps/2025_1_English.pdf",
        "Paper2_English": "https://jeeadv.ac.in/past_qps/2025_2_English.pdf",
        "Paper1_Hindi":   "https://jeeadv.ac.in/past_qps/2025_1_Hindi.pdf",
        "Paper2_Hindi":   "https://jeeadv.ac.in/past_qps/2025_2_Hindi.pdf",
    },
}

JEE_ADVANCED_AAT = {
    year: f"https://jeeadv.ac.in/past_qps/AAT-{year}.pdf"
    for year in range(2016, 2026)
}

# ─────────────────────────────────────────────
# PART 2: JEE MAINS — VEDANTU PAGE LINKS
# These pages contain embedded PDF download links
# that we scrape using BeautifulSoup / Playwright
# ─────────────────────────────────────────────

# Structure: (year, session_label, date_label, shift) -> vedantu_url
JEE_MAINS_PAGES = [
    # ── 2025 Session 1 (January) ──
    (2025, "Session1_Jan", "Jan22", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-22-january-shift-1"),
    (2025, "Session1_Jan", "Jan22", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-22-january-shift-2"),
    (2025, "Session1_Jan", "Jan23", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-23-january-shift-1"),
    (2025, "Session1_Jan", "Jan23", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-23-january-shift-2"),
    (2025, "Session1_Jan", "Jan24", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-24-january-shift-1"),
    (2025, "Session1_Jan", "Jan24", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-24-january-shift-2"),
    (2025, "Session1_Jan", "Jan28", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-28-january-shift-1"),
    (2025, "Session1_Jan", "Jan28", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-28-january-shift-2"),
    (2025, "Session1_Jan", "Jan29", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-29-january-shift-1"),
    (2025, "Session1_Jan", "Jan29", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-29-january-shift-2"),
    # ── 2025 Session 2 (April) ──
    (2025, "Session2_Apr", "Apr02", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-2-april-shift-1"),
    (2025, "Session2_Apr", "Apr02", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-2-april-shift-2"),
    (2025, "Session2_Apr", "Apr03", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-3-april-shift-1"),
    (2025, "Session2_Apr", "Apr03", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-3-april-shift-2"),
    (2025, "Session2_Apr", "Apr04", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-4-april-shift-1"),
    (2025, "Session2_Apr", "Apr04", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-4-april-shift-2"),
    (2025, "Session2_Apr", "Apr07", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-7-april-shift-1"),
    (2025, "Session2_Apr", "Apr07", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-7-april-shift-2"),
    (2025, "Session2_Apr", "Apr08", "Shift1", "https://www.vedantu.com/jee-main/2025-question-paper-8-april-shift-1"),
    (2025, "Session2_Apr", "Apr08", "Shift2", "https://www.vedantu.com/jee-main/2025-question-paper-8-april-shift-2"),
    # ── 2024 Session 1 (January–February) ──
    (2024, "Session1_Jan", "Jan27", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-27-january-shift-1"),
    (2024, "Session1_Jan", "Jan27", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-27-january-shift-2"),
    (2024, "Session1_Jan", "Jan29", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-29-january-shift-1"),
    (2024, "Session1_Jan", "Jan29", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-29-january-shift-2"),
    (2024, "Session1_Jan", "Jan30", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-30-january-shift-1"),
    (2024, "Session1_Jan", "Jan30", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-30-january-shift-2"),
    (2024, "Session1_Jan", "Jan31", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-31-january-shift-1"),
    (2024, "Session1_Jan", "Jan31", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-31-january-shift-2"),
    (2024, "Session1_Jan", "Feb01", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-1-february-shift-1"),
    (2024, "Session1_Jan", "Feb01", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-1-february-shift-2"),
    # ── 2024 Session 2 (April) ──
    (2024, "Session2_Apr", "Apr04", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-4-april-shift-1"),
    (2024, "Session2_Apr", "Apr04", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-4-april-shift-2"),
    (2024, "Session2_Apr", "Apr05", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-5-april-shift-1"),
    (2024, "Session2_Apr", "Apr05", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-5-april-shift-2"),
    (2024, "Session2_Apr", "Apr06", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-6-april-shift-1"),
    (2024, "Session2_Apr", "Apr06", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-6-april-shift-2"),
    (2024, "Session2_Apr", "Apr08", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-8-april-shift-1"),
    (2024, "Session2_Apr", "Apr08", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-8-april-shift-2"),
    (2024, "Session2_Apr", "Apr09", "Shift1", "https://www.vedantu.com/jee-main/2024-question-paper-9-april-shift-1"),
    (2024, "Session2_Apr", "Apr09", "Shift2", "https://www.vedantu.com/jee-main/2024-question-paper-9-april-shift-2"),
    # ── 2023 Session 1 (January) ──
    (2023, "Session1_Jan", "Jan24", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-24-january-shift-1"),
    (2023, "Session1_Jan", "Jan24", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-24-january-shift-2"),
    (2023, "Session1_Jan", "Jan25", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-25-january-shift-1"),
    (2023, "Session1_Jan", "Jan25", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-25-january-shift-2"),
    (2023, "Session1_Jan", "Jan29", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-29-january-shift-1"),
    (2023, "Session1_Jan", "Jan29", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-29-january-shift-2"),
    (2023, "Session1_Jan", "Jan30", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-30-january-shift-1"),
    (2023, "Session1_Jan", "Jan30", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-30-january-shift-2"),
    (2023, "Session1_Jan", "Jan31", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-31-january-shift-1"),
    (2023, "Session1_Jan", "Jan31", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-31-january-shift-2"),
    # ── 2023 Session 2 (April) ──
    (2023, "Session2_Apr", "Apr06", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-6-april-shift-1"),
    (2023, "Session2_Apr", "Apr06", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-6-april-shift-2"),
    (2023, "Session2_Apr", "Apr08", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-8-april-shift-1"),
    (2023, "Session2_Apr", "Apr08", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-8-april-shift-2"),
    (2023, "Session2_Apr", "Apr10", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-10-april-shift-1"),
    (2023, "Session2_Apr", "Apr10", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-10-april-shift-2"),
    (2023, "Session2_Apr", "Apr11", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-11-april-shift-1"),
    (2023, "Session2_Apr", "Apr11", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-11-april-shift-2"),
    (2023, "Session2_Apr", "Apr12", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-12-april-shift-1"),
    (2023, "Session2_Apr", "Apr12", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-12-april-shift-2"),
    (2023, "Session2_Apr", "Apr13", "Shift1", "https://www.vedantu.com/jee-main/2023-question-paper-13-april-shift-1"),
    (2023, "Session2_Apr", "Apr13", "Shift2", "https://www.vedantu.com/jee-main/2023-question-paper-13-april-shift-2"),
    # ── 2022 Session 1 (June) ──
    (2022, "Session1_Jun", "Jun23", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-23-june-shift-1"),
    (2022, "Session1_Jun", "Jun23", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-23-june-shift-2"),
    (2022, "Session1_Jun", "Jun24", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-24-june-shift-1"),
    (2022, "Session1_Jun", "Jun24", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-24-june-shift-2"),
    (2022, "Session1_Jun", "Jun25", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-25-june-shift-1"),
    (2022, "Session1_Jun", "Jun25", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-25-june-shift-2"),
    (2022, "Session1_Jun", "Jun26", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-26-june-shift-1"),
    (2022, "Session1_Jun", "Jun26", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-26-june-shift-2"),
    # ── 2022 Session 2 (July) ──
    (2022, "Session2_Jul", "Jul25", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-25-july-shift-1"),
    (2022, "Session2_Jul", "Jul25", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-25-july-shift-2"),
    (2022, "Session2_Jul", "Jul26", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-26-july-shift-1"),
    (2022, "Session2_Jul", "Jul26", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-26-july-shift-2"),
    (2022, "Session2_Jul", "Jul27", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-27-july-shift-1"),
    (2022, "Session2_Jul", "Jul27", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-27-july-shift-2"),
    (2022, "Session2_Jul", "Jul28", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-28-july-shift-1"),
    (2022, "Session2_Jul", "Jul28", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-28-july-shift-2"),
    (2022, "Session2_Jul", "Jul29", "Shift1", "https://www.vedantu.com/jee-main/2022-question-paper-29-july-shift-1"),
    (2022, "Session2_Jul", "Jul29", "Shift2", "https://www.vedantu.com/jee-main/2022-question-paper-29-july-shift-2"),
    # ── 2021 Session 1 (February) ──
    (2021, "Session1_Feb", "Feb24", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-24-february-shift-1"),
    (2021, "Session1_Feb", "Feb24", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-24-february-shift-2"),
    (2021, "Session1_Feb", "Feb25", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-25-february-shift-1"),
    (2021, "Session1_Feb", "Feb25", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-25-february-shift-2"),
    (2021, "Session1_Feb", "Feb26", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-26-february-shift-1"),
    (2021, "Session1_Feb", "Feb26", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-26-february-shift-2"),
    # ── 2021 Session 2 (March) ──
    (2021, "Session2_Mar", "Mar16", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-16-march-shift-1"),
    (2021, "Session2_Mar", "Mar16", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-16-march-shift-2"),
    (2021, "Session2_Mar", "Mar17", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-17-march-shift-1"),
    (2021, "Session2_Mar", "Mar17", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-17-march-shift-2"),
    (2021, "Session2_Mar", "Mar18", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-18-march-shift-1"),
    (2021, "Session2_Mar", "Mar18", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-18-march-shift-2"),
    # ── 2021 Session 3 (July) ──
    (2021, "Session3_Jul", "Jul20", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-20-july-shift-1"),
    (2021, "Session3_Jul", "Jul20", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-20-july-shift-2"),
    (2021, "Session3_Jul", "Jul22", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-22-july-shift-1"),
    (2021, "Session3_Jul", "Jul22", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-22-july-shift-2"),
    (2021, "Session3_Jul", "Jul25", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-25-july-shift-1"),
    (2021, "Session3_Jul", "Jul25", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-25-july-shift-2"),
    (2021, "Session3_Jul", "Jul27", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-27-july-shift-1"),
    (2021, "Session3_Jul", "Jul27", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-27-july-shift-2"),
    # ── 2021 Session 4 (August–September) ──
    (2021, "Session4_Aug", "Aug26", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-26-august-shift-1"),
    (2021, "Session4_Aug", "Aug26", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-26-august-shift-2"),
    (2021, "Session4_Aug", "Aug27", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-27-august-shift-1"),
    (2021, "Session4_Aug", "Aug27", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-27-august-shift-2"),
    (2021, "Session4_Aug", "Aug31", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-31-august-shift-1"),
    (2021, "Session4_Aug", "Aug31", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-31-august-shift-2"),
    (2021, "Session4_Aug", "Sep01", "Shift1", "https://www.vedantu.com/jee-main/2021-question-paper-1-september-shift-1"),
    (2021, "Session4_Aug", "Sep01", "Shift2", "https://www.vedantu.com/jee-main/2021-question-paper-1-september-shift-2"),
    # ── 2020 (September, COVID rescheduled) ──
    (2020, "Session1_Sep", "Sep01", "Shift1", "https://www.vedantu.com/jee-main/2020-question-paper-1-september-shift-1"),
    (2020, "Session1_Sep", "Sep01", "Shift2", "https://www.vedantu.com/jee-main/2020-question-paper-1-september-shift-2"),
    (2020, "Session1_Sep", "Sep02", "Shift1", "https://www.vedantu.com/jee-main/2020-question-paper-2-september-shift-1"),
    (2020, "Session1_Sep", "Sep02", "Shift2", "https://www.vedantu.com/jee-main/2020-question-paper-2-september-shift-2"),
    (2020, "Session1_Sep", "Sep03", "Shift1", "https://www.vedantu.com/jee-main/2020-question-paper-3-september-shift-1"),
    (2020, "Session1_Sep", "Sep03", "Shift2", "https://www.vedantu.com/jee-main/2020-question-paper-3-september-shift-2"),
    # ── 2019 Session 1 (January) ──
    (2019, "Session1_Jan", "Jan09", "Shift1", "https://www.vedantu.com/jee-main/2019-question-paper-9-january-shift-1"),
    (2019, "Session1_Jan", "Jan09", "Shift2", "https://www.vedantu.com/jee-main/2019-question-paper-9-january-shift-2"),
    (2019, "Session1_Jan", "Jan10", "Shift1", "https://www.vedantu.com/jee-main/2019-question-paper-10-january-shift-1"),
    (2019, "Session1_Jan", "Jan10", "Shift2", "https://www.vedantu.com/jee-main/2019-question-paper-10-january-shift-2"),
    # ── 2019 Session 2 (April) ──
    (2019, "Session2_Apr", "Apr08", "Shift1", "https://www.vedantu.com/jee-main/2019-question-paper-8-april-shift-1"),
    (2019, "Session2_Apr", "Apr08", "Shift2", "https://www.vedantu.com/jee-main/2019-question-paper-8-april-shift-2"),
    (2019, "Session2_Apr", "Apr09", "Shift1", "https://www.vedantu.com/jee-main/2019-question-paper-9-april-shift-1"),
    (2019, "Session2_Apr", "Apr09", "Shift2", "https://www.vedantu.com/jee-main/2019-question-paper-9-april-shift-2"),
    # ── 2018 (single session) ──
    (2018, "Session1", "Paper", "Full", "https://www.vedantu.com/jee-main/2018-question-paper"),
    # ── 2017 (single session) ──
    (2017, "Session1", "Paper", "Full", "https://www.vedantu.com/jee-main/2017-question-paper"),
    # ── 2016 (single session) ──
    (2016, "Session1", "Paper", "Full", "https://www.vedantu.com/jee-main/2016-question-paper"),
]


# ─────────────────────────────────────────────
# DOWNLOADER UTILITIES
# ─────────────────────────────────────────────

def download_pdf(url: str, dest_path: Path, dry_run: bool = False) -> bool:
    """Download a PDF from a direct URL. Returns True on success."""
    if dest_path.exists():
        print(f"  [OK] Already exists: {dest_path.name}")
        return True
    if dry_run:
        print(f"  [DRY RUN] Would download: {url}")
        print(f"         -> {dest_path}")
        return True

    dest_path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT, stream=True)
            resp.raise_for_status()
            content_type = resp.headers.get("Content-Type", "")
            if "pdf" not in content_type and "octet-stream" not in content_type:
                print(f"  [WARN] Not a PDF (Content-Type: {content_type}): {url}")
                return False
            with open(dest_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
            size_kb = dest_path.stat().st_size // 1024
            print(f"  [OK] Downloaded ({size_kb} KB): {dest_path.name}")
            return True
        except requests.RequestException as e:
            print(f"  [WARN] Attempt {attempt}/{MAX_RETRIES} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
    print(f"  [FAIL] Failed after {MAX_RETRIES} attempts: {url}")
    return False


def scrape_pdf_from_vedantu(page_url: str, dry_run: bool = False) -> str | None:
    """
    Strategy 1: requests + BeautifulSoup to find PDF links in <a> tags.
    Strategy 2: Playwright (headless browser) if Strategy 1 fails — handles JS-rendered links.
    Returns the direct PDF URL or None.
    """
    # ── Strategy 1: Static scrape ──
    try:
        resp = requests.get(page_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, "html.parser")

        # Look for <a> tags with .pdf in href
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if ".pdf" in href.lower():
                pdf_url = href if href.startswith("http") else urljoin(page_url, href)
                return pdf_url

        # Look for PDF links in script tags (some sites embed them in JSON)
        scripts = soup.find_all("script")
        for script in scripts:
            if script.string:
                matches = re.findall(r'https?://[^\s"\']+\.pdf', script.string)
                if matches:
                    return matches[0]

    except Exception as e:
        print(f"  [WARN] Static scrape failed: {e}")

    # ── Strategy 2: Playwright (JS-rendered) ──
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            pdf_urls = []

            def capture_response(response):
                if ".pdf" in response.url.lower():
                    pdf_urls.append(response.url)

            page.on("response", capture_response)
            page.goto(page_url, wait_until="networkidle", timeout=30000)

            # Look for download links in rendered DOM
            links = page.eval_on_selector_all(
                "a[href*='.pdf'], a[href*='download']",
                "els => els.map(el => el.href)"
            )
            browser.close()

            if pdf_urls:
                return pdf_urls[0]
            if links:
                return links[0]

    except Exception as e:
        print(f"  [WARN] Playwright scrape failed: {e}")

    return None


# ─────────────────────────────────────────────
# MAIN DOWNLOAD ROUTINES
# ─────────────────────────────────────────────

def download_jee_advanced(dry_run: bool = False):
    print("\n" + "=" * 60)
    print("  JEE ADVANCED - Direct PDF Downloads")
    print("  Source: jeeadv.ac.in (Official)")
    print("=" * 60)

    success, fail = 0, 0

    # Main papers
    for year, papers in sorted(JEE_ADVANCED_PAPERS.items()):
        print(f"\n> JEE Advanced {year}")
        year_dir = OUTPUT_DIR / "Advanced" / str(year)
        for label, url in papers.items():
            filename = f"JEE_Advanced_{year}_{label}.pdf"
            dest = year_dir / filename
            ok = download_pdf(url, dest, dry_run)
            if ok:
                success += 1
            else:
                fail += 1
            time.sleep(DELAY_BETWEEN_REQUESTS)

    # AAT papers
    print(f"\n> JEE Advanced AAT Papers")
    aat_dir = OUTPUT_DIR / "Advanced" / "AAT"
    for year, url in sorted(JEE_ADVANCED_AAT.items()):
        filename = f"JEE_Advanced_AAT_{year}.pdf"
        dest = aat_dir / filename
        ok = download_pdf(url, dest, dry_run)
        if ok:
            success += 1
        else:
            fail += 1
        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  JEE Advanced: [OK] {success} downloaded, [FAIL] {fail} failed")
    return success, fail


def download_jee_mains(dry_run: bool = False):
    print("\n" + "=" * 60)
    print("  JEE MAINS - Scraped from Vedantu")
    print("  (Scrapes each page to find direct PDF link)")
    print("=" * 60)

    success, fail, skipped = 0, 0, 0
    failed_pages = []

    for (year, session, date_label, shift, page_url) in JEE_MAINS_PAGES:
        filename = f"JEE_Main_{year}_{date_label}_{shift}.pdf"
        dest = OUTPUT_DIR / "Mains" / str(year) / session / filename

        if dest.exists():
            print(f"  [OK] Already exists: {filename}")
            skipped += 1
            continue

        print(f"\n> {year} | {session} | {date_label} | {shift}")
        print(f"  Scraping: {page_url}")

        if dry_run:
            print(f"  [DRY RUN] Would scrape and download -> {dest}")
            skipped += 1
            continue

        pdf_url = scrape_pdf_from_vedantu(page_url, dry_run)

        if pdf_url:
            print(f"  Found PDF: {pdf_url}")
            ok = download_pdf(pdf_url, dest, dry_run)
            if ok:
                success += 1
            else:
                fail += 1
                failed_pages.append((filename, page_url))
        else:
            print(f"  [FAIL] No PDF found on page: {page_url}")
            fail += 1
            failed_pages.append((filename, page_url))

        time.sleep(DELAY_BETWEEN_REQUESTS)

    print(f"\n  JEE Mains: [OK] {success} downloaded, [FAIL] {fail} failed, [SKIP] {skipped} skipped")

    if failed_pages:
        print("\n  -- Failed pages (manual download needed) --")
        for name, url in failed_pages:
            print(f"  {name}: {url}")

    return success, fail


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Download all JEE Mains & Advanced papers (2016-2025)"
    )
    parser.add_argument("--only-advanced", action="store_true", help="Download only JEE Advanced")
    parser.add_argument("--only-mains", action="store_true", help="Download only JEE Mains")
    parser.add_argument("--dry-run", action="store_true", help="Print links without downloading")
    parser.add_argument("--output-dir", default="JEE_Papers", help="Output directory (default: JEE_Papers)")
    args = parser.parse_args()

    global OUTPUT_DIR
    OUTPUT_DIR = Path(args.output_dir)

    print("+----------------------------------------------------------+")
    print("|     JEE Papers Downloader - 2016 to 2025                 |")
    print("|     JEE Advanced: ~44 PDFs (official jeeadv.ac.in)       |")
    print("|     JEE Mains:   ~110 PDFs (scraped from Vedantu)        |")
    print("+----------------------------------------------------------+")
    if args.dry_run:
        print("\n  [WARN] DRY RUN MODE - no files will be downloaded\n")

    total_success, total_fail = 0, 0

    if not args.only_mains:
        s, f = download_jee_advanced(dry_run=args.dry_run)
        total_success += s
        total_fail += f

    if not args.only_advanced:
        s, f = download_jee_mains(dry_run=args.dry_run)
        total_success += s
        total_fail += f

    print("\n" + "=" * 60)
    print(f"  TOTAL: [OK] {total_success} downloaded, [FAIL] {total_fail} failed")
    print(f"  Output directory: {OUTPUT_DIR.resolve()}")
    print("=" * 60)


if __name__ == "__main__":
    main()
