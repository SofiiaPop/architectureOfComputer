import os
import time
import httpx
import hazelcast
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

PORT = int(os.getenv("PORT", 8081))
CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8080")
HZ_HOSTS = os.getenv("HZ_HOSTS", "hz1:5701").split(",")

app = FastAPI()

hz_client = None
messages_map = None

def connect_hazelcast():
    global hz_client, messages_map
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(
                cluster_members=HZ_HOSTS,
                cluster_name="dev"
            )
            messages_map = hz_client.get_map("messages").blocking()
            print(f"[logging-service:{PORT}] Connected to Hazelcast")
            break
        except Exception as e:
            print(f"[logging-service:{PORT}] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)


def register_self():
    while True:
        try:
            service_url = f"http://logging-service-{PORT - 8080}:{PORT}"
            resp = httpx.post(
                f"{CONFIG_SERVER_URL}/register",
                json={"service_name": "logging-service", "url": service_url}
            )
            print(f"[logging-service:{PORT}] Registered: {resp.json()}")
            break
        except Exception as e:
            print(f"[logging-service:{PORT}] Config server not ready: {e}, retrying...")
            time.sleep(2)


class LogEntry(BaseModel):
    uuid: str
    msg: str


@app.post("/log")
def log_message(entry: LogEntry):
    print(f"[logging-service:{PORT}] Received POST uuid={entry.uuid} msg={entry.msg}")
    messages_map.put(entry.uuid, entry.msg)
    return {"status": "logged", "port": PORT}


@app.get("/logs")
def get_logs():
    all_entries = {k: v for k, v in messages_map.entry_set()}
    print(f"[logging-service:{PORT}] Returning {len(all_entries)} log entries")
    return all_entries


@app.get("/health")
def health():
    return {"status": "ok", "port": PORT}


if __name__ == "__main__":
    connect_hazelcast()
    register_self()
    uvicorn.run(app, host="0.0.0.0", port=PORT)