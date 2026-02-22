"""
facade-service — HTTP server on port 8000
POST /  {msg: "..."}  → UUID generated, sent to logging-service via gRPC
GET  /                → queries logging-service (gRPC) + messages-service (HTTP)
GET  /debug           → shows last error for diagnosis
"""
import uuid, time, traceback
import requests
from flask import Flask, request, jsonify
from grpc_lib import RpcClient, LogRequest, LogResponse, GetRequest, GetResponse

app = Flask(__name__)

LOGGING_HOST  = "127.0.0.1"
LOGGING_PORT  = 8001
MESSAGES_URL  = "http://127.0.0.1:8002"

RETRY_ATTEMPTS = 3
RETRY_DELAY    = 1.0

_last_error = ""


def grpc_log_with_retry(msg_uuid: str, msg: str):
    global _last_error
    payload = LogRequest(uuid=msg_uuid, msg=msg).SerializeToString()
    client  = RpcClient(LOGGING_HOST, LOGGING_PORT)
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            print(f"[FACADE] gRPC attempt {attempt}/{RETRY_ATTEMPTS}: "
                  f"LogMessage uuid={msg_uuid} msg={msg}", flush=True)
            raw  = client.call("LogMessage", payload)
            resp = LogResponse()
            resp.ParseFromString(raw)
            print(f"[FACADE] gRPC response: status={resp.status}", flush=True)
            _last_error = ""
            return resp
        except Exception as e:
            err = traceback.format_exc()
            _last_error = err
            print(f"[FACADE] Attempt {attempt} FAILED:\n{err}", flush=True)
            if attempt < RETRY_ATTEMPTS:
                print(f"[FACADE] Retrying in {RETRY_DELAY}s ...", flush=True)
                time.sleep(RETRY_DELAY)
    return None


def grpc_get_messages() -> str:
    client  = RpcClient(LOGGING_HOST, LOGGING_PORT)
    payload = GetRequest().SerializeToString()
    raw     = client.call("GetMessages", payload)
    resp    = GetResponse()
    resp.ParseFromString(raw)
    return resp.messages


@app.route("/debug")
def debug():
    """Shows the last gRPC error — open this in browser if POST isn't working."""
    return jsonify({"last_grpc_error": _last_error or "none"})


@app.route("/", methods=["POST"])
def post_message():
    data = request.get_json(silent=True)
    if not data or "msg" not in data:
        return jsonify({"error": "Body must be JSON with 'msg' field"}), 400
    msg      = data["msg"]
    msg_uuid = str(uuid.uuid4())
    print(f"[FACADE] POST received: msg={msg}  uuid={msg_uuid}", flush=True)
    resp = grpc_log_with_retry(msg_uuid, msg)
    if resp is None:
        return jsonify({"error": f"logging-service unavailable after {RETRY_ATTEMPTS} retries",
                        "detail": _last_error}), 503
    return jsonify({"uuid": msg_uuid, "status": resp.status})


@app.route("/", methods=["GET"])
def get_messages():
    print("[FACADE] GET — querying logging-service (gRPC) + messages-service (HTTP)", flush=True)
    try:
        logged = grpc_get_messages()
        print(f"[FACADE] logging-service returned: '{logged}'", flush=True)
    except Exception as e:
        err = traceback.format_exc()
        print(f"[FACADE] gRPC GetMessages FAILED:\n{err}", flush=True)
        logged = f"[error: {e}]"
    try:
        r      = requests.get(f"{MESSAGES_URL}/messages", timeout=3)
        static = r.json().get("message", "")
    except Exception as e:
        static = f"[messages-service error: {e}]"
    combined = f"{logged}: {static}"
    print(f"[FACADE] Combined: {combined}", flush=True)
    return jsonify({"result": combined})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)