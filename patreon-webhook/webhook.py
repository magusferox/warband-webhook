import collections
import hashlib
import hmac
import os
from datetime import datetime, timezone

import requests
from flask import Flask, abort, jsonify, request

app = Flask(__name__)

PATREON_WEBHOOK_SECRET = os.environ.get("PATREON_WEBHOOK_SECRET", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

MAX_LOG = 50
event_log = collections.deque(maxlen=MAX_LOG)


def verify_signature(payload, signature):
    mac = hmac.new(
        PATREON_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.sha256,
    )
    expected = mac.hexdigest()
    return hmac.compare_digest(expected, signature)


def log_event(title, url, discord_ok, error=None):
    event_log.appendleft({
        "time": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "title": title,
        "url": url,
        "discord_ok": discord_ok,
        "error": error,
    })


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
        log_event("(parse error)", "", False, str(e))
        return "ok"

    message = {
        "content": (
            f"🔥 **New Warband Update!** 🔥\n"
            f"**{title}**\n"
            f"🔗 {url}\n"
            f"📝 {excerpt}..."
        )
    }

    discord_ok = False
    error = None
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=message, timeout=10)
        discord_ok = resp.status_code in (200, 204)
        if not discord_ok:
            error = f"Discord returned {resp.status_code}"
    except Exception as e:
        error = str(e)

    log_event(title, url, discord_ok, error)
    return "ok"


@app.route("/webhook/status")
def status_page():
    rows = ""
    for e in event_log:
        badge = (
            '<span style="color:#22c55e;font-weight:600">✓ Sent</span>'
            if e["discord_ok"]
            else f'<span style="color:#ef4444;font-weight:600">✗ Failed</span>'
        )
        error_cell = f'<span style="color:#ef4444;font-size:0.8em">{e["error"]}</span>' if e["error"] else ""
        title_cell = (
            f'<a href="{e["url"]}" target="_blank" style="color:#c084fc;text-decoration:none">{e["title"]}</a>'
            if e["url"]
            else e["title"]
        )
        rows += f"""
        <tr>
          <td style="padding:10px 14px;color:#94a3b8;font-size:0.85em;white-space:nowrap">{e["time"]}</td>
          <td style="padding:10px 14px">{title_cell}</td>
          <td style="padding:10px 14px;text-align:center">{badge}<br>{error_cell}</td>
        </tr>"""

    empty = "" if event_log else """
        <tr>
          <td colspan="3" style="padding:32px;text-align:center;color:#64748b">
            No events received yet. Waiting for Patreon...
          </td>
        </tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <meta http-equiv="refresh" content="30">
  <title>Webhook Status</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ background: #0f172a; color: #e2e8f0; font-family: system-ui, sans-serif; padding: 32px 16px; }}
    h1 {{ font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }}
    .sub {{ color: #64748b; font-size: 0.85em; margin-bottom: 28px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ background: #0f172a; padding: 10px 14px; text-align: left; font-size: 0.75em; text-transform: uppercase; letter-spacing: .05em; color: #64748b; border-bottom: 1px solid #334155; }}
    tbody tr {{ border-bottom: 1px solid #1e293b; }}
    tbody tr:hover {{ background: #263348; }}
    tbody tr:last-child {{ border-bottom: none; }}
    .pill {{ display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 0.75em; font-weight: 600; }}
  </style>
</head>
<body>
  <h1>🔥 Warband Webhook Status</h1>
  <p class="sub">Last {MAX_LOG} events &nbsp;·&nbsp; Auto-refreshes every 30 s</p>
  <div class="card">
    <table>
      <thead>
        <tr>
          <th>Time</th>
          <th>Post</th>
          <th style="text-align:center">Discord</th>
        </tr>
      </thead>
      <tbody>
        {rows}{empty}
      </tbody>
    </table>
  </div>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
