#!/usr/bin/env bash
# Render build command. Exit on the first failure so a bad deploy is obvious.
set -o errexit

pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
python manage.py seed_notifications
