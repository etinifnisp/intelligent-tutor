---
description: Extract and classify all questions from downloaded JEE PDFs
---

## Steps

### 1. Inventory PDFs
- Scan ./papers/main/ and ./papers/advanced/ for all PDF files
- Cross-check against download_manifest.json
- Print count: X PDFs found for extraction

### 2. Extract text per PDF
- For each PDF, use pdfplumber to extract text page-by-page
- Use PyMuPDF to extract embedded images (diagrams, figures, equations)
- Save images to ./extracted/images/{pdf_name}/img_{n}.png

### 3. Classify questions using Gemini
- For each page of text, prompt Gemini to identify question boundaries
- For each question, extract:
  subject, question_type, marks, topic, chapter, difficulty, raw_text
- For each image, call Gemini Vision with prompt:
  "Identify the subject, describe what this diagram shows, extract 
   any text or labels. Return JSON with: subject, description, labels"

### 4. Build corpus JSON
- Merge text and image data per question
- Validate all required fields are present
- Save to ./outputs/jee_corpus.json
- // turbo

### 5. Produce Artifact
- Generate summary: total questions, breakdown by year/subject/type
- Produce Artifact: "extraction_report.json"
