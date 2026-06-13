# JEE Research Pipeline — Agent Rules

## Project context
This project downloads, scrapes, extracts, and deep-researches JEE Main 
and JEE Advanced question papers from 2015–2025. All agent behavior must 
conform to the following rules at all times.

## Data integrity rules
- NEVER overwrite a successfully downloaded PDF. Check file existence 
  before any download attempt. If a file exists and is >10KB, skip it.
- ALWAYS log every file operation (download, parse, write) to 
  ./logs/pipeline.log with a timestamp.
- ALL JSON outputs must be valid JSON. Run json.dumps() with 
  indent=2 before writing. Never write partial or malformed JSON.
- If a phase produces zero output files, halt and report the failure 
  before proceeding to the next phase.

## Code standards
- Use Python 3.10+ syntax throughout.
- All file I/O must use context managers (with open(...) as f).
- All async operations must use asyncio and httpx, not requests, 
  for concurrent downloads.
- Every function must have a docstring and type hints.
- Use pathlib.Path for all file system paths, never os.path strings.
- Handle all exceptions explicitly — never use bare except:.
- Gemini API calls must include retry logic with exponential 
  backoff (3 retries, 2s/4s/8s delays).

## Classification rules
- Every extracted question MUST have: year, exam_type, session, 
  shift, subject, question_type, marks_positive, marks_negative, 
  topic, chapter, difficulty.
- Subject must be exactly one of: Physics | Chemistry | Mathematics.
- Difficulty must be exactly one of: Easy | Medium | Hard.
- Exam type must be exactly one of: JEE_MAIN | JEE_ADVANCED.

## Rate limiting rules
- Gemini Vision calls: max 10 concurrent, 1s delay between batches.
- Web scraping: max 3 concurrent requests per domain, 2s delay 
  between page fetches. Always include a User-Agent header.
- Never make more than 60 Gemini API calls per minute.

## Output rules
- Every phase must produce at least one Artifact before the next 
  phase begins.
- All reports must be saved to ./outputs/ directory.
- Excel files must have freeze_panes on header rows.
- JSON corpus must be sorted by year descending, then by 
  question_number ascending.

## Security and ethics rules
- Do not scrape or store student personal data. Papers only.
- Do not bypass any CAPTCHA or login wall. If a source requires 
  login, skip it and log a warning.
- Respect robots.txt of all domains being scraped.
- Do not store raw PDFs beyond the project directory.
