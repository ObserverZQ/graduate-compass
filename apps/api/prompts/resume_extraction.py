EXTRACTION_PROMPT = """\
Parse the resume text below and return a single JSON object with exactly the
keys listed here. Do not add keys. Use null for an unknown scalar field and an
empty array for an unknown collection.
Keep all free-text descriptions concise (1-2 sentences). Do not copy full
bullet-point lists from the resume verbatim.

Keys:
- name: string — applicant's full name
- gpa: number — GPA value (e.g. 3.8)
- gpa_base: number — GPA scale (4.0, 5.0, or 100.0); infer from context if not stated
- gpa_ranking: string — undergraduate school name or ranking text (e.g. "MIT", "Top 50 US university")
- toefl_scale_6: number — TOEFL's latest iBT score (range 0-6); null if not found
- toefl_scale_120: integer — TOEFL (range 0-120); null if not found
- ielts: number — IELTS band score (range 0-9); null if not found
- target_degrees: array of strings — degrees the applicant mentions targeting, e.g. ["MS", "PhD"]
- work_experiences: array of objects with keys: company, title, start_date, end_date, description
  - description: a brief 1-2 sentence summary of the role's key responsibility/impact
- research_experiences: array of objects with keys: institution, title, start_date, end_date, description
  - description: a brief 1-2 sentence summary of the research focus/contribution
- publications: array of objects with keys: title, venue, year, authors

Resume:
{resume_text}
"""
