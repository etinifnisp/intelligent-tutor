import httpx
from bs4 import BeautifulSoup
import re

url = "https://www.mathongo.com/iit-jee/jee-main-previous-year-question-paper"
r = httpx.get(url)
soup = BeautifulSoup(r.text, 'html.parser')

sections = {}
for h3 in soup.find_all('h3'):
    title = h3.text.strip()
    sections[title] = []
    
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
                    paper_name = cols[1].text.strip()
                    a = cols[2].find('a', href=True)
                    link = a['href'] if a else None
                    sections[title].append((paper_name, link))
        sibling = sibling.next_sibling

# The 12 failed papers to check
failed_targets = [
    ("2025", "Apr 08", "Shift 1"),
    ("2023", "Apr 12", "Shift 2"),
    ("2022", "Jun 23", "Shift 1"),
    ("2022", "Jun 23", "Shift 2"),
    ("2021", "Jul 22", "Shift 1"),
    ("2021", "Sep 01", "Shift 1"),
    ("2021", "Sep 01", "Shift 2"),
    ("2020", "Sep 01", "Shift 1"),
    ("2020", "Sep 01", "Shift 2"),
    ("2018", "Full", "Paper"),
    ("2017", "Full", "Paper"),
    ("2016", "Full", "Paper")
]

print("--- MATHONGO SCANNED MATCHES ---")
for t_year, t_date, t_shift in failed_targets:
    found = False
    for title, rows in sections.items():
        # check if year is in section title
        if t_year in title:
            # For 2021 September, it might be in August section
            # For 2020 September, it might be in September section
            for paper_name, link in rows:
                p_name_lower = paper_name.lower()
                
                # Check for match
                if t_year in ["2018", "2017", "2016"]:
                    if "offline" in p_name_lower or "online" in p_name_lower or "question paper" in p_name_lower:
                        print(f"Match found for {t_year} {t_date} {t_shift}: '{paper_name}' -> {link}")
                        found = True
                else:
                    # check date and shift
                    # date: remove spaces
                    t_date_clean = t_date.replace(" ", "").lower()
                    # e.g. "apr08" or "08apr"
                    # shift: e.g. "shift1" or "shift 1"
                    t_shift_clean = t_shift.replace(" ", "").lower()
                    
                    p_name_clean = p_name_lower.replace(" ", "")
                    # match day and month, e.g. "12" and "apr"
                    day_match = re.search(r'\b\d+\b', t_date)
                    day_str = day_match.group(0) if day_match else ""
                    month_str = "".join([c for c in t_date if c.isalpha()]).lower()
                    
                    if day_str in p_name_clean and month_str in p_name_clean and t_shift_clean in p_name_clean:
                        print(f"Match found for {t_year} {t_date} {t_shift}: '{paper_name}' -> {link}")
                        found = True
                        
    if not found:
        print(f"No direct match on main page for {t_year} {t_date} {t_shift}")
