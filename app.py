from flask import Flask, jsonify

app = Flask(__name__)


@app.route("/")
def hello_world():
    return "Hello from Koyeb - VJ Forward Bot is running!"


@app.route("/health")
def health():
    return jsonify({"status": "ok", "service": "vj-forward-bot"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)