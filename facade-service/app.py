import os
import uuid
import random
import logging
import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [facade] %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="Facade Service")

LOGGING_URLS = [u.strip() for u in os.getenv("LOGGING_SERVICE_URLS", "http://logging1:8001,http://logging2:8002,http://logging3:8003").split(",") if u.strip()]
COUNTER_URL = os.getenv("COUNTER_SERVICE_URL", "http://counter:8010")

class MessageRequest(BaseModel):
    msg: str

async def post_to_logging(msg_id: str, msg: str):
    urls = LOGGING_URLS.copy()
    random.shuffle(urls)
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(f"{url}/log", json={"id": msg_id, "msg": msg})
                resp.raise_for_status()
                logger.info(f"POST to {url} OK — id={msg_id}")
                return
        except Exception as e:
            logger.warning(f"logging-service {url} unavailable: {e}, trying next...")
    raise HTTPException(status_code=503, detail="All logging-service instances are unavailable")

async def get_from_logging():
    urls = LOGGING_URLS.copy()
    random.shuffle(urls)
    for url in urls:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{url}/log")
                resp.raise_for_status()
                logger.info(f"GET from {url} OK")
                return resp.json()
        except Exception as e:
            logger.warning(f"logging-service {url} unavailable: {e}, trying next...")
    raise HTTPException(status_code=503, detail="All logging-service instances are unavailable")

@app.post("/")
async def post_message(body: MessageRequest):
    msg_id = str(uuid.uuid4())
    logger.info(f"Received POST msg='{body.msg}', assigned id={msg_id}")
    await post_to_logging(msg_id, body.msg)
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            await client.post(f"{COUNTER_URL}/count", json={"msg": body.msg})
        except Exception as e:
            logger.warning(f"counter-service unavailable: {e}")
    return {"id": msg_id, "msg": body.msg, "status": "logged"}

@app.get("/")
async def get_messages():
    logs = await get_from_logging()
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            counter_resp = await client.get(f"{COUNTER_URL}/count")
            counter_data = counter_resp.json()
        except Exception as e:
            logger.warning(f"counter-service unavailable: {e}")
            counter_data = {"error": "counter-service unavailable"}
    return {"logs": logs, "counter": counter_data}

@app.get("/health")
async def health():
    return {"status": "ok", "service": "facade"}
