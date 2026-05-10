import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

from flask import Flask, abort, jsonify, request

from handlers import handle_event

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

PATREON_WEBHOOK_SECRET = os.environ.get("PATREON_WEBHOOK_SECRET", "")


def verify_signature(payload_bytes: bytes, signature_header: str) -> bool:
    if not PATREON_WEBHOOK_SECRET:
        logger.warning("PATREON_WEBHOOK_SECRET not set — skipping signature verification")
        return True
    if not signature_header:
        return False
    expected = hmac.new(
        PATREON_WEBHOOK_SECRET.encode("utf-8"),
        payload_bytes,
        hashlib.md5,
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


@app.route("/webhook", methods=["POST"])
def patreon_webhook():
    payload_bytes = request.get_data()
    signature = request.headers.get("X-Patreon-Signature", "")
    event_type = request.headers.get("X-Patreon-Event", "unknown")

    if not verify_signature(payload_bytes, signature):
        logger.warning("Invalid signature — rejecting request")
        abort(403)

    try:
        payload = json.loads(payload_bytes)
    except json.JSONDecodeError:
        logger.error("Failed to parse JSON payload")
        abort(400)

    logger.info("Received Patreon event: %s", event_type)

    try:
        result = handle_event(event_type, payload)
        logger.info("Handler result: %s", result)
    except Exception as exc:
        logger.exception("Handler raised an exception: %s", exc)
        return jsonify({"status": "error", "message": str(exc)}), 500

    return jsonify({"status": "ok", "event": event_type, "result": result}), 200


@app.route("/healthz", methods=["GET"])
def health():
    return jsonify({"status": "ok", "time": datetime.utcnow().isoformat()}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info("Starting Patreon webhook server on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=False)
