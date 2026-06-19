from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv, find_dotenv
import os

load_dotenv(find_dotenv())

DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL is None:
    raise RuntimeError("DATABASE_URL environment variable is not set")

# engine = create_async_engine(DATABASE_URL)
# statement_cache_size=0 disables asyncpg's prepared statement cache, which is
# required when connecting through Supabase's pgbouncer pooler (transaction
# pooling mode doesn't support reusable prepared statements).
engine = create_async_engine(
    DATABASE_URL,
    connect_args={"ssl": "require", "statement_cache_size": 0},
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
Base = declarative_base()
