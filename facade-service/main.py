import uuid, time, threading
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

LOGGING_URL = "http://logging-service:8001"
COUNTER_URL = "http://counter-service:8002"

stats_lock = threading.Lock()
logging_total_ms  = 0.0
logging_calls     = 0
counter_total_ms  = 0.0
counter_calls     = 0


def _timed_post(url, payload):
    t0 = time.perf_counter()
    r  = requests.post(url, json=payload, timeout=10)
    ms = (time.perf_counter() - t0) * 1000
    return r, ms


def _timed_get(url):
    t0 = time.perf_counter()
    r  = requests.get(url, timeout=10)
    ms = (time.perf_counter() - t0) * 1000
    return r, ms

@app.route("/transaction", methods=["POST"])
def post_transaction():
    global logging_total_ms, logging_calls, counter_total_ms, counter_calls

    data = request.get_json(silent=True)
    if not data or "user_id" not in data or "amount" not in data:
        return jsonify({"error": "Required: user_id, amount"}), 400

    user_id    = str(data["user_id"])
    amount     = float(data["amount"])
    tx_id      = str(uuid.uuid4())
    timestamp  = time.time()

    transaction = {
        "transaction_id": tx_id,
        "user_id":        user_id,
        "amount":         amount,
        "timestamp":      timestamp,
    }

    print(f"[FACADE] POST transaction: {transaction}")

    log_result   = [None]
    count_result = [None]
    log_ms       = [0.0]
    count_ms     = [0.0]
    errors       = []

    def call_logging():
        try:
            r, ms = _timed_post(f"{LOGGING_URL}/log", transaction)
            log_result[0] = r.json()
            log_ms[0]     = ms
        except Exception as e:
            errors.append(f"logging-service: {e}")

    def call_counter():
        try:
            r, ms = _timed_post(f"{COUNTER_URL}/counter",
                                 {"user_id": user_id, "amount": amount})
            count_result[0] = r.json()
            count_ms[0]     = ms
        except Exception as e:
            errors.append(f"counter-service: {e}")

    t_log   = threading.Thread(target=call_logging)
    t_count = threading.Thread(target=call_counter)
    t_log.start();   t_count.start()
    t_log.join();    t_count.join()

    if errors:
        return jsonify({"error": errors}), 503

    with stats_lock:
        logging_total_ms  += log_ms[0];   logging_calls  += 1
        counter_total_ms  += count_ms[0]; counter_calls  += 1

    balance = count_result[0].get("balance", 0)
    print(f"[FACADE] tx_id={tx_id}  user={user_id}  "
          f"amount={amount:+.2f}  balance={balance:.2f}  "
          f"log={log_ms[0]:.1f}ms  counter={count_ms[0]:.1f}ms")

    return jsonify({"transaction_id": tx_id, "balance": balance})


@app.route("/user/<user_id>", methods=["GET"])
def get_user(user_id):
    global logging_total_ms, logging_calls, counter_total_ms, counter_calls

    try:
        r_log, ms_log = _timed_get(f"{LOGGING_URL}/log/{user_id}")
        transactions  = r_log.json().get("transactions", [])
    except Exception as e:
        return jsonify({"error": f"logging-service: {e}"}), 503

    try:
        r_cnt, ms_cnt = _timed_get(f"{COUNTER_URL}/counter/{user_id}")
        balance       = r_cnt.json().get("balance", 0)
    except Exception as e:
        return jsonify({"error": f"counter-service: {e}"}), 503

    with stats_lock:
        logging_total_ms += ms_log; logging_calls  += 1
        counter_total_ms += ms_cnt; counter_calls  += 1

    print(f"[FACADE] GET user={user_id}  balance={balance}  "
          f"txs={len(transactions)}  log={ms_log:.1f}ms  counter={ms_cnt:.1f}ms")
    return jsonify({"user_id": user_id, "balance": balance,
                    "transactions": transactions})

@app.route("/accounts", methods=["GET"])
def get_accounts():
    global counter_total_ms, counter_calls
    try:
        r, ms = _timed_get(f"{COUNTER_URL}/counter")
        balances = r.json().get("balances", {})
    except Exception as e:
        return jsonify({"error": f"counter-service: {e}"}), 503

    with stats_lock:
        counter_total_ms += ms; counter_calls += 1

    print(f"[FACADE] GET /accounts  counter={ms:.1f}ms")
    return jsonify({"balances": balances})

@app.route("/stats", methods=["GET"])
def get_stats():
    with stats_lock:
        return jsonify({
            "logging_service":  {
                "total_calls": logging_calls,
                "total_ms":    round(logging_total_ms, 2),
                "avg_ms":      round(logging_total_ms / logging_calls, 2) if logging_calls else 0,
            },
            "counter_service":  {
                "total_calls": counter_calls,
                "total_ms":    round(counter_total_ms, 2),
                "avg_ms":      round(counter_total_ms / counter_calls, 2) if counter_calls else 0,
            },
        })


@app.route("/stats", methods=["DELETE"])
def reset_stats():
    global logging_total_ms, logging_calls, counter_total_ms, counter_calls
    with stats_lock:
        logging_total_ms = logging_calls = counter_total_ms = counter_calls = 0
    return jsonify({"status": "stats reset"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)