from fastapi import APIRouter
from sqlalchemy import text
from apps.api.database import engine
from openai import OpenAI
import os

router = APIRouter()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com"
)

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
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say hello from GradCompass."}],
    )
    return {"reply": resp.choices[0].message.content}