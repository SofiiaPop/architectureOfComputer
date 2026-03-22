import os
import logging
import asyncpg
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [counter] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/counterdb")

app = FastAPI(title="Counter Service")

db_pool = None

async def get_pool():
    global db_pool
    if db_pool is None:
        for attempt in range(10):
            try:
                db_pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=5)
                logger.info("Connected to PostgreSQL")
                break
            except Exception as e:
                logger.warning(f"DB connection attempt {attempt+1} failed: {e}")
                await asyncio.sleep(3)
        else:
            raise RuntimeError("Could not connect to PostgreSQL after 10 attempts")
    return db_pool

@app.on_event("startup")
async def startup():
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                msg TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW()
            )
        """)
    logger.info("Table 'messages' ready")

class CountRequest(BaseModel):
    msg: str

@app.post("/count")
async def count_message(body: CountRequest):
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute("INSERT INTO messages (msg) VALUES ($1)", body.msg)
    logger.info(f"Stored message in DB: '{body.msg}'")
    return {"status": "stored", "msg": body.msg}

@app.get("/count")
async def get_count():
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT msg, created_at FROM messages ORDER BY created_at")
        count = await conn.fetchval("SELECT COUNT(*) FROM messages")
    result = [{"msg": r["msg"], "created_at": str(r["created_at"])} for r in rows]
    logger.info(f"GET count — total={count}")
    return {"total": count, "messages": result}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "counter"}
