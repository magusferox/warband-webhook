"""
Send a test Patreon webhook payload to your local server.

Usage:
    python test_webhook.py [event_type]

    event_type defaults to "members:pledge:create"

Examples:
    python test_webhook.py members:create
    python test_webhook.py members:pledge:delete
    python test_webhook.py posts:publish
"""

import hashlib
import hmac
import json
import os
import sys

import requests

SERVER_URL = os.environ.get("WEBHOOK_URL", "http://localhost:8080/webhook")
SECRET = os.environ.get("PATREON_WEBHOOK_SECRET", "")

SAMPLE_PAYLOADS = {
    "members:create": {
        "data": {
            "id": "member-001",
            "type": "member",
            "attributes": {
                "full_name": "Jane Patron",
                "email": "jane@example.com",
                "patron_status": "active_patron",
                "currently_entitled_amount_cents": 500,
                "lifetime_support_cents": 500,
                "pledge_relationship_start": "2026-05-10T00:00:00.000+00:00",
            },
        },
        "included": [
            {
                "type": "user",
                "attributes": {
                    "full_name": "Jane Patron",
                    "email": "jane@example.com",
                    "url": "https://www.patreon.com/user?u=12345",
                },
            }
        ],
    },
    "members:pledge:create": {
        "data": {
            "id": "member-002",
            "type": "member",
            "attributes": {
                "full_name": "Bob Supporter",
                "email": "bob@example.com",
                "patron_status": "active_patron",
                "currently_entitled_amount_cents": 1000,
                "lifetime_support_cents": 1000,
                "pledge_relationship_start": "2026-05-10T00:00:00.000+00:00",
            },
        },
        "included": [],
    },
    "members:pledge:delete": {
        "data": {
            "id": "member-003",
            "type": "member",
            "attributes": {
                "full_name": "Alice Former",
                "email": "alice@example.com",
                "patron_status": "former_patron",
                "currently_entitled_amount_cents": 0,
                "lifetime_support_cents": 2000,
                "pledge_relationship_start": "2025-01-01T00:00:00.000+00:00",
            },
        },
        "included": [],
    },
    "posts:publish": {
        "data": {
            "id": "post-001",
            "type": "post",
            "attributes": {
                "title": "Exclusive Update for Patrons",
                "url": "https://www.patreon.com/posts/exclusive-update-123456",
                "content": "Thank you for your support!",
                "published_at": "2026-05-10T12:00:00.000+00:00",
            },
        },
        "included": [],
    },
}


def send_test(event_type: str):
    payload = SAMPLE_PAYLOADS.get(event_type)
    if payload is None:
        print(f"No sample payload for event type '{event_type}'.")
        print(f"Available: {', '.join(SAMPLE_PAYLOADS.keys())}")
        sys.exit(1)

    body = json.dumps(payload).encode("utf-8")

    if SECRET:
        sig = hmac.new(SECRET.encode("utf-8"), body, hashlib.md5).hexdigest()
    else:
        sig = ""
        print("Warning: PATREON_WEBHOOK_SECRET not set — sending without signature")

    headers = {
        "Content-Type": "application/json",
        "X-Patreon-Event": event_type,
        "X-Patreon-Signature": sig,
    }

    print(f"Sending '{event_type}' to {SERVER_URL} ...")
    response = requests.post(SERVER_URL, data=body, headers=headers, timeout=10)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")


if __name__ == "__main__":
    event = sys.argv[1] if len(sys.argv) > 1 else "members:pledge:create"
    send_test(event)
