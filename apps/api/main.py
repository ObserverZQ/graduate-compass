# apps/api/main.py
from fastapi import FastAPI
from openai import OpenAI
from google import genai
from dotenv import load_dotenv
from server.apps.api.database import engine
import os

from sqlalchemy import text

load_dotenv()
app = FastAPI()
client = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
)


@app.get("/")
async def home():
    return {"reply": "Hello World"}


# health check endpoint
@app.get("/health")
async def health():
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    return {"status": "ok", "db": "connected"}


@app.get("/ping")
async def ping():
    resp = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": "Say hello from GradCompass."}],
    )
    return {"reply": resp.choices[0].message.content}


@app.get("/test")
async def test():
    response = client.chat.completions.create(
        model="deepseek-v4-pro",
        messages=[
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
        ],
        stream=False,
        reasoning_effort="high",
        extra_body={"thinking": {"type": "enabled"}},
    )
    print(response.choices[0].message.content)


@app.get("/gemini")
async def gemini():
    # The client gets the API key from the environment variable `GEMINI_API_KEY`.
    client = genai.Client()

    response = client.models.generate_content(
        model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
    )
    print(response.text)
    return {"text": response.text}
