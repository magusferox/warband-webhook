"""
Patreon webhook event handlers.

Each function receives the full Patreon webhook payload (a dict) and should
return a string or dict describing what was done.

Event types emitted by Patreon:
  members:create          — a new member joins (free or paid)
  members:update          — a member's details change
  members:delete          — a member is removed
  members:pledge:create   — a new paid pledge is created
  members:pledge:update   — a pledge amount or tier changes
  members:pledge:delete   — a pledge is cancelled
  posts:publish           — a new post is published
"""

import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helper: extract commonly used fields from a member payload
# ---------------------------------------------------------------------------

def _extract_member(payload: dict) -> dict:
    data = payload.get("data", {})
    attrs = data.get("attributes", {})
    included = payload.get("included", [])

    user_info = {}
    for item in included:
        if item.get("type") == "user":
            user_attrs = item.get("attributes", {})
            user_info = {
                "full_name": user_attrs.get("full_name"),
                "email": user_attrs.get("email"),
                "url": user_attrs.get("url"),
            }
            break

    return {
        "member_id": data.get("id"),
        "full_name": attrs.get("full_name"),
        "email": attrs.get("email"),
        "patron_status": attrs.get("patron_status"),
        "currently_entitled_amount_cents": attrs.get("currently_entitled_amount_cents"),
        "lifetime_support_cents": attrs.get("lifetime_support_cents"),
        "pledge_relationship_start": attrs.get("pledge_relationship_start"),
        "user": user_info,
    }


# ---------------------------------------------------------------------------
# Core event handlers — customise the body of each function
# ---------------------------------------------------------------------------

def on_member_create(payload: dict) -> str:
    member = _extract_member(payload)
    logger.info("New member: %s (%s)", member["full_name"], member["email"])

    # TODO: add your custom logic here, e.g.:
    #   - send a welcome email
    #   - add to a mailing list
    #   - grant access to a Discord server

    return f"New member welcomed: {member['full_name']}"


def on_member_update(payload: dict) -> str:
    member = _extract_member(payload)
    logger.info(
        "Member updated: %s — status=%s amount=%s cents",
        member["full_name"],
        member["patron_status"],
        member["currently_entitled_amount_cents"],
    )

    # TODO: sync updated member data to your database or external service

    return f"Member updated: {member['full_name']}"


def on_member_delete(payload: dict) -> str:
    member = _extract_member(payload)
    logger.info("Member deleted: %s", member["full_name"])

    # TODO: revoke access, update your records, etc.

    return f"Member removed: {member['full_name']}"


def on_pledge_create(payload: dict) -> str:
    member = _extract_member(payload)
    amount = (member["currently_entitled_amount_cents"] or 0) / 100
    logger.info(
        "New pledge: %s — $%.2f/month",
        member["full_name"],
        amount,
    )

    # TODO: unlock paid content, update subscription records, thank the patron

    return f"Pledge created: {member['full_name']} (${amount:.2f}/month)"


def on_pledge_update(payload: dict) -> str:
    member = _extract_member(payload)
    amount = (member["currently_entitled_amount_cents"] or 0) / 100
    logger.info(
        "Pledge updated: %s — now $%.2f/month",
        member["full_name"],
        amount,
    )

    # TODO: adjust tier access, update records

    return f"Pledge updated: {member['full_name']} (now ${amount:.2f}/month)"


def on_pledge_delete(payload: dict) -> str:
    member = _extract_member(payload)
    logger.info("Pledge cancelled: %s", member["full_name"])

    # TODO: revoke paid-only access, send a cancellation email

    return f"Pledge cancelled: {member['full_name']}"


def on_post_publish(payload: dict) -> str:
    data = payload.get("data", {})
    attrs = data.get("attributes", {})
    title = attrs.get("title", "Untitled")
    url = attrs.get("url", "")
    logger.info("New post published: %s — %s", title, url)

    # TODO: notify subscribers, push to social media, etc.

    return f"Post published: {title}"


# ---------------------------------------------------------------------------
# Dispatcher — routes event types to the correct handler
# ---------------------------------------------------------------------------

_HANDLERS = {
    "members:create": on_member_create,
    "members:update": on_member_update,
    "members:delete": on_member_delete,
    "members:pledge:create": on_pledge_create,
    "members:pledge:update": on_pledge_update,
    "members:pledge:delete": on_pledge_delete,
    "posts:publish": on_post_publish,
}


def handle_event(event_type: str, payload: dict) -> str:
    handler = _HANDLERS.get(event_type)
    if handler is None:
        logger.warning("No handler registered for event type: %s", event_type)
        return f"Unhandled event type: {event_type}"
    return handler(payload)
