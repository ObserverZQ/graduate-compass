from openai import AsyncOpenAI, OpenAI
from supabase import create_client, Client
import os

deepseek = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

deepseek_sync = OpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
)

_supabase_url = os.getenv("SUPABASE_URL")
_supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
if _supabase_url is None:
    raise RuntimeError("SUPABASE_URL environment variable is not set")
if _supabase_key is None:
    raise RuntimeError("SUPABASE_SERVICE_ROLE_KEY environment variable is not set")

supabase: Client = create_client(_supabase_url, _supabase_key)