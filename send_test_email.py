"""Тест надсилання листа через Resend API.

Перевіряє інтеграцію з Resend окремо від Django. Запуск з кореня проєкту:

    .venv\\Scripts\\python.exe send_test_email.py your-email@gmail.com

Без аргументів лист піде на адресу-заглушку з прикладу.
"""

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from config.email_service import is_configured, send_email

if __name__ == "__main__":
    to_email = sys.argv[1] if len(sys.argv) > 1 else "your-email@gmail.com"

    if not is_configured():
        sys.exit(
            "RESEND_API_KEY не задано.\n"
            "Додай його у файл .env (RESEND_API_KEY=re_...) або в Render ->\n"
            "Environment, потім повтори запуск."
        )

    try:
        message_id = send_email(
            to_email,
            "Тест GrandStay",
            "<h1>Ласкаво просимо до GrandStay!</h1>",
        )
    except Exception as exc:
        sys.exit(f"Помилка надсилання: {exc}")

    print(f"Лист надіслано на {to_email}, Resend id: {message_id}")
