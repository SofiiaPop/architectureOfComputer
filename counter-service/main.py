from flask import Flask, request, jsonify
import threading

app = Flask(__name__)
balances: dict = {}
lock = threading.Lock()


@app.route("/counter", methods=["POST"])
def apply_transaction():
    data = request.get_json(silent=True)
    if not data or "user_id" not in data or "amount" not in data:
        return jsonify({"error": "Invalid payload"}), 400
    user_id = str(data["user_id"])
    try:
        amount = float(data["amount"])
    except (ValueError, TypeError):
        return jsonify({"error": "amount must be a number"}), 400

    with lock:
        balances[user_id] = balances.get(user_id, 0.0) + amount
        new_balance = balances[user_id]

    print(f"[COUNTER] user={user_id}  delta={amount:+.2f}  balance={new_balance:.2f}")
    return jsonify({"user_id": user_id, "balance": new_balance})


@app.route("/counter/<user_id>", methods=["GET"])
def get_balance(user_id):
    with lock:
        balance = balances.get(str(user_id), 0.0)
    return jsonify({"user_id": user_id, "balance": balance})


@app.route("/counter", methods=["GET"])
def get_all_balances():
    with lock:
        all_b = dict(balances)
    return jsonify({"balances": all_b})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=False)