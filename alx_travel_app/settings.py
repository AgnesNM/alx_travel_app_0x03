import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key-here-change-in-production'

DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'drf_yasg',
    'corsheaders',
    'django_filters',
    
    # Local apps
    'listings',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'alx_travel_app_0x03.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'alx_travel_app_0x03.wsgi.application'

# Custom User Model
AUTH_USER_MODEL = 'listings.User'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
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

# REST Framework Configuration
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ],
}

# Swagger Configuration
SWAGGER_SETTINGS = {
    'SECURITY_DEFINITIONS': {
        'Token': {
            'type': 'apiKey',
            'name': 'Authorization',
            'in': 'header'
        }
    },
    'USE_SESSION_AUTH': False,
    'JSON_EDITOR': True,
    'SUPPORTED_SUBMIT_METHODS': [
        'get', 'post', 'put', 'delete', 'patch'
    ],
}

# CORS Configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
]

CORS_ALLOW_CREDENTIALS = True

# Internationalization
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# Static files
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Email Configuration
# Development: Use console backend to see emails in terminal
# Production: Configure SMTP settings below
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# SMTP Configuration (uncomment and configure for production)
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', 'your-email@gmail.com')
# EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', 'your-app-password')

# Default from email
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'ALX Travel App <noreply@alxtravelapp.com>')

# Support email for customer service
SUPPORT_EMAIL = os.environ.get('SUPPORT_EMAIL', 'support@alxtravelapp.com')

# Website URL for email links
WEBSITE_URL = os.environ.get('WEBSITE_URL', 'http://localhost:8000')

# =============================================================================
# CELERY CONFIGURATION
# =============================================================================

# Celery Broker Configuration
CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'amqp://guest:guest@localhost:5672//')

# Result backend configuration
CELERY_RESULT_BACKEND = 'rpc://'

# Celery message serialization settings
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

# Celery timezone configuration
CELERY_TIMEZONE = TIME_ZONE

# Task routing configuration
CELERY_TASK_ROUTES = {
    'listings.tasks.send_booking_confirmation_email': {'queue': 'emails'},
    'listings.tasks.send_booking_reminder_email': {'queue': 'emails'},
    'listings.tasks.send_booking_cancellation_email': {'queue': 'emails'},
    'listings.tasks.send_bulk_promotional_emails': {'queue': 'bulk_emails'},
    'listings.tasks.test_email_configuration': {'queue': 'test_emails'},
}

# Task execution settings
CELERY_TASK_RETRY_DELAY = 60        # Retry after 60 seconds
CELERY_TASK_MAX_RETRIES = 3         # Maximum 3 retries
CELERY_TASK_SOFT_TIME_LIMIT = 300   # 5 minutes soft limit
CELERY_TASK_TIME_LIMIT = 600        # 10 minutes hard limit

# Task result settings
CELERY_RESULT_EXPIRES = 3600        # Results expire after 1 hour

# Worker settings
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000
CELERY_WORKER_DISABLE_RATE_LIMITS = False

# Celery Beat settings for periodic tasks
CELERY_BEAT_SCHEDULE = {
    # Example: Health check every 30 minutes
    'health-check': {
        'task': 'alx_travel_app_0x03.celery.health_check',
        'schedule': 30.0 * 60,  # 30 minutes
        'options': {'queue': 'periodic_tasks'}
    },
    # Example: Cleanup old task results daily at 2 AM
    'cleanup-old-results': {
        'task': 'listings.tasks.cleanup_old_task_results',
        'schedule': 24.0 * 60 * 60,  # 24 hours
        'options': {'queue': 'maintenance_tasks'}
    },
}

# Additional settings for production
if not DEBUG:
    # Enable task events for monitoring
    CELERY_WORKER_SEND_TASK_EVENTS = True
    CELERY_TASK_SEND_SENT_EVENT = True
    CELERY_SEND_EVENTS = True
    CELERY_SEND_TASK_SENT_EVENT = True
    
    # Enable result extended for better monitoring
    CELERY_RESULT_EXTENDED = True
    
    # Configure task compression
    CELERY_TASK_COMPRESSION = 'gzip'
    CELERY_RESULT_COMPRESSION = 'gzip'

# Queue configuration for different task types
CELERY_TASK_CREATE_MISSING_QUEUES = True
CELERY_TASK_DEFAULT_QUEUE = 'default'
CELERY_TASK_DEFAULT_EXCHANGE = 'default'
CELERY_TASK_DEFAULT_EXCHANGE_TYPE = 'direct'
CELERY_TASK_DEFAULT_ROUTING_KEY = 'default'

# =============================================================================
# END CELERY CONFIGURATION
# =============================================================================

# Logging Configuration
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
        'celery': {
            'format': '[{asctime}] {levelname} [{name}] {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'app.log',
            'formatter': 'verbose',
        },
        'celery_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'celery.log',
            'formatter': 'celery',
        },
        'email_file': {
            'class': 'logging.FileHandler',
            'filename': BASE_DIR / 'logs' / 'email_tasks.log',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'listings': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'listings.tasks': {
            'handlers': ['console', 'email_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.task': {
            'handlers': ['console', 'celery_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.core.mail': {
            'handlers': ['console', 'email_file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Create logs directory if it doesn't exist
import os
os.makedirs(BASE_DIR / 'logs', exist_ok=True)

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
