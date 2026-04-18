import os
import time
import uuid
import random
import hazelcast
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

PORT = int(os.getenv("PORT", 8000))
CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8080")
HZ_HOSTS = os.getenv("HZ_HOSTS", "hz1:5701").split(",")

app = FastAPI()

hz_client = None
mq = None

def connect_hazelcast():
    global hz_client, mq
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(
                cluster_members=HZ_HOSTS,
                cluster_name="dev"
            )
            mq = hz_client.get_queue("counter-queue").blocking()
            print("[facade-service] Connected to Hazelcast")
            break
        except Exception as e:
            print(f"[facade-service] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)


def get_service_urls(service_name: str):
    """Ask config-server for all URLs of a service."""
    resp = httpx.get(f"{CONFIG_SERVER_URL}/services/{service_name}")
    resp.raise_for_status()
    return resp.json()["urls"]


def pick_random_url(service_name: str) -> str:
    urls = get_service_urls(service_name)
    return random.choice(urls)


class PostRequest(BaseModel):
    msg: str


@app.post("/")
def handle_post(req: PostRequest):
    msg_uuid = str(uuid.uuid4())
    msg = req.msg

    logging_url = pick_random_url("logging-service")
    print(f"[facade-service] POST -> logging-service at {logging_url}, uuid={msg_uuid}")
    log_resp = httpx.post(f"{logging_url}/log", json={"uuid": msg_uuid, "msg": msg})
    log_resp.raise_for_status()

    print(f"[facade-service] Enqueuing to counter-queue: {msg}")
    mq.put(msg)

    return {"status": "ok", "uuid": msg_uuid, "logged_by": logging_url}


@app.get("/")
def handle_get():
    logging_url = pick_random_url("logging-service")
    print(f"[facade-service] GET logs <- {logging_url}")
    logs_resp = httpx.get(f"{logging_url}/logs")
    logs_resp.raise_for_status()
    logs = logs_resp.json()

    counter_url = pick_random_url("counter-service")
    print(f"[facade-service] GET counter <- {counter_url}")
    try:
        counter_resp = httpx.get(f"{counter_url}/counter", timeout=3)
        counter_resp.raise_for_status()
        counters = counter_resp.json()
    except Exception as e:
        print(f"[facade-service] Counter-service unavailable: {e}")
        counters = None

    return {"logs": logs, "counters": counters}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    connect_hazelcast()
    uvicorn.run(app, host="0.0.0.0", port=PORT)