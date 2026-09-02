"""Stripe webhook: billing is the source of truth for tier/period/status.

Configure in Stripe Dashboard -> Developers -> Webhooks -> endpoint
POST {base_url}/webhooks/stripe with events:
  customer.subscription.created / updated / deleted, checkout.session.completed

Mapping from Stripe price IDs to (tier, period) lives in config/settings.yaml
under apex.stripe_prices — marketing can add/repoint products without code.
Lifetime deals are one-off Payment Links carrying metadata {tier, period:lifetime}.
Signature verification is implemented directly (HMAC-SHA256, Stripe v1 scheme).
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time

from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse

from betbot.config import secrets, tunables
from betbot.members.repo import MembersRepo

log = logging.getLogger(__name__)

STATUS_MAP = {
    "active": "active", "trialing": "trialing", "past_due": "past_due",
    "canceled": "canceled", "unpaid": "past_due", "paused": "paused",
    "incomplete": "past_due", "incomplete_expired": "canceled",
}


def verify_signature(payload: bytes, header: str | None, secret: str,
                     tolerance_seconds: int = 300, now: float | None = None) -> bool:
    if not header:
        return False
    parts = dict(p.split("=", 1) for p in header.split(",") if "=" in p)
    timestamp, signature = parts.get("t"), parts.get("v1")
    if not timestamp or not signature:
        return False
    try:
        if abs((now or time.time()) - int(timestamp)) > tolerance_seconds:
            return False
    except ValueError:
        return False
    expected = hmac.new(secret.encode(), f"{timestamp}.".encode() + payload,
                        hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _price_mapping(price_id: str) -> dict | None:
    return tunables().apex.stripe_prices.get(price_id)


async def handle_event(mrepo: MembersRepo, event: dict, notifier=None) -> str:
    etype = event.get("type", "")
    obj = event.get("data", {}).get("object", {})

    if etype in ("customer.subscription.created", "customer.subscription.updated",
                 "customer.subscription.deleted"):
        customer_id = obj.get("customer")
        items = obj.get("items", {}).get("data", [])
        price_id = items[0].get("price", {}).get("id") if items else None
        mapping = _price_mapping(price_id) if price_id else None
        status = ("canceled" if etype.endswith("deleted")
                  else STATUS_MAP.get(obj.get("status", ""), "past_due"))
        member = mrepo.get_member_by_stripe_customer(customer_id) if customer_id else None
        if member is None:
            log.warning("subscription event for unknown customer %s (price %s) — "
                        "waiting for checkout.session.completed", customer_id, price_id)
            return "unknown-customer"
        fields: dict = {"status": status, "stripe_subscription_id": obj.get("id")}
        if mapping:
            fields.update(tier=mapping["tier"], billing_period=mapping["period"])
        mrepo.update_member(member["id"], **fields)
        return f"member {member['id']} -> {status}"

    if etype == "checkout.session.completed":
        email = (obj.get("customer_details") or {}).get("email") or obj.get("customer_email")
        if not email:
            return "no-email"
        name = (obj.get("customer_details") or {}).get("name")
        customer_id = obj.get("customer")
        metadata = obj.get("metadata") or {}
        if obj.get("mode") == "payment" and metadata.get("period") == "lifetime":
            tier = metadata.get("tier", "pro")
            member_id = mrepo.upsert_member_from_billing(
                email, tier=tier, billing_period="lifetime", status="active",
                stripe_customer_id=customer_id, name=name)
            if notifier:
                await notifier.send(f"💎 Lifetime {tier} member: {email}")
            return f"lifetime member {member_id}"
        # Subscription checkout: create/attach the member; the subscription
        # event that follows carries price -> tier/period.
        member_id = mrepo.upsert_member_from_billing(
            email, tier="paddock", billing_period="monthly", status="active",
            stripe_customer_id=customer_id, name=name)
        if notifier:
            await notifier.send(f"🎉 New checkout: {email}")
        return f"member {member_id} checkout"

    return "ignored"


def build_stripe_router(mrepo: MembersRepo, notifier) -> APIRouter:
    router = APIRouter()

    @router.post("/webhooks/stripe")
    async def stripe_webhook(request: Request) -> PlainTextResponse:
        secret = secrets().stripe_webhook_secret
        if not secret:
            return PlainTextResponse("webhook not configured", status_code=503)
        payload = await request.body()
        if not verify_signature(payload, request.headers.get("stripe-signature"), secret):
            return PlainTextResponse("bad signature", status_code=400)
        try:
            event = json.loads(payload)
        except ValueError:
            return PlainTextResponse("bad payload", status_code=400)
        outcome = await handle_event(mrepo, event, notifier)
        log.info("stripe %s: %s", event.get("type"), outcome)
        return PlainTextResponse("ok")

    return router
