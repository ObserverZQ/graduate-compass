# Graduate Compass

## Run locally

From the repository root, use two terminals. You need Python, [Bun](https://bun.sh/), and access to the configured Supabase project and DeepSeek API.

1. Create a root `.env` file with `DATABASE_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, and `DEEPSEEK_API_KEY`. Keep this file private; never commit it. `DATABASE_URL` should use the project's async PostgreSQL connection URL. If you already have a working `.env`, leave it as is.
2. Start the backend:

   ```bash
   python3 -m venv .venv                 # skip if .venv already exists
   .venv/bin/python -m pip install -r requirements.txt
   .venv/bin/uvicorn apps.api.main:app --reload --env-file .env
   ```

3. In a second terminal, start the frontend:

   ```bash
   cd web
   bun install --frozen-lockfile         # skip if dependencies are already installed
   bun dev
   ```

Open [http://localhost:3000](http://localhost:3000). The API documentation is at [http://localhost:8000/docs](http://localhost:8000/docs); [http://localhost:8000/health](http://localhost:8000/health) checks the database connection.

The frontend defaults to `http://localhost:8000` for API calls. To use another backend URL, set `NEXT_PUBLIC_API_URL` in `web/.env.local` and restart `bun dev`. The commands above use the configured Supabase database; `supabase start` is not required for that setup.
