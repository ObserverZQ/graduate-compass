# apps/api/main.py
from fastapi import FastAPI
from dotenv import load_dotenv
from apps.api.routers import profile, schools, health

load_dotenv()
app = FastAPI()

app.include_router(health.router)
app.include_router(profile.router, prefix="/profile")
app.include_router(schools.router, prefix="/schools")

# from fastapi import FastAPI
# from openai import OpenAI
# from google import genai
# from dotenv import load_dotenv
# from apps.api.database import engine
# import os
# from fastapi import UploadFile, File, Form
# import pdfplumber
# import io
# import uuid
# from apps.api.database import SessionLocal

# from sqlalchemy import text

# load_dotenv()
# app = FastAPI()
# client = OpenAI(
#     api_key=os.getenv("DEEPSEEK_API_KEY"), base_url="https://api.deepseek.com"
# )


# @app.get("/")
# async def home():
#     return {"reply": "Hello World"}

# @app.get("/t")
# async def home():
#     return {"reply": "Hello T"}



# @app.post("/profile/upload-resume")
# async def upload_resume(file: UploadFile = File(...)):
#     # Read file bytes
#     contents = await file.read()
    
#     # Extract text using pdfplumber
#     with pdfplumber.open(io.BytesIO(contents)) as pdf:
#         extracted_text = "\n".join(
#             page.extract_text() or ""
#             for page in pdf.pages
#         )
    
#     # Generate session_id
#     session_id = str(uuid.uuid4())
    
#     # Save to DB
#     async with SessionLocal() as session:
#         await session.execute(text("""
#             INSERT INTO user_profiles (session_id, resume_raw_text)
#             VALUES (:session_id, :resume_raw_text)
#         """), {
#             "session_id": session_id,
#             "resume_raw_text": extracted_text
#         })
#         await session.commit()
    
#     return {
#         "session_id": session_id,
#         "extracted_text": extracted_text
#     }

# # health check endpoint
# @app.get("/health")
# async def health():
#     async with engine.connect() as conn:
#         await conn.execute(text("SELECT 1"))
#     return {"status": "ok", "db": "connected"}


# @app.get("/ping")
# async def ping():
#     resp = client.chat.completions.create(
#         model="deepseek-chat",
#         messages=[{"role": "user", "content": "Say hello from GradCompass."}],
#     )
#     return {"reply": resp.choices[0].message.content}


# @app.get("/test")
# async def test():
#     response = client.chat.completions.create(
#         model="deepseek-v4-pro",
#         messages=[
#             {"role": "system", "content": "You are a helpful assistant"},
#             {"role": "user", "content": "Hello"},
#         ],
#         stream=False,
#         reasoning_effort="high",
#         extra_body={"thinking": {"type": "enabled"}},
#     )
#     print(response.choices[0].message.content)


# @app.get("/gemini")
# async def gemini():
#     # The client gets the API key from the environment variable `GEMINI_API_KEY`.
#     client = genai.Client()

#     response = client.models.generate_content(
#         model="gemini-3-flash-preview", contents="Explain how AI works in a few words"
#     )
#     print(response.text)
#     return {"text": response.text}
