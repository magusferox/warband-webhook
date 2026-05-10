# Patreon Webhook Server

A Python Flask server that receives Patreon webhook events and posts styled messages to Discord.

## Files

| File | Purpose |
|---|---|
| `webhook.py` | Flask server — validates signatures, posts to Discord, logs events |
| `render.yaml` | Render deployment configuration |
| `requirements.txt` | Python dependencies |
| `test_webhook.py` | Sends a test payload to your local server |

---

## Deploy to Render (free, always-on)

### 1. Push this folder to GitHub

Render deploys from a Git repo. Either:

- Push your whole Replit project to GitHub, **or**
- Copy just the `patreon-webhook/` folder into a new GitHub repo

### 2. Create a new Web Service on Render

1. Go to [render.com](https://render.com) and sign in (free account works)
2. Click **New → Web Service**
3. Connect your GitHub repo
4. Render will detect `render.yaml` automatically — confirm the settings:
   - **Runtime:** Python
   - **Build command:** `pip install -r requirements.txt`
   - **Start command:** `gunicorn webhook:app --bind 0.0.0.0:$PORT --workers 1 --timeout 60`

### 3. Add your secrets

In Render's dashboard, go to **Environment** and add:

| Key | Value |
|---|---|
| `PATREON_WEBHOOK_SECRET` | Your Patreon webhook secret |
| `DISCORD_WEBHOOK_URL` | Your Discord webhook URL |

### 4. Deploy

Click **Create Web Service**. Render will build and deploy — takes about 1–2 minutes.

Your permanent URLs will be:
- **Webhook** → `https://patreon-webhook.onrender.com/webhook`
- **Status page** → `https://patreon-webhook.onrender.com/webhook/status`

### 5. Update Patreon

In the [Patreon developer portal](https://www.patreon.com/portal/registration/register-clients), update your webhook URL to:
```
https://patreon-webhook.onrender.com/webhook
```
(Replace `patreon-webhook` with whatever Render names your service.)

---

## Run locally

```bash
pip install -r requirements.txt
export PATREON_WEBHOOK_SECRET=your_secret
export DISCORD_WEBHOOK_URL=your_discord_url
python webhook.py
```

## Test locally

```bash
python test_webhook.py posts:publish
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook` | Receives Patreon events |
| `GET` | `/webhook/status` | Live event log (last 50 events) |

---

## Note on Render's free plan

Render free web services **spin down after 15 minutes of inactivity**. For a webhook receiver that only fires when Patreon posts, this means the first request after a quiet period may time out (Patreon will retry).

To keep it always-on, either:
- Upgrade to Render's **Starter** plan ($7/month), or
- Add a free uptime monitor (e.g. [UptimeRobot](https://uptimerobot.com)) that pings `/webhook/status` every 10 minutes to prevent spin-down
