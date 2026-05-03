import os
import time
import threading
import sqlite3
import hazelcast
import uvicorn
from fastapi import FastAPI

PORT = int(os.getenv("PORT", 8084))
HZ_HOSTS = os.getenv("HZ_HOSTS", "hazelcast:5701").split(",")
HZ_CLUSTER_NAME = os.getenv("HZ_CLUSTER_NAME", "dev")
MQ_QUEUE_NAME = os.getenv("MQ_QUEUE_NAME", "counter-queue")

app = FastAPI()
hz_client = None
mq = None
DB_PATH = "/data/counters.db"

def init_db():
    os.makedirs("/data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("CREATE TABLE IF NOT EXISTS counters (msg TEXT PRIMARY KEY, count INTEGER DEFAULT 0)")
    conn.commit()
    conn.close()

def increment(msg):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO counters(msg,count) VALUES(?,1) ON CONFLICT(msg) DO UPDATE SET count=count+1", (msg,))
    conn.commit()
    conn.close()

def get_all():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT msg, count FROM counters").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}

def connect_hazelcast():
    global hz_client, mq
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(cluster_members=HZ_HOSTS, cluster_name=HZ_CLUSTER_NAME)
            mq = hz_client.get_queue(MQ_QUEUE_NAME).blocking()
            print(f"[counter-service] Connected to Hazelcast, queue={MQ_QUEUE_NAME}")
            break
        except Exception as e:
            print(f"[counter-service] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)

def consume_loop():
    while True:
        try:
            msg = mq.poll(timeout=2)
            if msg:
                increment(msg)
        except Exception as e:
            print(f"[counter-service] Consumer error: {e}")
            time.sleep(1)

@app.get("/counter")
def get_counter():
    return get_all()

@app.get("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    init_db()
    connect_hazelcast()
    threading.Thread(target=consume_loop, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
