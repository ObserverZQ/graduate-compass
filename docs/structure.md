graduate-compass/
├── web/                # Next.js (Vercel)
│   ├── app/
│   │   ├── page.tsx        # Landing page
│   │   ├── dashboard/      # User profile, results
│   │   └── api/            # Proxies to backend (optional)
│   └── components/
│
├── server/                 # FastAPI (Railway)
│   ├── app/
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── match.py        # Main recommendation endpoint
│   │   │   │   ├── resume.py       # CV parsing
│   │   │   │   └── programs.py     # CRUD for program database
│   │   │   └── deps.py             # Dependency injection
│   │   ├── core/
│   │   │   ├── config.py            # Environment variables
│   │   │   ├── llm.py               # LLM orchestrator with fallback
│   │   │   └── vector_store.py      # pgvector wrapper
│   │   ├── services/
│   │   │   ├── matcher.py           # 3-layer matching logic
│   │   │   ├── parser.py            # Resume → structured data
│   │   │   └── explainer.py         # LLM explanation generation
│   │   └── models/
│   │       ├── user.py
│   │       ├── program.py
│   │       └── match.py
│   ├── tasks/               # Celery background jobs
│   │   └── embeddings.py    # Batch embedding generation
│   └── requirements.txt
│
├── supabase/
│   └── migrations/          # Database schema
│       ├── 001_programs.sql
│       ├── 002_users.sql
│       └── 003_vector_tables.sql
│
└── docker-compose.yml       # Local development