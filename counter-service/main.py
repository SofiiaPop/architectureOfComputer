import os
import time
import threading
import sqlite3
import hazelcast
import httpx
import uvicorn
from fastapi import FastAPI

PORT = int(os.getenv("PORT", 8084))
CONFIG_SERVER_URL = os.getenv("CONFIG_SERVER_URL", "http://config-server:8080")
HZ_HOSTS = os.getenv("HZ_HOSTS", "hz1:5701").split(",")

app = FastAPI()

hz_client = None
mq = None

DB_PATH = "counters.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS counters (
            msg TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


def increment(msg: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT INTO counters(msg, count) VALUES(?, 1)
        ON CONFLICT(msg) DO UPDATE SET count = count + 1
    """, (msg,))
    conn.commit()
    conn.close()


def get_all():
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT msg, count FROM counters").fetchall()
    conn.close()
    return {row[0]: row[1] for row in rows}


def connect_hazelcast():
    global hz_client, mq
    while True:
        try:
            hz_client = hazelcast.HazelcastClient(
                cluster_members=HZ_HOSTS,
                cluster_name="dev"
            )
            mq = hz_client.get_queue("counter-queue").blocking()
            print(f"[counter-service] Connected to Hazelcast")
            break
        except Exception as e:
            print(f"[counter-service] Hazelcast not ready: {e}, retrying...")
            time.sleep(3)


def register_self():
    while True:
        try:
            resp = httpx.post(
                f"{CONFIG_SERVER_URL}/register",
                json={"service_name": "counter-service",
                      "url": f"http://counter-service:{PORT}"}
            )
            print(f"[counter-service] Registered: {resp.json()}")
            break
        except Exception as e:
            print(f"[counter-service] Config server not ready: {e}, retrying...")
            time.sleep(2)


def consume_loop():
    """Background thread: reads from MQ and updates DB."""
    print("[counter-service] Consumer loop started")
    while True:
        try:
            msg = mq.poll(timeout=2)
            if msg is not None:
                print(f"[counter-service] Consumed from queue: {msg}")
                increment(msg)
        except Exception as e:
            print(f"[counter-service] Error in consumer loop: {e}")
            time.sleep(1)


@app.get("/counter")
def get_counter():
    data = get_all()
    print(f"[counter-service] GET /counter -> {data}")
    return data


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    init_db()
    connect_hazelcast()
    register_self()

    t = threading.Thread(target=consume_loop, daemon=True)
    t.start()

    uvicorn.run(app, host="0.0.0.0", port=PORT)