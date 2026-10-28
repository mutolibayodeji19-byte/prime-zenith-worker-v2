import os
import time
import json
import hmac

from flask import Flask, jsonify, request
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__)
WORKER_VERSION = "2.3.1"


def worker_authorized():
    expected = os.environ.get("WORKER_KEY", "").strip()
    supplied = request.headers.get("X-Worker-Key", "").strip()

    return bool(expected) and hmac.compare_digest(expected, supplied)


def ptero_request(path, method="GET", payload=None):
    panel = os.environ.get("PTERODACTYL_URL", "").strip().rstrip("/")
    key = os.environ.get("PTERODACTYL_API_KEY", "").strip()

    if not panel or not key:
        return None, 503, "Pterodactyl environment variables are missing"

    if not panel.startswith("https://"):
        return None, 503, "Panel URL must use HTTPS"

    body = None if payload is None else json.dumps(payload).encode("utf-8")

    req = Request(
        panel + path,
        data=body,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/vnd.pterodactyl.v1+json",
            "Content-Type": "application/json",
            "User-Agent": f"PRIME-ZENITH-WORKER/{WORKER_VERSION}",
        },
        method=method,
    )

    try:
        with urlopen(req, timeout=20) as response:
            raw = response.read()
            if not raw:
                return {}, response.status, None
            try:
                return json.loads(raw.decode("utf-8")), response.status, None
            except (ValueError, UnicodeDecodeError):
                return {}, response.status, None

    except HTTPError as exc:
    try:
        details = exc.read().decode("utf-8", errors="replace")[:500]
    except Exception:
        details = ""

    message = f"Pterodactyl returned HTTP {exc.code}"
    if details:
        message += f": {details}"

    return None, exc.code, message

    except (URLError, TimeoutError, OSError):
        return None, 502, "Could not reach Pterodactyl"


@app.get("/")
def home():
    return jsonify({
        "name": "PRIME ZENITH WORKER",
        "status": "online",
        "version": WORKER_VERSION,
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "PRIME ZENITH WORKER",
        "timestamp": int(time.time()),
    })


@app.get("/worker/status")
def worker_status():
    _, status, error = ptero_request("/api/client/account")

    return jsonify({
        "connected": True,
        "execution": True,
        "pterodactyl": {
            "configured": status != 503 or not error,
            "connected": status == 200,
            "http_status": status,
            "message": "Pterodactyl API authentication successful"
            if status == 200 else error,
        },
        "version": WORKER_VERSION,
        "timestamp": int(time.time()),
    })


@app.get("/worker/servers")
def list_servers():
    if not worker_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data, status, error = ptero_request("/api/client/servers")

    if status != 200 or not isinstance(data, dict):
        return jsonify({
            "error": error or "Could not retrieve servers",
            "http_status": status,
        }), 502

    servers = []

    for item in data.get("data", []):
        attrs = item.get("attributes", {})
        servers.append({
            "identifier": attrs.get("identifier"),
            "name": attrs.get("name"),
            "suspended": attrs.get("is_suspended", False),
            "limits": attrs.get("limits", {}),
        })

    return jsonify({"count": len(servers), "servers": servers})


@app.get("/worker/servers/<identifier>/status")
def server_status(identifier):
    if not worker_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    data, status, error = ptero_request(
        f"/api/client/servers/{identifier}/resources"
    )

    if status != 200:
        return jsonify({
            "error": error or "Could not retrieve server status",
            "http_status": status,
        }), 502

    attrs = data.get("attributes", {})
    return jsonify({
        "identifier": identifier,
        "current_state": attrs.get("current_state", "unknown"),
        "is_suspended": attrs.get("is_suspended", False),
        "resources": attrs.get("resources", {}),
    })


@app.post("/worker/servers/<identifier>/power")
def server_power(identifier):
    if not worker_authorized():
        return jsonify({"error": "Unauthorized"}), 401

    payload = request.get_json(silent=True) or {}
    signal = str(payload.get("signal", "")).lower()

    if signal not in {"start", "stop", "restart"}:
        return jsonify({
            "error": "Signal must be start, stop, or restart"
        }), 400

    # Only allow identifiers that look like Pterodactyl short identifiers.
    if not identifier.isalnum() or len(identifier) > 64:
        return jsonify({"error": "Invalid server identifier"}), 400

    _, status, error = ptero_request(
        f"/api/client/servers/{identifier}/power",
        method="POST",
        payload={"signal": signal},
    )

    if status not in (200, 204):
        return jsonify({
            "error": error or "Pterodactyl rejected the power action",
            "http_status": status,
        }), 502

    return jsonify({
        "success": True,
        "identifier": identifier,
        "signal": signal,
        "message": f"{signal.title()} request sent",
    }), 200


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
    )
