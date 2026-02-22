from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/messages", methods=["GET"])
def get_messages():
    print("[MESSAGES] GET /messages — returning static message.")
    return jsonify({"message": "not implemented yet"})


@app.route("/", methods=["GET"])
def root():
    return jsonify({"service": "messages-service", "port": 8002,
                    "endpoints": {"GET /messages": "returns static text"}})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8002, debug=False)