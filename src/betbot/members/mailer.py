"""Outbound email for magic links.

SMTP when configured (works with MailerLite SMTP, Mailgun, Gmail app passwords,
anything). Until SMTP is set up, the sign-in link is relayed to the admin's
Telegram so it can be forwarded manually — nothing silently vanishes.
"""
from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from betbot.config import secrets

log = logging.getLogger(__name__)


async def send_magic_link(email: str, link: str, notifier=None) -> bool:
    s = secrets()
    if s.smtp_host and s.smtp_from:
        msg = EmailMessage()
        msg["Subject"] = "Your Apex Code sign-in link"
        msg["From"] = s.smtp_from
        msg["To"] = email
        msg.set_content(
            "Here's your one-time sign-in link (valid 30 minutes):\n\n"
            f"{link}\n\n"
            "If you didn't request this, ignore this email.\n\n"
            "The Apex Code · 18+ · BeGambleAware.org"
        )
        try:
            with smtplib.SMTP(s.smtp_host, s.smtp_port or 587, timeout=20) as smtp:
                smtp.starttls()
                if s.smtp_user:
                    smtp.login(s.smtp_user, s.smtp_password or "")
                smtp.send_message(msg)
            return True
        except (smtplib.SMTPException, OSError):
            log.exception("SMTP send failed for %s", email)

    log.warning("SMTP not configured/failed — relaying magic link for %s to admin", email)
    if notifier is not None:
        await notifier.send(f"🔑 Sign-in link requested by {email} (SMTP not set up — forward it "
                            f"to them manually):\n{link}")
        return True
    return False
