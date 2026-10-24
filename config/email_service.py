"""Надсилання листів через Resend (HTTPS API).

Render Free блокує вихідні SMTP-з'єднання на портах 25, 465 і 587, тому
виробничі листи (наприклад, код підтвердження реєстрації) надсилаються не
через SMTP, а через HTTPS API Resend (порт 443).

Для роботи потрібні змінні середовища:
- RESEND_API_KEY — API-ключ Resend;
- RESEND_VERIFICATION_TEMPLATE_ID — ID опублікованого HTML-шаблону листа
  підтвердження (за потреби; без нього лист формується inline-HTML).

Адреса-відправник береться з DEFAULT_FROM_EMAIL і має належати
підтвердженому в Resend домену.
"""

import logging
import os

import resend
from resend.exceptions import ResendError

logger = logging.getLogger(__name__)

DEFAULT_FROM_EMAIL = "noreply@grandstay.top"


def is_configured():
    """Повертає True, якщо Resend API-ключ заданий у середовищі."""
    return bool(os.environ.get("RESEND_API_KEY", "").strip())


def verification_template_id():
    """Повертає ID опублікованого шаблону Resend або порожній рядок."""
    return os.environ.get("RESEND_VERIFICATION_TEMPLATE_ID", "").strip()


def send_email(to, subject, html, text=None):
    """Надсилає HTML-лист через Resend і повертає його ідентифікатор.

    Повертає рядок з id листа у Resend. Ключ читається з середовища при
    кожному виклику, щоб зміна змінної під час роботи процесу враховувалась.
    """
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


def send_template_email(to, subject, variables):
    """Надсилає лист через опублікований шаблон Resend.

    Шаблон задається змінною середовища RESEND_VERIFICATION_TEMPLATE_ID
    (id не хардкодиться у коді). У шаблон передаються динамічні змінні,
    наприклад {"USERNAME": "ivan", "CODE": "A1B2C3"}.

    Формат payload відповідає Resend Emails API / resend SDK (>=2.40):
    поле "template" має вигляд {"id": ..., "variables": {...}}.

    ВАЖЛИВО: Resend API повертає 422 validation_error
    "Cannot provide 'text' when using a template" (та сама заборона для
    "html"), тому в payload з "template" НЕ передаються ні "text", ні
    "html" — тіло листа бере на себе шаблон.

    Кидає RuntimeError, якщо RESEND_API_KEY або
    RESEND_VERIFICATION_TEMPLATE_ID відсутні.
    """
    api_key = os.environ.get("RESEND_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("RESEND_API_KEY is not set")
    template_id = verification_template_id()
    if not template_id:
        raise RuntimeError("RESEND_VERIFICATION_TEMPLATE_ID is not set")
    resend.api_key = api_key

    payload = {
        "from": os.environ.get("DEFAULT_FROM_EMAIL", DEFAULT_FROM_EMAIL),
        "to": [to] if isinstance(to, str) else list(to),
        "subject": subject,
        "template": {
            "id": template_id,
            "variables": dict(variables),
        },
    }

    response = resend.Emails.send(payload)
    return getattr(response, "id", None)


def send_email_safe(to, subject, html, text=None):
    """Надсилає лист, але не кидає винятків.

    Повертає id листа або None, якщо Resend не налаштовано чи виникла
    помилка API. Використовується в бізнес-логіці, де збій пошти не має
    валити запит. У лог пишуться лише діагностика без секретів.
    """
    if not is_configured():
        logger.warning(
            "email_service: RESEND_API_KEY is not set; email to %s skipped",
            to,
        )
        return None
    try:
        return send_email(to, subject, html, text)
    except ResendError as exc:
        logger.error("email_service: Resend API error while sending email: %s", exc)
        return None
    except (OSError, RuntimeError) as exc:
        logger.error("email_service: could not send email via Resend: %s", exc)
        return None


def send_template_email_safe(to, subject, variables):
    """Надсилає лист шаблоном Resend без винятків.

    Повертає id листа або None. У лог пишеться причина відмови
    (відсутність змінних середовища чи помилка API), але ні API-ключі,
    ні значення змінних шаблону (код підтвердження) не логуються.
    "text"/"html" не передаються — Resend повертає 422 при їх наявності
    разом із "template".
    """
    if not is_configured():
        logger.warning(
            "email_service: RESEND_API_KEY is not set; template email to %s skipped",
            to,
        )
        return None
    if not verification_template_id():
        logger.warning(
            "email_service: RESEND_VERIFICATION_TEMPLATE_ID is not set; "
            "template email to %s skipped",
            to,
        )
        return None
    try:
        return send_template_email(to, subject, variables)
    except ResendError as exc:
        logger.error(
            "email_service: Resend API error while sending template email: %s", exc
        )
        return None
    except (OSError, RuntimeError) as exc:
        logger.error(
            "email_service: could not send template email via Resend: %s", exc
        )
        return None


__all__ = [
    "send_email",
    "send_email_safe",
    "send_template_email",
    "send_template_email_safe",
    "is_configured",
    "verification_template_id",
    "ResendError",
]
