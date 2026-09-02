"""Membership layer: entitlements, overrides, auth flow, webhook handling, member feed."""
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import pytest

from betbot.members.repo import MembersRepo
from betbot.members.stripe_webhook import handle_event, verify_signature


@pytest.fixture
def mrepo(repo) -> MembersRepo:
    return MembersRepo(repo)


class NullNotifier:
    async def send(self, text: str) -> None:
        pass


# ---- entitlements: tiers, switches, overrides ----

def member_row(mrepo, **kwargs):
    member_id = mrepo.create_member(kwargs.pop("email", "m@example.com"), **kwargs)
    return mrepo.get_member(member_id)


def test_tier_defaults(mrepo):
    assert mrepo.features_for(member_row(mrepo, tier="paddock")) == set()
    assert mrepo.features_for(member_row(mrepo, email="a@x.com", tier="member")) == {"selections", "full_log"}
    pro = mrepo.features_for(member_row(mrepo, email="b@x.com", tier="pro"))
    assert {"selections", "full_log", "auto_bet", "bank_tracker", "debrief", "qa"} <= pro


def test_tier_switchboard_flips_live(mrepo):
    m = member_row(mrepo, tier="member")
    assert "auto_bet" not in mrepo.features_for(m)
    mrepo.set_tier_feature("member", "auto_bet", True)   # marketing changes its mind
    assert "auto_bet" in mrepo.features_for(m)
    mrepo.set_tier_feature("member", "auto_bet", False)  # and back
    assert "auto_bet" not in mrepo.features_for(m)


def test_member_overrides_beat_tier(mrepo):
    m = member_row(mrepo, tier="member")
    mrepo.set_member_feature(m["id"], "auto_bet", True)      # comp'd for one member
    assert "auto_bet" in mrepo.features_for(m)
    mrepo.set_member_feature(m["id"], "full_log", False)     # revoked for one member
    assert "full_log" not in mrepo.features_for(m)
    mrepo.set_member_feature(m["id"], "full_log", None)      # back to tier default
    assert "full_log" in mrepo.features_for(m)


def test_inactive_member_loses_everything(mrepo):
    m = member_row(mrepo, tier="pro")
    assert mrepo.features_for(m)
    mrepo.update_member(m["id"], status="past_due")
    assert mrepo.features_for(mrepo.get_member(m["id"])) == set()
    mrepo.update_member(m["id"], status="trialing")
    assert mrepo.features_for(mrepo.get_member(m["id"]))


def test_lifetime_period_persists(mrepo):
    m = member_row(mrepo, tier="pro", billing_period="lifetime")
    assert m["billing_period"] == "lifetime"


# ---- magic links & sessions ----

def test_magic_link_flow(mrepo):
    m = member_row(mrepo)
    token = mrepo.create_magic_link(m["id"])
    assert mrepo.consume_magic_link(token) == m["id"]
    assert mrepo.consume_magic_link(token) is None          # single use
    assert mrepo.consume_magic_link("nonsense") is None
    session = mrepo.create_session(m["id"])
    assert mrepo.session_member(session)["id"] == m["id"]
    mrepo.delete_session(session)
    assert mrepo.session_member(session) is None


def test_expired_magic_link_rejected(mrepo, repo):
    m = member_row(mrepo)
    token = mrepo.create_magic_link(m["id"])
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    repo._exec("UPDATE magic_links SET expires_at=? WHERE token=?", (past, token))
    assert mrepo.consume_magic_link(token) is None


# ---- stripe webhook ----

def sign(payload: bytes, secret: str, ts: int | None = None) -> str:
    ts = ts or int(time.time())
    sig = hmac.new(secret.encode(), f"{ts}.".encode() + payload, hashlib.sha256).hexdigest()
    return f"t={ts},v1={sig}"


def test_signature_verification():
    payload = b'{"ok":true}'
    header = sign(payload, "whsec_test")
    assert verify_signature(payload, header, "whsec_test")
    assert not verify_signature(payload, header, "whsec_other")
    assert not verify_signature(b"tampered", header, "whsec_test")
    assert not verify_signature(payload, sign(payload, "whsec_test", ts=int(time.time()) - 9999),
                                "whsec_test")
    assert not verify_signature(payload, None, "whsec_test")


@pytest.mark.asyncio
async def test_checkout_then_subscription_events(mrepo, monkeypatch):
    from betbot import config
    monkeypatch.setitem(config.tunables().apex.stripe_prices,
                        "price_pro_monthly", {"tier": "pro", "period": "monthly"})

    await handle_event(mrepo, {
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "subscription", "customer": "cus_1",
                            "customer_details": {"email": "new@x.com", "name": "New Member"}}},
    }, NullNotifier())
    m = mrepo.get_member_by_email("new@x.com")
    assert m is not None and m["stripe_customer_id"] == "cus_1"

    await handle_event(mrepo, {
        "type": "customer.subscription.created",
        "data": {"object": {"customer": "cus_1", "id": "sub_1", "status": "trialing",
                            "items": {"data": [{"price": {"id": "price_pro_monthly"}}]}}},
    }, NullNotifier())
    m = mrepo.get_member_by_email("new@x.com")
    assert m["tier"] == "pro" and m["billing_period"] == "monthly" and m["status"] == "trialing"

    await handle_event(mrepo, {
        "type": "customer.subscription.deleted",
        "data": {"object": {"customer": "cus_1", "id": "sub_1", "status": "canceled",
                            "items": {"data": [{"price": {"id": "price_pro_monthly"}}]}}},
    }, NullNotifier())
    m = mrepo.get_member_by_email("new@x.com")
    assert m["status"] == "canceled"
    assert mrepo.features_for(m) == set()


@pytest.mark.asyncio
async def test_lifetime_checkout(mrepo):
    await handle_event(mrepo, {
        "type": "checkout.session.completed",
        "data": {"object": {"mode": "payment", "customer": "cus_life",
                            "metadata": {"tier": "pro", "period": "lifetime"},
                            "customer_details": {"email": "life@x.com"}}},
    }, NullNotifier())
    m = mrepo.get_member_by_email("life@x.com")
    assert m["tier"] == "pro" and m["billing_period"] == "lifetime" and m["status"] == "active"


# ---- member auto-bet feed gating ----

def test_member_feed_gating(repo, mrepo):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from betbot.members.portal import build_portal_router

    app = FastAPI()
    app.include_router(build_portal_router(repo, mrepo))
    client = TestClient(app)

    m = member_row(mrepo, email="feed@x.com", tier="pro")
    token = m["feed_token"]

    # pro but delivery_mode=manual -> no feed
    assert client.get(f"/feed/member/{token}.csv").status_code == 404
    mrepo.update_member(m["id"], delivery_mode="auto")
    response = client.get(f"/feed/member/{token}.csv")
    assert response.status_code == 200
    assert response.text.startswith("RaceDate,RaceTime,Course")

    # tier switch-off kills it live
    mrepo.set_tier_feature("pro", "auto_bet", False)
    assert client.get(f"/feed/member/{token}.csv").status_code == 404
    mrepo.set_tier_feature("pro", "auto_bet", True)

    # canceled member -> dead feed
    mrepo.update_member(m["id"], status="canceled")
    assert client.get(f"/feed/member/{token}.csv").status_code == 404
    mrepo.update_member(m["id"], status="active")

    # token rotation kills the old URL
    new_token = mrepo.rotate_feed_token(m["id"])
    assert client.get(f"/feed/member/{token}.csv").status_code == 404
    assert client.get(f"/feed/member/{new_token}.csv").status_code == 200

    # downloads are logged per member
    rows = repo._all("SELECT * FROM member_feed_downloads WHERE member_id=?", (m["id"],))
    assert len(rows) == 2
