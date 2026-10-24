"""
Django settings for config project.
"""

import os
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['SECRET_KEY']



DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in ('1', 'true', 'yes')


def _csv_env(name, default=''):
    """Список значень, розділених комою, зі змінної середовища."""
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]






ALLOWED_HOSTS = _csv_env('ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    _host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
    ALLOWED_HOSTS = ([_host] if _host else ['*']) + ['localhost', '127.0.0.1', '[::1]']






if os.environ.get('TRUST_X_FORWARDED_PROTO', '').strip().lower() in ('1', 'true', 'yes'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


CSRF_TRUSTED_ORIGINS = _csv_env('CSRF_TRUSTED_ORIGINS')

_render_host = os.environ.get(
    'RENDER_EXTERNAL_HOSTNAME', ''
).strip()

if _render_host:
    _render_origin = f'https://{_render_host}'
    if _render_origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_render_origin)

CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = False





INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'hotel',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',

    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'hotel.context_processors.ui_prefs',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'









_database_url = os.environ.get('DATABASE_URL', '').strip()
if _database_url:
    _parsed_database_url = urlparse(_database_url)
    if _parsed_database_url.scheme not in ('postgres', 'postgresql'):
        raise ValueError('DATABASE_URL must use the postgres:// or postgresql:// scheme')

    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': unquote(_parsed_database_url.path.lstrip('/')),
            'USER': unquote(_parsed_database_url.username or ''),
            'PASSWORD': unquote(_parsed_database_url.password or ''),
            'HOST': _parsed_database_url.hostname or '',
            'PORT': str(_parsed_database_url.port or 5432),
        }
    }
    _database_query = parse_qs(_parsed_database_url.query)
    if _database_query:
        DATABASES['default']['OPTIONS'] = {
            key: values[-1] for key, values in _database_query.items()
        }
else:
    DATABASES = {
        'default': {
            'ENGINE': os.environ.get('DB_ENGINE', 'django.db.backends.postgresql'),
            'NAME': os.environ.get('DB_NAME', 'janglo_hotel'),
            'USER': os.environ.get('DB_USER', 'janglo'),
            'PASSWORD': os.environ.get('DB_PASSWORD', ''),
            'HOST': os.environ.get('DB_HOST', 'localhost'),
            'PORT': os.environ.get('DB_PORT', '5432'),
        }
    }

if DATABASES['default']['ENGINE'].endswith('.mysql'):




    _db_options = {'ssl_verify_cert': True}
    _ssl_ca = os.environ.get('DB_SSL_CA', '').strip()
    if _ssl_ca:
        _db_options['ssl_ca'] = _ssl_ca
        _db_options['ssl_verify_identity'] = True
    if os.environ.get('DB_SSL_VERIFY', 'true').strip().lower() in ('0', 'false', 'no'):
        _db_options = {'ssl_disabled': True}
    DATABASES['default']['OPTIONS'] = _db_options





AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]





LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Kyiv'

USE_I18N = True

USE_TZ = True

LOGIN_URL = 'hotel:login'
LOGIN_REDIRECT_URL = 'hotel:dashboard'
LOGOUT_REDIRECT_URL = 'hotel:login'


SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
if not DEBUG:

    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True





STATIC_URL = 'static/'

STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {



        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
WHITENOISE_MANIFEST_STRICT = False




MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EMAIL_BACKEND = os.environ.get(
    'EMAIL_BACKEND', 'django.core.mail.backends.console.EmailBackend'
)
EMAIL_HOST = os.environ.get('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', '587'))
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'true').lower() in ('1', 'true', 'yes')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@grandstay.example')
