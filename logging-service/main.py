"""
logging-service — stores transactions in memory
POST /log        — store {transaction_id, user_id, amount}
GET  /log        — return all transactions
GET  /log/{user} — return transactions for a specific user
"""
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
store: dict = {}
lock = threading.Lock()


@app.route("/log", methods=["POST"])
def log_transaction():
    data = request.get_json(silent=True)
    if not data or "transaction_id" not in data:
        return jsonify({"error": "Invalid payload"}), 400
    tid = data["transaction_id"]
    with lock:
        if tid in store:
            print(f"[LOG] Duplicate transaction_id={tid}, skipping.")
            return jsonify({"status": "duplicate"})
        store[tid] = data
    print(f"[LOG] Stored: {data}")
    return jsonify({"status": "ok"})


@app.route("/log", methods=["GET"])
def get_all():
    with lock:
        txs = list(store.values())
    return jsonify({"transactions": txs})


@app.route("/log/<user_id>", methods=["GET"])
def get_user(user_id):
    with lock:
        txs = [v for v in store.values() if str(v.get("user_id")) == str(user_id)]
    return jsonify({"transactions": txs})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8001, debug=False)