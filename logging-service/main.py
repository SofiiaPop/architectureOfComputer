import os
import time
import hazelcast
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

PORT = int(os.getenv("PORT", 8081))
HZ_HOSTS = os.getenv("HZ_HOSTS", "hazelcast:5701").split(",")
HZ_CLUSTER_NAME = os.getenv("HZ_CLUSTER_NAME", "dev")
HZ_MAP_NAME = os.getenv("HZ_MAP_NAME", "messages")

app = FastAPI()
hz_client = None
messages_map = None

def connect_hazelcast():
    global hz_client, messages_map
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(
                cluster_members=HZ_HOSTS,
                cluster_name=HZ_CLUSTER_NAME
            )
            messages_map = hz_client.get_map(HZ_MAP_NAME).blocking()
            print(f"[logging-service:{PORT}] Connected to Hazelcast")
            break
        except Exception as e:
            print(f"[logging-service:{PORT}] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)

class LogEntry(BaseModel):
    uuid: str
    msg: str

@app.post("/log")
def log_message(entry: LogEntry):
    messages_map.put(entry.uuid, entry.msg)
    return {"status": "logged", "port": PORT}

@app.get("/logs")
def get_logs():
    return {k: v for k, v in messages_map.entry_set()}

@app.get("/health")
def health():
    return {"status": "ok", "port": PORT}

if __name__ == "__main__":
    connect_hazelcast()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
