#!/usr/bin/env bash
set -euo pipefail

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate

if [[ -n "${DJANGO_SUPERUSER_USERNAME:-}" && -n "${DJANGO_SUPERUSER_PASSWORD:-}" ]]; then
    export DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-}"
    if python manage.py shell -c 'import os, sys; from django.contrib.auth import get_user_model; sys.exit(0 if get_user_model().objects.filter(username=os.environ["DJANGO_SUPERUSER_USERNAME"]).exists() else 1)' >/dev/null 2>&1; then
        echo "Superuser already exists; skipping creation."
    else
        python manage.py createsuperuser --noinput
    fi
else
    echo "Superuser creation skipped; set DJANGO_SUPERUSER_USERNAME and DJANGO_SUPERUSER_PASSWORD to enable it."
fi
