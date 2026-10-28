"""Outbound email: magic links and the Apex lifecycle emails.

SMTP when configured (SiteGround's hello@apexcode.uk in production). Until SMTP
is set up, sign-in links are relayed to the admin's Telegram so they can be
forwarded manually — nothing silently vanishes. Marketing emails are never
relayed: without SMTP they simply aren't sent.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from betbot.config import secrets

log = logging.getLogger(__name__)

FOOTER = ("\n\n—\nThe Apex Code · apexcode.uk · 18+ only\n"
          "Betting involves risk. Never bet money you can't afford to lose.\n"
          "Free, confidential support: BeGambleAware.org · National Gambling Helpline 0808 8020 133")


def smtp_configured() -> bool:
    s = secrets()
    return bool(s.smtp_host and s.smtp_from)


def send_email(to: str, subject: str, body: str, *, unsubscribe_url: str | None = None) -> bool:
    """Send one plain-text email. Returns False (and logs) on any failure."""
    s = secrets()
    if not smtp_configured():
        log.warning("SMTP not configured — email to %s not sent (%s)", to, subject)
        return False
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = s.smtp_from
    msg["To"] = to
    msg["Reply-To"] = s.smtp_from
    text = body + FOOTER
    if unsubscribe_url:
        msg["List-Unsubscribe"] = f"<{unsubscribe_url}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
        text += f"\nUnsubscribe from these emails: {unsubscribe_url}"
    msg.set_content(text)
    port = s.smtp_port or 587
    try:
        # Port 465 is implicit SSL; anything else is plain SMTP upgraded via STARTTLS.
        if port == 465:
            smtp_ctx = smtplib.SMTP_SSL(s.smtp_host, port, timeout=20)
        else:
            smtp_ctx = smtplib.SMTP(s.smtp_host, port, timeout=20)
        with smtp_ctx as smtp:
            if port != 465:
                smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password or "")
            smtp.send_message(msg)
        return True
    except (smtplib.SMTPException, OSError):
        log.exception("SMTP send failed for %s", to)
        return False


async def send_magic_link(email: str, link: str, notifier=None) -> bool:
    body = ("Here's your one-time sign-in link (valid 30 minutes):\n\n"
            f"{link}\n\n"
            "If you didn't request this, ignore this email.")
    if send_email(email, "Your Apex Code sign-in link", body):
        return True
    log.warning("SMTP not configured/failed — relaying magic link for %s to admin", email)
    if notifier is not None:
        await notifier.send(f"🔑 Sign-in link requested by {email} (email didn't send — forward it "
                            f"to them manually):\n{link}")
        return True
    return False
