import collections
import hashlib
import hmac
import os
import threading
import time
from datetime import datetime, timezone

import requests
from flask import Flask, abort, jsonify, request

app = Flask(__name__)

PATREON_WEBHOOK_SECRET = os.environ.get("PATREON_WEBHOOK_SECRET", "")
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL", "")
PATREON_CREATOR_URL = os.environ.get("PATREON_CREATOR_URL", "https://www.patreon.com/magusferox")

PING_INTERVAL = 10 * 60


def _keep_alive():
    global last_keepalive_ping
    time.sleep(30)
    while True:
        if RENDER_EXTERNAL_URL:
            try:
                requests.get(f"{RENDER_EXTERNAL_URL}/webhook/status", timeout=10)
                last_keepalive_ping = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                print(f"Keep-alive ping sent at {last_keepalive_ping}")
            except Exception as e:
                print(f"Keep-alive ping failed: {e}")
        time.sleep(PING_INTERVAL)


if RENDER_EXTERNAL_URL:
    t = threading.Thread(target=_keep_alive, daemon=True)
    t.start()

MAX_LOG = 50
event_log = collections.deque(maxlen=MAX_LOG)
last_keepalive_ping = None
discord_rate_limit_until = 0.0
_discord_lock = threading.Lock()


def verify_signature(payload, signature):
    mac = hmac.new(
        PATREON_WEBHOOK_SECRET.encode("utf-8"),
        msg=payload,
        digestmod=hashlib.md5,
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


def send_to_discord(title, url, excerpt, image_url=None):
    global discord_rate_limit_until

    with _discord_lock:
        cooldown_remaining = discord_rate_limit_until - time.time()
        if cooldown_remaining > 0:
            mins = int(cooldown_remaining // 60)
            secs = int(cooldown_remaining % 60)
            label = f"{mins}m {secs}s" if mins else f"{secs}s"
            print(f"Discord in cooldown — skipping send, {label} remaining")
            return False, f"Discord cooldown active — {label} remaining"

    embed = {
        "title": title,
        "url": url,
        "description": excerpt + ("..." if excerpt else ""),
        "color": 0xE8350A,
        "footer": {
            "text": "Patreon · Warband",
            "icon_url": "https://c5.patreon.com/external/favicon/apple-touch-icon.png",
        },
        "author": {
            "name": "magusferox on Patreon",
            "url": PATREON_CREATOR_URL,
            "icon_url": "https://c5.patreon.com/external/favicon/apple-touch-icon.png",
        },
    }
    if image_url:
        embed["image"] = {"url": image_url}

    message = {
        "content": "🔥 **New Warband Update!**",
        "embeds": [embed],
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK_URL, json=message, timeout=10)
        if resp.status_code == 429:
            try:
                retry_after = float(resp.json().get("retry_after", 0))
            except Exception:
                retry_after = 0
            if retry_after <= 0:
                retry_after = 60.0
            with _discord_lock:
                discord_rate_limit_until = time.time() + retry_after
            print(f"Discord 429 — cooldown set for {retry_after}s. Body: {resp.text[:200]!r}")
            mins = int(retry_after // 60)
            secs = int(retry_after % 60)
            label = f"{mins}m {secs}s" if mins else f"{secs}s"
            return False, f"Discord rate limited — cooldown set for {label}"
        discord_ok = resp.status_code in (200, 204)
        error = None if discord_ok else f"Discord {resp.status_code}: {resp.text[:120]}"
        return discord_ok, error
    except Exception as e:
        return False, str(e)


def _dispatch_to_discord(title, url, excerpt, image_url):
    discord_ok, error = send_to_discord(title, url, excerpt, image_url)
    log_event(title, url, discord_ok, error)


@app.route("/webhook", methods=["POST"])
def patreon_webhook():
    raw_payload = request.data
    signature = request.headers.get("X-Patreon-Signature", "")

    if not verify_signature(raw_payload, signature):
        log_event("(rejected — bad signature)", "", False, f"Got signature: {signature[:20]}...")
        abort(400)

    data = request.json

    try:
        post = data["data"]
        title = post["attributes"]["title"]
        url = post["attributes"]["url"]
        excerpt = post["attributes"].get("content", "")[:200]
        image_data = post["attributes"].get("image") or {}
        image_url = image_data.get("large_url") or image_data.get("url")
    except Exception as e:
        print("Error parsing Patreon payload:", e)
        log_event("(parse error)", "", False, str(e))
        return "ok"

    threading.Thread(
        target=_dispatch_to_discord,
        args=(title, url, excerpt, image_url),
        daemon=True,
    ).start()
    return "ok"


@app.route("/webhook/test", methods=["POST"])
def test_webhook():
    title = "🧪 Test Post — Warband Webhook"
    url = PATREON_CREATOR_URL
    excerpt = "This is a test event fired from the status page to verify the Discord notification is working correctly."
    discord_ok, error = send_to_discord(title, url, excerpt)
    log_event(f"[TEST] {title}", url, discord_ok, error)
    return jsonify({"ok": discord_ok, "error": error})


@app.route("/webhook/status")
def status_page():
    rows = ""
    for e in event_log:
        badge = (
            '<span style="color:#22c55e;font-weight:600">✓ Sent</span>'
            if e["discord_ok"]
            else '<span style="color:#ef4444;font-weight:600">✗ Failed</span>'
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
    .sub {{ color: #64748b; font-size: 0.85em; margin-bottom: 20px; }}
    .toolbar {{ display: flex; align-items: center; gap: 12px; margin-bottom: 24px; }}
    .btn {{ background: #7c3aed; color: #fff; border: none; border-radius: 8px; padding: 9px 20px; font-size: 0.9em; font-weight: 600; cursor: pointer; transition: background .15s; }}
    .btn:hover {{ background: #6d28d9; }}
    .btn:disabled {{ background: #334155; color: #64748b; cursor: not-allowed; }}
    .result {{ font-size: 0.85em; }}
    .ok {{ color: #22c55e; }}
    .fail {{ color: #ef4444; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; overflow: hidden; }}
    table {{ width: 100%; border-collapse: collapse; }}
    thead th {{ background: #0f172a; padding: 10px 14px; text-align: left; font-size: 0.75em; text-transform: uppercase; letter-spacing: .05em; color: #64748b; border-bottom: 1px solid #334155; }}
    tbody tr {{ border-bottom: 1px solid #1e293b; }}
    tbody tr:hover {{ background: #263348; }}
    tbody tr:last-child {{ border-bottom: none; }}
  </style>
</head>
<body>
  <h1>🔥 Warband Webhook Status</h1>
  <p class="sub">Last {MAX_LOG} events &nbsp;·&nbsp; Auto-refreshes every 30 s &nbsp;·&nbsp; Keep-alive: {"🟢 Last ping " + last_keepalive_ping if last_keepalive_ping else "⏳ First ping in ~30 s" if RENDER_EXTERNAL_URL else "⚪ Not on Render"} &nbsp;·&nbsp; Discord: {("🔴 Cooldown " + (lambda s: f"{int(s//60)}m {int(s%60)}s" if s >= 60 else f"{int(s)}s")(discord_rate_limit_until - time.time())) if discord_rate_limit_until > time.time() else "🟢 Ready"}</p>
  <div class="toolbar">
    <button class="btn" id="testBtn" onclick="sendTest()">Send Test to Discord</button>
    <span class="result" id="testResult"></span>
  </div>
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
  <script>
    const COOLDOWN = 30;
    let cooldownTimer = null;

    function startCooldown(btn) {{
      let remaining = COOLDOWN;
      btn.disabled = true;
      btn.textContent = `Cooldown (${{remaining}}s)`;
      cooldownTimer = setInterval(() => {{
        remaining -= 1;
        if (remaining <= 0) {{
          clearInterval(cooldownTimer);
          btn.disabled = false;
          btn.textContent = 'Send Test to Discord';
        }} else {{
          btn.textContent = `Cooldown (${{remaining}}s)`;
        }}
      }}, 1000);
    }}

    async function sendTest() {{
      const btn = document.getElementById('testBtn');
      const result = document.getElementById('testResult');
      btn.disabled = true;
      btn.textContent = 'Sending...';
      result.textContent = '';
      try {{
        const r = await fetch('/webhook/test', {{ method: 'POST' }});
        const data = await r.json();
        if (data.ok) {{
          result.textContent = '✓ Discord message sent!';
          result.className = 'result ok';
        }} else {{
          result.textContent = '✗ ' + (data.error || 'Failed');
          result.className = 'result fail';
        }}
      }} catch(e) {{
        result.textContent = '✗ Request failed';
        result.className = 'result fail';
      }}
      startCooldown(btn);
      setTimeout(() => location.reload(), 1500);
    }}
  </script>
</body>
</html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port)
