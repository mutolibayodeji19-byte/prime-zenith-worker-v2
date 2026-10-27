import os
import time
import hmac
import secrets
import subprocess
import tempfile
from pathlib import Path

from flask import Flask, request, jsonify

app = Flask(__name__)

WORKER_KEY = os.environ.get("WORKER_KEY", "")
MAX_CODE_SIZE = 10_000
MAX_RUNTIME = 5


@app.get("/")
def home():
    return jsonify({
        "name": "PRIME ZENITH WORKER",
        "status": "online",
        "version": "2.0.0"
    })


@app.get("/worker/status")
def status():
    return jsonify({
        "connected": True,
        "execution": bool(WORKER_KEY),
        "runtime": {
            "python": True,
            "node": shutil_which("node") is not None
        },
        "timestamp": int(time.time())
    })


def shutil_which(command):
    import shutil
    return shutil.which(command)


def authorized():
    supplied = request.headers.get("X-Worker-Key", "")
    return bool(WORKER_KEY) and hmac.compare_digest(
        supplied, WORKER_KEY
    )


@app.post("/worker/execute")
def execute():
    if not authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    language = data.get("language", "python")
    code = data.get("code")

    if language not in ("python", "node"):
        return jsonify({"error": "Use python or node"}), 400

    if not isinstance(code, str) or not code.strip():
        return jsonify({"error": "Code is required"}), 400

    if len(code.encode("utf-8")) > MAX_CODE_SIZE:
        return jsonify({"error": "Code is too large"}), 413

    # Execution is deliberately disabled until a proper
    # isolated sandbox and resource limits are configured.
    return jsonify({
        "success": False,
        "error": "Execution is disabled until sandboxing is configured."
    }), 503


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
