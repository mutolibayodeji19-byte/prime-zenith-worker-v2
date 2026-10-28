import os
import time
import json

from flask import Flask, jsonify
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__)
WORKER_VERSION = "2.2.0"


def ptero_request(path):
    panel = os.environ.get("PTERODACTYL_URL", "").strip().rstrip("/")
    key = os.environ.get("PTERODACTYL_API_KEY", "").strip()

    if not panel or not key:
        return None, 0, "Pterodactyl environment variables are missing"

    if not panel.startswith("https://"):
        return None, 0, "Panel URL must use HTTPS"

    request = Request(
        panel + path,
        headers={
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": f"PRIME-ZENITH-WORKER/{WORKER_VERSION}",
        },
    )

    try:
        with urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
            return json.loads(body) if body else {}, response.status, None
    except HTTPError as exc:
        return None, exc.code, "Pterodactyl API request failed"
    except (URLError, TimeoutError, OSError):
        return None, 0, "Could not reach Pterodactyl"
    except (ValueError, json.JSONDecodeError):
        return None, 0, "Invalid response from Pterodactyl"


def check_pterodactyl():
    data, status, error = ptero_request("/api/client/account")

    return {
        "configured": status != 0 or bool(
            os.environ.get("PTERODACTYL_URL")
            and os.environ.get("PTERODACTYL_API_KEY")
        ),
        "connected": status == 200,
        "http_status": status or None,
        "message": "Pterodactyl API authentication successful"
        if status == 200 else error,
    }


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
    return jsonify({
        "connected": True,
        "execution": True,
        "runtime": {"node": True, "python": True},
        "pterodactyl": check_pterodactyl(),
        "timestamp": int(time.time()),
    })


@app.get("/worker/servers")
def list_servers():
    # This read-only diagnostic endpoint must not expose server details publicly.
    expected = os.environ.get("WORKER_KEY", "").strip()
    supplied = __import__("flask").request.headers.get(
        "X-Worker-Key", ""
    ).strip()

    if not expected or supplied != expected:
        return jsonify({"error": "Unauthorized"}), 401

    data, status, error = ptero_request("/api/client")

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
            "status": attrs.get("status", "unknown"),
            "suspended": attrs.get("is_suspended", False),
            "installing": attrs.get("is_installing", False),
        })

    return jsonify({"count": len(servers), "servers": servers})


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000)),
        )
