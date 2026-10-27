import os
import time
from flask import Flask, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return jsonify({
        "name": "PRIME ZENITH WORKER",
        "status": "online",
        "version": "1.0.0"
    })

@app.get("/worker/status")
def status():
    return jsonify({
        "connected": True,
        "execution": False,
        "runtime": "not configured",
        "timestamp": int(time.time())
    })

if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
