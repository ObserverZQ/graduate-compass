# Graduate Compass MVP (1 week)

## Goal
Help a CS student find top 10 grad programs via resume + preferences in 5 aspects.

## Core Flow
1. Upload resume (PDF/text)
2. Choose: Location (East/West/Mid USA/Europe/Any), Budget (Low/Med/High), Climate (Cold/Mild/Warm), Safety (1-10), Career (Industry/PhD), Expected Enroll Year&Term(e.g. 2027 Fall)
3. Click "Match" → see ranked list with 1‑line reason per program, and suggested roadmap.

## Data
- 50 CS master's/PhD programs manually seeded.(24/50)
- Columns used: name, university, min_gpa, tuition, location, safety_score, climate, career_focus (from description).

## Tech (simplest)
- Supabase (programs table)
- Python script (later FastAPI) that queries all rows, filters by user's hard constraints (min_gpa), builds prompt with remaining data, calls DeepSeek.
- LLM prompt generation and responses retrieval
- Next.js form + results & suggestions display.

## Success Criteria
One real student says "I would use this again."

## Out of scope
- Vector search, embeddings, RAG, user accounts, saving results, program scraping.