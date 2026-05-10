Local Development
# Terminal 1: Supabase locally
supabase start

# Terminal 2: Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Terminal 3: Frontend
cd frontend
npm install
npm run dev