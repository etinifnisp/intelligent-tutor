---
description: Generate the final Excel report and study strategy brief
---

## Steps

### 1. Load all outputs
- Load jee_corpus.json and research_analysis.json
- Verify both files exist and are valid JSON

### 2. Build Excel workbook
- Sheet 1: Chapter heatmap — rows = chapters, cols = years, 
  values = question count. Conditional formatting: green low, red high.
- Sheet 3: Top 50 predicted high-weightage topics with confidence score
- Sheet 4: Difficulty distribution by year and subject (stacked bar data)
- Sheet 5: JEE Advanced vs JEE Main overlap — shared chapters and exclusive
- Apply freeze_panes, bold headers, auto column width
- Save to ./outputs/jee_research_report.xlsx
- // turbo

### 3. Build Markdown summary
- Write ./outputs/jee_summary.md with:
  Executive summary, top 10 topics per exam, trend insights, 
  predicted focus areas for next year, study strategy recommendations

### 4. Produce final Artifact
- Produce Artifact: "pipeline_complete.md" listing all output files 
  with descriptions and file sizes
