import os
import time
from flask import Flask, jsonify
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

app = Flask(__name__)


def check_pterodactyl():
    panel_url = os.environ.get("PTERODACTYL_URL", "").rstrip("/")
    api_key = os.environ.get("PTERODACTYL_API_KEY", "")

    if not panel_url or not api_key:
        return {
            "configured": False,
            "connected": False,
            "message": "Pterodactyl credentials are missing"
        }

    request = Request(
        f"{panel_url}/api/client/account",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
        },
        method="GET",
    )

    try:
        with urlopen(request, timeout=10) as response:
            if response.status == 200:
                return {
                    "configured": True,
                    "connected": True,
                    "message": "Pterodactyl authentication successful"
                }

            return {
                "configured": True,
                "connected": False,
                "message": "Unexpected response from Pterodactyl"
            }

    except HTTPError as error:
    try:
        details = error.read().decode("utf-8", errors="replace")[:300]
    except Exception:
        details = "No response details available"

    return {
        "configured": True,
        "connected": False,
        "http_status": error.code,
        "message": "Pterodactyl rejected the request",
        "details": details
    }

    except (URLError, TimeoutError, OSError):
        return {
            "configured": True,
            "connected": False,
            "message": "Could not reach Pterodactyl"
        }


@app.get("/")
def home():
    return jsonify({
        "name": "PRIME ZENITH WORKER",
        "status": "online",
        "version": "2.1.0"
    })


@app.get("/worker/status")
def status():
    return jsonify({
        "connected": True,
        "execution": True,
        "runtime": {
            "node": True,
            "python": True
        },
        "pterodactyl": check_pterodactyl(),
        "timestamp": int(time.time())
    })


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
