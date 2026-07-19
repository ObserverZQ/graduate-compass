# apps/api/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from apps.api.routers import profile, schools, health, match

load_dotenv()
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(profile.router, prefix="/profile")
app.include_router(schools.router, prefix="/schools")

# create API POST /match/stream
app.include_router(match.router, prefix="/match", tags=["matching"])
