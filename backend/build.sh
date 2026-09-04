#!/usr/bin/env bash
# Render build command. Exit on the first failure so a bad deploy is obvious.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_notifications

# The free plan has no shell, so the admin account is created here instead.
# Django reads the password from DJANGO_SUPERUSER_PASSWORD; a second run fails
# harmlessly because the username already exists.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --no-input || echo "superuser already exists, skipping"
fi
