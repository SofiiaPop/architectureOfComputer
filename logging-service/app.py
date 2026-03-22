import os
import time
import logging
import hazelcast
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

INSTANCE_ID = os.getenv("INSTANCE_ID", "1")

logging.basicConfig(
    level=logging.INFO,
    format=f"%(asctime)s [logging-svc:{INSTANCE_ID}] %(levelname)s %(message)s",
)
logger = logging.getLogger(__name__)

HZ_ADDRESSES = [a.strip() for a in os.getenv("HZ_ADDRESSES", "hazelcast1:5701,hazelcast2:5701,hazelcast3:5701").split(",") if a.strip()]
HZ_CONNECT_RETRIES = int(os.getenv("HZ_CONNECT_RETRIES", "10"))
HZ_CONNECT_DELAY = float(os.getenv("HZ_CONNECT_DELAY", "3.0"))

app = FastAPI(title=f"Logging Service (instance {INSTANCE_ID})")

hz_client = None
hz_map = None

def get_hz_map():
    global hz_client, hz_map
    if hz_map is None:
        for attempt in range(1, HZ_CONNECT_RETRIES + 1):
            try:
                logger.info(f"Connecting to Hazelcast {HZ_ADDRESSES} (attempt {attempt})")
                hz_client = hazelcast.HazelcastClient(
                    cluster_members=HZ_ADDRESSES,
                    cluster_name="dev",
                    connection_timeout=5.0,
                )
                hz_map = hz_client.get_map("messages").blocking()
                logger.info("Connected to Hazelcast cluster — map 'messages' ready")
                break
            except Exception as e:
                logger.warning(f"Hazelcast connect attempt {attempt} failed: {e}")
                if attempt < HZ_CONNECT_RETRIES:
                    time.sleep(HZ_CONNECT_DELAY)
        else:
            raise RuntimeError("Could not connect to Hazelcast after all retries")
    return hz_map

@app.on_event("startup")
async def startup():
    try:
        get_hz_map()
    except Exception as e:
        logger.error(f"Failed to connect to Hazelcast on startup: {e}")

class LogEntry(BaseModel):
    id: str
    msg: str

@app.post("/log")
async def log_message(entry: LogEntry):
    try:
        m = get_hz_map()
        m.put(entry.id, entry.msg)
        logger.info(f"Stored — id={entry.id}  msg='{entry.msg}'")
        return {"status": "stored", "id": entry.id, "instance": INSTANCE_ID}
    except Exception as e:
        logger.error(f"Failed to store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/log")
async def get_messages():
    try:
        m = get_hz_map()
        entries = m.entry_set()
        result = {k: v for k, v in entries}
        logger.info(f"GET — returning {len(result)} messages")
        return result
    except Exception as e:
        logger.error(f"Failed to read: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "logging", "instance": INSTANCE_ID}

@app.on_event("shutdown")
async def shutdown():
    global hz_client
    if hz_client:
        hz_client.shutdown()
