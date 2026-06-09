from fastapi import APIRouter
from sqlalchemy import text
from apps.api.database import SessionLocal

router = APIRouter()

@router.get("/search")
async def search_schools(q: str, limit: int = 10):
    async with SessionLocal() as session:
        result = await session.execute(text("""
            SELECT id, name, country, alpha_two_code,
                   qs_world_rank, usnews_national_rank
            FROM schools
            WHERE search_vector @@ plainto_tsquery('english', :q)
               OR name ILIKE :ilike
            ORDER BY
                CASE WHEN name ILIKE :starts_with THEN 0 ELSE 1 END,
                qs_world_rank ASC NULLS LAST
            LIMIT :limit
        """), {
            "q": q,
            "ilike": f"%{q}%",
            "starts_with": f"{q}%",
            "limit": limit
        })
        rows = result.mappings().all()
        return {"results": [dict(r) for r in rows]}