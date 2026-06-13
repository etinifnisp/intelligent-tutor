---
description: Download all JEE Main and Advanced PDFs for a given year range
---

## Steps

### 1. Confirm parameters
- Ask the user: which years to download (default: 2015–2025)?
- Ask: JEE Main only, JEE Advanced only, or both?
- Confirm the target directory (default: ./papers/)

### 2. Check existing downloads
- List all files already present in ./papers/main/ and ./papers/advanced/
- Print a summary: X papers already downloaded, Y missing
- Only proceed to download missing files

### 3. Download JEE Main papers
- Navigate to the NTA Downloads page: https://nta.ac.in/Downloads
- Scrape shift-wise PDF URLs for JEE Main.
- If NTA triggers a CAPTCHA or Cloudflare wall:
  - Log a warning in `./logs/pipeline.log`.
  - Fall back to fetching direct public PDF links from educational mirrors (e.g., MathonGo at `https://www.mathongo.com/jee-main-previous-year-question-papers/` or Allen at `https://allen.in/jee-main/previous-year-papers`).
  - Download each PDF to `./papers/main/JEE_MAIN_{YEAR}_S{s}_Shift{n}.pdf`.
- If both fail, log a critical warning prompting the user to place manually downloaded PDFs in the `./papers/main` folder.

### 4. Download JEE Advanced papers
- Navigate to the official JEE Advanced archive page: https://jeeadv.ac.in/archive.html
- Extract the official Paper 1 and Paper 2 PDF links.
- If the official site presents a CAPTCHA or login screen:
  - Log a warning in `./logs/pipeline.log`.
  - Fall back to downloading direct PDF copies from public educational repositories (e.g., Vedantu or MathonGo).
  - Download each to `./papers/advanced/JEE_ADV_{YEAR}_P{n}.pdf`.
- If both fail, log a critical warning prompting the user to manually place downloaded papers under `./papers/advanced`.

### 5. Verify and produce Artifact
- Verify each downloaded file is >10KB (valid PDF, not error page)
- Generate ./outputs/download_manifest.json with: 
  filename, year, source_url, file_size_kb, status
- Produce Artifact: "download_manifest.json"
