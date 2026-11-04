"""Email delivery via Resend HTTP API.

If RESEND_API_KEY is not configured, emails are logged and skipped so
auth flows keep working in development.
"""

import logging
from typing import Optional

import httpx

from app.core.config import settings

log = logging.getLogger(__name__)

RESEND_ENDPOINT = "https://api.resend.com/emails"


async def send_via_resend(
    to: str,
    subject: str,
    html: str,
    text: Optional[str] = None,
) -> bool:
    """Send a single email through Resend. Returns True on success."""
    if not settings.RESEND_API_KEY:
        log.warning("RESEND_API_KEY not set; skipping email to %s (%s)", to, subject)
        return False

    payload = {
        "from": settings.EMAIL_FROM,
        "to": [to],
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                RESEND_ENDPOINT,
                headers={"Authorization": f"Bearer {settings.RESEND_API_KEY}"},
                json=payload,
            )
        if resp.status_code in (200, 201, 202):
            log.info("Resend accepted email for %s", to)
            return True
        log.error("Resend error %s: %s", resp.status_code, resp.text)
        return False
    except Exception as exc:  # never break the auth flow on email failure
        log.error("Resend send failed: %s", exc)
        return False
