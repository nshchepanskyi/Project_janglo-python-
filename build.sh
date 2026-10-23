#!/usr/bin/env bash
# Build script для Render: збірка + підготовка бази перед стартом gunicorn.
set -euo pipefail

pip install -r requirements.txt

# Збирає статику у STATIC_ROOT (Whitenoise віддає її в проді)
python manage.py collectstatic --noinput

# Міграції у TiDB Cloud (зовнішня база доступна вже на етапі збірки)
python manage.py migrate --noinput

# Демонстраційний каталог номерів і послуг — лише якщо база порожня
python manage.py seed_if_empty

# Одноразово створює адміністратора, якщо задані DJANGO_SUPERUSER_* env vars.
python manage.py bootstrap_admin
