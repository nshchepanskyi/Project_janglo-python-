#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt
python manage.py collectstatic --noinput
python manage.py migrate --noinput
python manage.py seed_if_empty
python manage.py bootstrap_admin
