"""
logging-service
  - gRPC TCP server on port 8001  (LogMessage, GetMessages)
  - HTTP debug server on port 8011 (/, /health)
"""
import threading
from flask import Flask, jsonify
from grpc_lib import RpcServer, LogRequest, LogResponse, GetRequest, GetResponse

message_store: dict = {}
store_lock = threading.Lock()


def handle_log(body: bytes) -> bytes:
    req = LogRequest()
    req.ParseFromString(body)
    with store_lock:
        if req.uuid in message_store:
            print(f"[DEDUP] UUID {req.uuid} already stored — skipping.")
            resp = LogResponse(status="duplicate", uuid=req.uuid)
        else:
            message_store[req.uuid] = req.msg
            print(f"[LOG] Stored: UUID={req.uuid}  msg={req.msg}")
            resp = LogResponse(status="ok", uuid=req.uuid)
    return resp.SerializeToString()


def handle_get(body: bytes) -> bytes:
    with store_lock:
        msgs = list(message_store.values())
    result = ", ".join(msgs) if msgs else ""
    print(f"[LOG] Returning {len(msgs)} message(s): {result}")
    return GetResponse(messages=result).SerializeToString()


http_app = Flask("logging-http-debug")

@http_app.route("/")
@http_app.route("/health")
def health():
    with store_lock:
        msgs = list(message_store.values())
    return jsonify({"service": "logging-service", "grpc_port": 8001,
                    "http_debug_port": 8011, "stored_messages": msgs})


rpc = RpcServer("0.0.0.0", 8001)
rpc.register("LogMessage",  handle_log)
rpc.register("GetMessages", handle_get)

if __name__ == "__main__":
    threading.Thread(
        target=lambda: http_app.run(host="0.0.0.0", port=8011, debug=False),
        daemon=True
    ).start()
    print("[LOG] HTTP debug endpoint → http://127.0.0.1:8011/health")
    rpc.serve()