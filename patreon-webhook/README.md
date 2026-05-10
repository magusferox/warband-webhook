# Patreon Webhook Server

A Python Flask server that receives and handles Patreon webhook events.

## Files

| File | Purpose |
|---|---|
| `webhook.py` | Flask server — validates signatures and routes events |
| `handlers.py` | Your custom logic for each event type |
| `test_webhook.py` | Sends a test payload to your local server |

## Setup

### 1. Set your Patreon webhook secret

In Patreon's portal, create a webhook and copy the **secret**.
Then set it as an environment variable:

```bash
export PATREON_WEBHOOK_SECRET=your_secret_here
```

In Replit, add it in the **Secrets** tab.

### 2. Run the server

```bash
cd patreon-webhook
python webhook.py
```

The server starts on port `8080` by default. Override with `PORT`:

```bash
PORT=3000 python webhook.py
```

### 3. Point Patreon at your server

In [Patreon's developer portal](https://www.patreon.com/portal/registration/register-clients), set your webhook URL to:

```
https://<your-domain>/webhook
```

If running locally, use [ngrok](https://ngrok.com/) to expose your server:

```bash
ngrok http 8080
# Then use the https URL ngrok gives you
```

## Handled event types

| Event | Handler |
|---|---|
| `members:create` | `on_member_create` |
| `members:update` | `on_member_update` |
| `members:delete` | `on_member_delete` |
| `members:pledge:create` | `on_pledge_create` |
| `members:pledge:update` | `on_pledge_update` |
| `members:pledge:delete` | `on_pledge_delete` |
| `posts:publish` | `on_post_publish` |

## Customising handlers

Open `handlers.py` and fill in the `TODO` sections in each handler function.
Each handler receives the full Patreon payload and should return a string
describing what was done.

Example — send a Discord notification on new pledge:

```python
import requests

def on_pledge_create(payload: dict) -> str:
    member = _extract_member(payload)
    amount = (member["currently_entitled_amount_cents"] or 0) / 100

    requests.post(
        os.environ["DISCORD_WEBHOOK_URL"],
        json={"content": f"New patron: {member['full_name']} (${amount:.2f}/month)!"},
    )

    return f"Notified Discord: {member['full_name']}"
```

## Testing locally

While the server is running in one terminal, run this in another:

```bash
cd patreon-webhook

# Test a new pledge
python test_webhook.py members:pledge:create

# Test a cancellation
python test_webhook.py members:pledge:delete

# Test a new post
python test_webhook.py posts:publish
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/webhook` | Receives Patreon events |
| `GET` | `/healthz` | Health check |
