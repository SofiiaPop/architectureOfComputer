import os
import time
import uuid
import hazelcast
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PORT = int(os.getenv("PORT", 8000))
LOGGING_SERVICE_URL = os.getenv("LOGGING_SERVICE_URL", "http://logging-service:8081")
COUNTER_SERVICE_URL = os.getenv("COUNTER_SERVICE_URL", "http://counter-service:8084")
HZ_HOSTS = os.getenv("HZ_HOSTS", "hazelcast:5701").split(",")
HZ_CLUSTER_NAME = os.getenv("HZ_CLUSTER_NAME", "dev")
MQ_QUEUE_NAME = os.getenv("MQ_QUEUE_NAME", "counter-queue")

app = FastAPI()
hz_client = None
mq = None

def connect_hazelcast():
    global hz_client, mq
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(cluster_members=HZ_HOSTS, cluster_name=HZ_CLUSTER_NAME)
            mq = hz_client.get_queue(MQ_QUEUE_NAME).blocking()
            print(f"[facade-service] Connected to Hazelcast")
            break
        except Exception as e:
            print(f"[facade-service] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)

class PostRequest(BaseModel):
    msg: str

@app.post("/")
def handle_post(req: PostRequest):
    msg_uuid = str(uuid.uuid4())
    try:
        r = httpx.post(f"{LOGGING_SERVICE_URL}/log", json={"uuid": msg_uuid, "msg": req.msg}, timeout=5)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    mq.put(req.msg)
    return {"status": "ok", "uuid": msg_uuid}

@app.get("/")
def handle_get():
    try:
        logs = httpx.get(f"{LOGGING_SERVICE_URL}/logs", timeout=5).json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))
    try:
        counters = httpx.get(f"{COUNTER_SERVICE_URL}/counter", timeout=3).json()
    except:
        counters = None
    return {"logs": logs, "counters": counters}

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    connect_hazelcast()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
