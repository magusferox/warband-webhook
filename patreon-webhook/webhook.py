import hashlib
import hmac
import json
import os

import requests
from flask import Flask, abort, request

app = Flask(__name__)

PATREON_WEBHOOK_SECRET = os.environ.get("PATREON_WEBHOOK_SECRET", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")


def verify_signature(payload, signature):
    mac = hmac.new(
        PATREON_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)


@app.route("/webhook", methods=["POST"])
def patreon_webhook():
    raw_payload = request.data
    signature = request.headers.get("X-Patreon-Signature", "")

    if not verify_signature(raw_payload, signature):
        abort(400)

    data = request.json

    try:
        post = data["data"]
        title = post["attributes"]["title"]
        url = post["attributes"]["url"]
        excerpt = post["attributes"].get("content", "")[:200]
    except Exception as e:
        print("Error parsing Patreon payload:", e)
        return "ok"

    message = {
        "content": (
            f"🔥 **New Warband Update!** 🔥\n"
            f"**{title}**\n"
            f"🔗 {url}\n"
            f"📝 {excerpt}..."
        )
    }

    requests.post(DISCORD_WEBHOOK_URL, json=message)

    return "ok"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
