Good question. Here's the standard practice:

---

**The flow:**

```
User uploads PDF resume
→ Frontend sends file to FastAPI via multipart form
→ FastAPI extracts text from PDF
→ Store raw text in DB (user_profiles table)
→ Use extracted text in RAG prompt
```

---

**Why extract on the backend, not frontend:**

- PDF parsing libraries are Python-native and much better than JS equivalents
- You want to store the extracted text in DB for reuse — no re-parsing on every evaluation
- Sensitive file processing shouldn't happen client-side

---

**The FastAPI endpoint:**

```python
from fastapi import UploadFile, File, Form
import pdfplumber
import io

@app.post("/profile/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    # Read file bytes
    contents = await file.read()
    
    # Extract text using pdfplumber
    with pdfplumber.open(io.BytesIO(contents)) as pdf:
        text = "\n".join(
            page.extract_text() or "" 
            for page in pdf.pages
        )
    
    # Store in DB and return extracted text
    return {"extracted_text": text}
```

```bash
pip install pdfplumber
```

---

**Why `pdfplumber` over `pypdf`:**

`pdfplumber` handles layout better — it preserves column structure which matters for resumes that have two-column layouts. `pypdf` often merges columns into garbled text.

---

**For your filtering flow specifically:**

After extraction, run a lightweight parse to pull out hard data before hitting the LLM — saves tokens and is more reliable for structured fields:

```python
import re

def extract_gpa(text):
    # Matches "GPA: 3.8", "GPA 3.85/4.0", "3.9/4.0"
    match = re.search(r'GPA[\s:]*(\d\.\d+)', text, re.IGNORECASE)
    return float(match.group(1)) if match else None

def extract_toefl(text):
    match = re.search(r'TOEFL[\s:]*(\d{2,3})', text, re.IGNORECASE)
    return int(match.group(1)) if match else None
```

Then your filtering pipeline becomes:

```
1. Extract GPA + TOEFL from resume text with regex  ← hard filter layer
2. Query DB: WHERE min_gpa <= :gpa AND min_toefl <= :toefl  ← SQL filter
3. Take remaining programs → stuff into RAG prompt  ← LLM soft matching
4. LLM ranks by fit, research alignment, preferences  ← output top 10-15
```

This is efficient — the SQL filter reduces 500 programs to maybe 50, then LLM only reasons over those 50. Saves tokens significantly.

---

**What to store in DB:**

```sql
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL,  -- no auth needed for MVP
    resume_raw_text TEXT,
    extracted_gpa FLOAT,
    extracted_toefl INT,
    preferences JSONB,  -- city, climate, budget etc.
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

Store everything — raw text, extracted fields, preferences. Then your evaluation endpoint just pulls from DB rather than re-parsing every time.

Want me to write the complete evaluation endpoint that chains filtering → RAG → LLM report generation?