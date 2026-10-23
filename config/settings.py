"""
Django settings for config project.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / '.env')

SECRET_KEY = os.environ['SECRET_KEY']

# SECURITY WARNING: don't run with debug turned on in production!
# Локально за замовчуванням True; на Render задається DEBUG=False.
DEBUG = os.environ.get('DEBUG', 'True').strip().lower() in ('1', 'true', 'yes')


def _csv_env(name, default=''):
    """Список значень, розділених комою, зі змінної середовища."""
    return [v.strip() for v in os.environ.get(name, default).split(',') if v.strip()]


# '*' — щоб сайт відкривався з телефона по LAN-IP (http://<IP-ПК>:8000),
# інакше Django відповідає 400 Bad Request (DisallowedHost).
# На Render: задайте ALLOWED_HOSTS=ваш-домен.onrender.com. Якщо не задано —
# беремо системну змінну Render RENDER_EXTERNAL_HOSTNAME.
ALLOWED_HOSTS = _csv_env('ALLOWED_HOSTS')
if not ALLOWED_HOSTS:
    _host = os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip()
    ALLOWED_HOSTS = ([_host] if _host else ['*']) + ['localhost', '127.0.0.1', '[::1]']

# CSRF: на Render HTTPS-трафік іде через зовнішній проксі, тому Django може
# «бачити» http і відхиляти POST-форми (вхід, реєстрація, бронювання).
# 1) TRUST_X_FORWARDED_PROTO=true робить request.is_secure() = True за заголовком
#    X-Forwarded-Proto (Render його завжди передає);
# 2) Origin додається у довірені — другий захисний шар (авто для домену Render).
if os.environ.get('TRUST_X_FORWARDED_PROTO', '').strip().lower() in ('1', 'true', 'yes'):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

CSRF_TRUSTED_ORIGINS = _csv_env('CSRF_TRUSTED_ORIGINS')
if not CSRF_TRUSTED_ORIGINS and os.environ.get('RENDER_EXTERNAL_HOSTNAME', '').strip():
    CSRF_TRUSTED_ORIGINS = ['https://' + os.environ['RENDER_EXTERNAL_HOSTNAME'].strip()]


# Application definition

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
    # WhiteNoise віддає зібрану статику (collectstatic → STATIC_ROOT)
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


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
#
# Локально — SQLite (див. .env: DB_ENGINE=django.db.backends.sqlite3).
# На Render + TiDB Cloud: DB_ENGINE=django.db.backends.mysql, порт 4000,
# TLS (параметри DB_SSL_* нижче). Також підтримується PostgreSQL.

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
    # TiDB Cloud (і MySQL) приймає клієнтів через TLS.
    # TLS обов'язковий і перевіряє ланцюжок сертифіката системними CA.
    # Якщо TiDB надає окремий CA-файл, DB_SSL_CA дозволяє також перевіряти ім'я хоста.
    # DB_SSL_VERIFY=false вимикає перевірку сертифіката (не рекомендовано).
    _db_options = {'ssl_verify_cert': True}
    _ssl_ca = os.environ.get('DB_SSL_CA', '').strip()
    if _ssl_ca:
        _db_options['ssl_ca'] = _ssl_ca
        _db_options['ssl_verify_identity'] = True
    if os.environ.get('DB_SSL_VERIFY', 'true').strip().lower() in ('0', 'false', 'no'):
        _db_options = {'ssl_disabled': True}
    DATABASES['default']['OPTIONS'] = _db_options


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Europe/Kyiv'

USE_I18N = True

USE_TZ = True

LOGIN_URL = 'hotel:login'
LOGIN_REDIRECT_URL = 'hotel:dashboard'
LOGOUT_REDIRECT_URL = 'hotel:login'

# Cookies лише по HTTPS у проді; локально (DEBUG=True) — без змін.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
if not DEBUG:
    # HSTS: браузер примусово використовує HTTPS (на Render він завжди)
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
# Куди collectstatic складає файли для WhiteNoise (build.sh на Render)
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # Manifest додає хеш у назви файлів → довге кешування в браузері.
        # WHITENOISE_MANIFEST_STRICT=false: якщо якогось файлу не вистачить,
        # буде 404, а не 500 на всій сторінці.
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}
WHITENOISE_MANIFEST_STRICT = False

# Завантажені файли (фото номерів) — hotel/media/rooms/…
# У проді DEBUG=False, тому допоміжний static() у config/urls.py не працює —
# медіа віддає окремий маршрут (див. config/urls.py).
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
