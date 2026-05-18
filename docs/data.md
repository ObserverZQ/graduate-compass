# Why PostgreSQL?
Three reasons that matter for GradCompass specifically:
* First, *pgvector*. Postgres has a first-class vector extension that lets you store embeddings and run similarity search in the same database as your structured data. For your RAG pipeline this means one database instead of Postgres + a separate vector DB like Pinecone. Simpler architecture, fewer failure points, cheaper.
* Second, relational data fits your domain naturally. User profiles, programs, schools, admitted student records — these all have clear relationships. A user has many target programs. A program belongs to a school. A school is in a city. Postgres handles this with foreign keys, joins, and constraints in a way that a document DB like MongoDB wouldn't enforce cleanly.
* Third, maturity and ecosystem. Postgres has been production-hardened for 30 years. Supabase, Railway, and every major cloud provider support it natively. SQLAlchemy, Alembic, and every Python ORM work with it out of the box.

# PostgreSQL vs. MySQL
1. Data types
Postgres supports a much richer set of types natively — arrays, JSON/JSONB, UUID, ranges, and critically vector via pgvector. MySQL's JSON support exists but is second-class. This matters for GradCompass because you're storing embeddings, flexible user preference objects, and potentially arrays of target programs.
2. JSONB specifically
Postgres's JSONB stores JSON as binary, meaning it's indexable and queryable efficiently. MySQL's JSON is stored as text under the hood. For semi-structured data like user profiles with optional fields, this is a real difference.
3. Standards compliance
Postgres is significantly more SQL-standard compliant. MySQL has historically had quirks — for example it used to silently insert invalid data rather than throwing errors, and its handling of GROUP BY was non-standard for years. Postgres is strict and predictable.
4. Concurrency model
Postgres uses MVCC (Multi-Version Concurrency Control) more thoroughly than MySQL, meaning reads never block writes and writes never block reads. Under high concurrency Postgres behaves more predictably.
5. Extensions
Postgres has a rich extension ecosystem — pgvector, PostGIS for geospatial, TimescaleDB for time series. MySQL has almost nothing comparable.
6. Open source
MySQL is owned by Oracle, which has historically caused concern in the community about its future direction. PostgreSQL is community-governed with no corporate owner.

# Why asyncpg?
FastAPI is built on async Python — it handles requests concurrently using Python's *asyncio* event loop. The problem is that traditional database drivers like psycopg2 are synchronous — when they make a database call, they block the entire thread until the DB responds. In a sync world that's fine. In an async world it's a bottleneck — one slow DB query freezes your whole server.
*asyncpg* is a PostgreSQL driver written from scratch for async Python. When it makes a DB call it yields control back to the event loop while waiting, so your server can handle other requests in the meantime.
The interview framing: asyncpg lets your FastAPI server remain non-blocking end-to-end. Without it you'd have an async web layer feeding into a sync DB layer — a bottleneck right at the most critical point.


# Dev Log
### schools
-- First create the schools table
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(500) NOT NULL,
    country VARCHAR(100),
    alpha_two_code CHAR(2),
    state_province VARCHAR(100),
    city VARCHAR(200),
    domains TEXT[],
    web_pages TEXT[],
    qs_world_rank INTEGER,
    the_world_rank INTEGER,
    usnews_global_rank INTEGER,
    usnews_national_rank INTEGER,
    search_vector tsvector,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
#### school name search and auto complete:
-- Uses the index, very fast
SELECT * FROM schools WHERE search_vector @@ plainto_tsquery('english', 'mit');


CREATE INDEX idx_schools_search ON schools USING GIN(search_vector)
GIN = Generalized Inverted Index. This is the index that makes tsvector search fast.
Think of it like a book index at the back:
"massachusetts" → [row 4, row 891]
"institute"     → [row 4, row 234, row 1205]
"technology"    → [row 4, row 567]
When you search for "massachusetts institute", Postgres looks up both words in the index and finds the intersection — row 4 — without reading the whole table.
Used when you query like:
sqlWHERE search_vector @@ plainto_tsquery('english', 'massachusetts institute')

CREATE INDEX idx_schools_name ON schools (name varchar_pattern_ops)
This is a regular B-tree index optimized for prefix matching — when you query with LIKE 'mit%' (starts with).
varchar_pattern_ops is a special operator class that tells Postgres to index the raw character pattern rather than locale-aware collation, which makes LIKE 'x%' queries use the index.
Used when you query like:
sqlWHERE name LIKE 'Tong%'  -- starts with "Tong"
Important: this only works for prefix matches. LIKE '%tong%' (contains) still does a full scan.

