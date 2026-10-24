"""Тест надсилання листа через Resend API.

Перевіряє інтеграцію з Resend окремо від Django. Запуск з кореня проєкту:

    .venv\\Scripts\\python.exe send_test_email.py your-email@gmail.com
    .venv\\Scripts\\python.exe send_test_email.py your-email@gmail.com --template

Перший варіант надсилає простий inline-HTML лист.
Другий (--template) надсилає лист через опублікований шаблон Resend
(RESEND_VERIFICATION_TEMPLATE_ID) зі змінними USERNAME і CODE.
"""

import sys

from dotenv import load_dotenv

load_dotenv()

from config.email_service import (
    is_configured,
    send_email,
    send_template_email,
    verification_template_id,
)

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--template"]
    use_template = "--template" in sys.argv[1:]
    to_email = args[0] if args else "your-email@gmail.com"

    if not is_configured():
        sys.exit(
            "RESEND_API_KEY не задано.\n"
            "Додай його у файл .env (RESEND_API_KEY=re_...) або в Render ->\n"
            "Environment, потім повтори запуск."
        )

    if use_template:
        template_id = verification_template_id()
        if not template_id:
            sys.exit(
                "RESEND_VERIFICATION_TEMPLATE_ID не задано.\n"
                "Додай ID опублікованого шаблону Resend у .env або в Render ->\n"
                "Environment, потім повтори запуск."
            )
        try:
            message_id = send_template_email(
                to_email,
                "Verify your email address — GrandStay",
                {"USERNAME": "TestUser", "CODE": "A1B2C3"},
            )
        except Exception as exc:
            sys.exit(f"Помилка надсилання: {exc}")
        print(
            f"Лист-шаблон (id шаблону: {template_id}) надіслано на {to_email}, "
            f"Resend id: {message_id}"
        )
    else:
        try:
            message_id = send_email(
                to_email,
                "Тест GrandStay",
                "<h1>Ласкаво просимо до GrandStay!</h1>",
            )
        except Exception as exc:
            sys.exit(f"Помилка надсилання: {exc}")
        print(f"Лист надіслано на {to_email}, Resend id: {message_id}")
