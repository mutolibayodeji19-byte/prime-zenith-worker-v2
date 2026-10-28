import os
import time

from flask import Flask, jsonify
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


app = Flask(__name__)

WORKER_VERSION = "2.1.1"


def check_pterodactyl():
    """
    Check whether the worker can authenticate
    with the Pterodactyl Client API.
    """

    panel_url = os.environ.get(
        "PTERODACTYL_URL", ""
    ).strip().rstrip("/")

    api_key = os.environ.get(
        "PTERODACTYL_API_KEY", ""
    ).strip()

    if not panel_url or not api_key:
        return {
            "configured": False,
            "connected": False,
            "message": "Required environment variables are missing"
        }

    if not panel_url.startswith("https://"):
        return {
            "configured": True,
            "connected": False,
            "message": "Panel URL must use HTTPS"
        }

    endpoint = f"{panel_url}/api/client/account"

    request = Request(
        endpoint,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "PRIME-ZENITH-WORKER/2.1.1"
        },
        method="GET"
    )

    try:
        with urlopen(request, timeout=15) as response:
            status_code = response.status

            if status_code == 200:
                return {
                    "configured": True,
                    "connected": True,
                    "http_status": 200,
                    "message": "Pterodactyl API authentication successful"
                }

            return {
                "configured": True,
                "connected": False,
                "http_status": status_code,
                "message": "Unexpected response from Pterodactyl"
            }

    except HTTPError as error:
        # Read a short error message for troubleshooting.
        try:
            response_body = error.read(512).decode(
                "utf-8", errors="replace"
            )

            # Avoid returning a potentially large HTML page.
            details = " ".join(response_body.split())[:200]

        except Exception:
            details = "No response details available"

        return {
            "configured": True,
            "connected": False,
            "http_status": error.code,
            "message": "Pterodactyl rejected the request",
            "details": details
        }

    except (URLError, TimeoutError, OSError) as error:
        reason = getattr(error, "reason", None)

        if isinstance(reason, TimeoutError):
            message = "Pterodactyl connection timed out"
        elif isinstance(error, TimeoutError):
            message = "Pterodactyl connection timed out"
        else:
            message = "Could not reach Pterodactyl"

        return {
            "configured": True,
            "connected": False,
            "message": message
        }

    except Exception:
        app.logger.exception(
            "Unexpected Pterodactyl connection error"
        )

        return {
            "configured": True,
            "connected": False,
            "message": "Unexpected connection error"
        }


@app.get("/")
def home():
    return jsonify({
        "name": "PRIME ZENITH WORKER",
        "status": "online",
        "version": WORKER_VERSION
    })


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "service": "PRIME ZENITH WORKER",
        "timestamp": int(time.time())
    })


@app.get("/worker/status")
def worker_status():
    pterodactyl = check_pterodactyl()

    return jsonify({
        "connected": True,
        "execution": True,
        "runtime": {
            "node": True,
            "python": True
        },
        "pterodactyl": pterodactyl,
        "timestamp": int(time.time())
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))

    app.run(
        host="0.0.0.0",
        port=port
    )
