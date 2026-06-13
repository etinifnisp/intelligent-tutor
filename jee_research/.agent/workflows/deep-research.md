---
description: Run full topic analysis and web deep-search on the JEE corpus
---

## Steps

### 1. Load corpus
- Read ./outputs/jee_corpus.json
- Confirm it contains data from at least 8 years before proceeding

### 2. Frequency analysis
- Compute chapter-wise question count across all years
- Compute marks-weighted frequency per chapter
- Identify top 20 chapters for JEE Main and top 20 for JEE Advanced
- Identify chapters with rising frequency trend (last 3 years vs prior 3)

### 3. Pattern analysis
- Find question sub-types that repeat across years (structural similarity)
- Flag chapters where difficulty shifted Easy→Hard over time

### 4. Web deep search
- Search: "JEE Main syllabus changes NTA 2023 2024 2025"
- Search: "JEE Advanced syllabus update IIT 2024 2025"
- Search: "JEE Main most important chapters Allen Resonance 2025"
- Search: "JEE Main pattern change NTA 2022 2023 numeric section"
- For each search, fetch the top result and extract key findings
- Cross-validate findings against corpus data

### 5. Output
- Save ./outputs/research_analysis.json
- Save ./outputs/deep_search_report.md with citations
- Produce Artifact: "research_complete.md"
