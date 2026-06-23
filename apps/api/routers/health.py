from fastapi import APIRouter
from sqlalchemy import text
from apps.api.database import engine
from apps.api.clients import deepseek_sync

router = APIRouter()

@router.get("/")
async def home():
    return {"reply": "Hello World"}

@router.get("/health")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}

@router.get("/ping")
async def ping():
    resp = deepseek_sync.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say hello from GradCompass."}],
    )
    return {"reply": resp.choices[0].message.content}