"""Apex growth layer: Stripe ordering + welcome, Paddock join/unsubscribe, the
public site API, the official log's stake-cap guard, and the Sunday email body."""
from datetime import date, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from betbot import config
from betbot.apex import emails
from betbot.apex.public import build_public_router
from betbot.apex.store import ApexStore
from betbot.members import mailer
from betbot.members.admin import build_admin_router
from betbot.members.repo import MembersRepo
from betbot.members.stripe_webhook import handle_event


class NullNotifier:
    async def send(self, text: str) -> None:
        pass


@pytest.fixture
def mrepo(repo) -> MembersRepo:
    return MembersRepo(repo)


@pytest.fixture
def store(repo) -> ApexStore:
    return ApexStore(repo)


@pytest.fixture
def outbox(monkeypatch):
    sent: list[dict] = []

    def fake_send(to, subject, body, *, unsubscribe_url=None):
        sent.append({"to": to, "subject": subject, "body": body, "unsub": unsubscribe_url})
        return True

    monkeypatch.setattr(mailer, "send_email", fake_send)
    return sent


@pytest.fixture
def pro_price(monkeypatch):
    monkeypatch.setitem(config.tunables().apex.stripe_prices,
                        "price_pro_monthly", {"tier": "pro", "period": "monthly"})


def sub_event(kind="created", status="active"):
    return {"type": f"customer.subscription.{kind}",
            "data": {"object": {"customer": "cus_9", "id": "sub_9", "status": status,
                                "items": {"data": [{"price": {"id": "price_pro_monthly"}}]}}}}


CHECKOUT = {"type": "checkout.session.completed",
            "data": {"object": {"mode": "subscription", "customer": "cus_9",
                                "customer_details": {"email": "early@x.com", "name": "Early"}}}}


# ---- Stripe: order-independent, welcome once ----

@pytest.mark.asyncio
async def test_subscription_event_before_checkout_is_not_lost(mrepo, pro_price, outbox):
    assert await handle_event(mrepo, sub_event(), NullNotifier()) == "stashed"
    await handle_event(mrepo, CHECKOUT, NullNotifier())
    m = mrepo.get_member_by_email("early@x.com")
    assert m["tier"] == "pro" and m["status"] == "active" and m["stripe_subscription_id"] == "sub_9"
    assert mrepo.pop_stashed_subscription("cus_9") is None


@pytest.mark.asyncio
async def test_welcome_email_sent_once_when_paid(mrepo, pro_price, outbox):
    await handle_event(mrepo, CHECKOUT, NullNotifier())
    assert outbox == []  # still on the free tier until the subscription lands
    await handle_event(mrepo, sub_event(), NullNotifier())
    await handle_event(mrepo, sub_event("updated"), NullNotifier())
    welcomes = [e for e in outbox if e["subject"].startswith("You're in")]
    assert len(welcomes) == 1 and welcomes[0]["to"] == "early@x.com"
    assert "/auth/verify?token=" in welcomes[0]["body"]
    assert mrepo.get_member_by_email("early@x.com")["welcomed_at"] is not None


@pytest.mark.asyncio
async def test_no_welcome_while_payment_incomplete(mrepo, pro_price, outbox):
    await handle_event(mrepo, sub_event(status="incomplete"), NullNotifier())
    await handle_event(mrepo, CHECKOUT, NullNotifier())
    assert outbox == []
    await handle_event(mrepo, sub_event("updated", status="active"), NullNotifier())
    assert len(outbox) == 1


# ---- the Paddock ----

@pytest.fixture
def client(repo, mrepo, store, monkeypatch):
    monkeypatch.setattr(config.secrets(), "paddock_shared_secret", "k" * 32)
    monkeypatch.setattr(config.secrets(), "dashboard_password", "pw")
    app = FastAPI()
    app.include_router(build_public_router(mrepo, store, NullNotifier()))
    app.include_router(build_admin_router(mrepo, repo, NullNotifier()))
    return TestClient(app)


def test_paddock_join_needs_the_shared_secret(client, outbox):
    assert client.post("/public/paddock", data={"email": "a@x.com"}).status_code == 403
    assert client.post("/public/paddock", data={"email": "a@x.com"},
                       headers={"X-Apex-Key": "wrong"}).status_code == 403
    assert outbox == []


def test_paddock_join_welcomes_once_and_unsubscribe_needs_a_post(client, mrepo, outbox):
    headers = {"X-Apex-Key": "k" * 32}
    r = client.post("/public/paddock", data={"email": "p@x.com"}, headers=headers)
    assert r.json() == {"ok": True, "welcomed": True}
    client.post("/public/paddock", data={"email": "P@x.com"}, headers=headers)
    assert len(outbox) == 1 and "bank-builder.html" in outbox[0]["body"]
    unsub = outbox[0]["unsub"]
    token = unsub.rsplit("/", 1)[1]
    assert [m["email"] for m in mrepo.weekly_email_list()] == ["p@x.com"]

    client.get(f"/unsubscribe/{token}")             # a mail scanner pre-fetching the link
    assert mrepo.weekly_email_list() != []
    client.post(f"/unsubscribe/{token}")
    assert mrepo.weekly_email_list() == []


def test_unsubscribe_page_escapes_the_token(client):
    body = client.get("/unsubscribe/<script>x</script>").text
    assert "<script>x" not in body


# ---- the public site API ----

def test_public_log_hides_todays_open_selections(client, store):
    today = date.today().isoformat()
    store.add_log_row(race_date=today, system="Apex Anchor", selection="Secret Horse", venue=None,
                      event_time=None, market="Place", price_x100=160, stake_pence=None,
                      stake_pct=3, reasoning=None)
    rows = client.get("/public/log.json").json()["rows"]
    names = [r["selection"] for r in rows]
    assert "Secret Horse" not in names
    assert "Kanzi" in names and "Galyx" in names        # launch week, as published
    kanzi = next(r for r in rows if r["selection"] == "Kanzi")
    assert kanzi["pnl"] == "−£122.35" and kanzi["result"] == "lost"


def test_public_stats_and_page_counts(client, store):
    assert client.get("/public/stats.json").json()["founding_remaining"] == 50
    client.get("/public/hit", params={"p": "/", "r": "https://t.co/abc", "us": "x"})
    client.get("/public/hit", params={"p": "/", "r": "https://apexcode.uk/#log"})
    assert store.views_since(1) == 2
    sources = {s["source"] for s in store.top_sources(1)}
    assert sources == {"x", "(direct)"}


# ---- the official log ----

AUTH = ("betbot", "pw")


def test_log_refuses_a_stake_above_the_published_cap(client, store):
    form = {"race_date": "2026-11-02", "system": "Apex Anchor", "selection": "Over The Top",
            "price": "1.60", "stake": "51.19", "stake_pct": "5"}
    r = client.post("/admin/log/add", data=form, auth=AUTH, follow_redirects=False)
    assert "above%20the%20published%203%25%20cap" in r.headers["location"]
    assert not [x for x in store.log_rows() if x["selection"] == "Over The Top"]

    client.post("/admin/log/add", data={**form, "stake_pct": "3", "stake": "30.71"}, auth=AUTH)
    row = next(x for x in store.log_rows() if x["selection"] == "Over The Top")
    assert row["result"] == "pending" and row["stake_pct"] == 3


def test_settling_needs_a_pnl(client, store):
    row_id = store.add_log_row(race_date="2026-11-02", system="Apex Anchor", selection="Y",
                               venue=None, event_time=None, market=None, price_x100=None,
                               stake_pence=None, stake_pct=3, reasoning=None)
    client.post(f"/admin/log/{row_id}/settle", data={"result": "lost", "position": "5th"}, auth=AUTH)
    assert store.get_log_row(row_id)["result"] == "pending"
    client.post(f"/admin/log/{row_id}/settle",
                data={"result": "lost", "position": "5th", "pnl": "-20"}, auth=AUTH)
    assert store.get_log_row(row_id)["pnl_pence"] == -2000


def test_admin_requires_auth(client):
    assert client.get("/admin").status_code == 401
    assert client.get("/admin", auth=AUTH).status_code == 200


def test_weekly_email_shows_losers_and_total(store):
    today = date.today()
    for name, result, pnl in (("Winner", "won", 1140), ("Loser", "lost", -2000)):
        row_id = store.add_log_row(race_date=(today - timedelta(days=1)).isoformat(),
                                   system="Apex Anchor", selection=name, venue="Goodwood",
                                   event_time="15:15", market="Place", price_x100=160,
                                   stake_pence=2000, stake_pct=3, reasoning=None)
        store.settle_log_row(row_id, result=result, position="2nd" if pnl > 0 else "5th",
                             pnl_pence=pnl)
    body, n = emails.weekly_log_body(store, today)
    assert n == 2 and "Loser" in body and "−£20.00" in body and "Week total: −£8.60" in body


def test_members_page_shows_official_log_in_pounds(repo, mrepo, store):
    from betbot.members.auth import SESSION_COOKIE
    from betbot.members.portal import build_portal_router
    app = FastAPI()
    app.include_router(build_portal_router(repo, mrepo, NullNotifier()))
    client = TestClient(app)
    store.set_setting("billing_portal_url", "https://billing.stripe.com/p/login/test")
    member_id = mrepo.create_member("pro@x.com", tier="pro", billing_period="monthly")
    client.cookies.set(SESSION_COOKIE, mrepo.create_session(member_id))
    page = client.get("/members").text
    assert "−£122.35" in page and "€" not in page          # official log, pounds
    assert "Manage billing" in page and "Ask the Analyst" in page
    assert "CONSUMED" not in page                            # no bot internals


def test_paddock_import_skips_existing_and_junk(client, mrepo, outbox):
    mrepo.join_paddock("old@x.com")
    r = client.post("/admin/paddock/import", auth=AUTH, follow_redirects=False,
                    data={"emails_text": "old@x.com, New@X.com\nnot-an-email\nthird@x.com",
                          "send_welcome": "on"})
    assert "Imported%202%20new%20of%203" in r.headers["location"]
    assert {e["to"] for e in outbox} == {"new@x.com", "third@x.com"}
