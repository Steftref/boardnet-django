# Copy this file to local_settings.py and fill in your own values.

# Generate a key with:
#   python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
# It also encrypts the card numbers, so do not change it later.
SECRET_KEY = 'change-me'

DEBUG = True
ALLOWED_HOSTS = []

DATABASE_USER = 'root'
DATABASE_PASSWORD = 'change-me'
