import os

import resend
from resend.exceptions import ResendError

DEFAULT_FROM_EMAIL = "noreply@grandstay.top"


def is_configured():

    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def send_email(to, subject, html, text=None):

    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")
    resend.api_key = api_key

    payload = {
        "from": os.environ.get("DEFAULT_FROM_EMAIL", DEFAULT_FROM_EMAIL),
        "to": [to] if isinstance(to, str) else list(to),
        "subject": subject,
        "html": html,
    }
    if text:
        payload["text"] = text

    response = resend.Emails.send(payload)
    return getattr(response, "id", None)


def send_email_safe(to, subject, html, text=None):

    if not is_configured():
        return None
    try:
        return send_email(to, subject, html, text)
    except ResendError:
        return None
    except (OSError, RuntimeError):
        return None


__all__ = ["send_email", "send_email_safe", "is_configured", "ResendError"]
