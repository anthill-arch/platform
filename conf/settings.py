import os

NETWORKS = ['internal', 'external']

BROKER = 'amqp://guest:guest@localhost:5672'

EMAIL_SUBJECT_PREFIX = '[Anthill] '

USE_I18N = True
LOCALE = 'en'

FILE_UPLOAD_PERMISSIONS = 0o644
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o755

DEFAULT_HANDLER_CLASS = None

CACHES = {
    "default": {
        "BACKEND": "anthill.framework.core.cache.backends.redis.cache.RedisCache",
        "LOCATION": "redis://localhost:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "anthill.framework.core.cache.backends.redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 500,
                "retry_on_timeout": True
            }
        }
    }
}
REDIS_IGNORE_EXCEPTIONS = False
REDIS_LOG_IGNORED_EXCEPTIONS = False
REDIS_LOGGER = False
REDIS_SCAN_ITERSIZE = 10

# HTTPS = {
#     'key_file': 'key_file_path',
#     'crt_file': 'crt_file_path',
# }
HTTPS = None

##########
# CELERY #
##########

# All celery configuration options:
# http://docs.celeryproject.org/en/latest/userguide/configuration.html#configuration
CELERY_SETTINGS = {
    'broker_url': BROKER,
    'broker_transport_options': {},
    'broker_connection_timeout': 4,

    'result_backend': 'redis://',
    'result_serializer': 'json',
    'result_compression': None,
    'redis_max_connections': 150,

    'worker_concurrency': None,
    'worker_pool': 'solo',

    'task_serializer': 'json',
    'task_compression': None,

    'worker_log_format': '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d] %(message)s',
    'worker_task_log_format':
        '[%(levelname)1.1s %(asctime)s %(module)s:%(lineno)d][%(task_name)s(%(task_id)s)] %(message)s'
}

CELERY_ENABLE = False

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'anthill.framework.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'anthill.framework.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'anthill.framework.auth.password_validation.NumericPasswordValidator',
    },
]

CSRF_COOKIES = True

LOG_STREAMING = {
    'handler': {
        'class': 'anthill.framework.handlers.WatchLogFileHandler',
        'kwargs': {'handler_name': 'anthill.server'}
    },
    'path': '/log/',
}

##############
# RATE LIMIT #
##############

CACHES['rate_limit'] = {
    "BACKEND": "anthill.framework.core.cache.backends.redis.cache.RedisCache",
    "LOCATION": "redis://localhost:6379/1",
    "OPTIONS": {
        "CLIENT_CLASS": "anthill.framework.core.cache.backends.redis.client.DefaultClient",
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 500,
            "retry_on_timeout": True
        }
    },
    "KEY_PREFIX": "rate_limit"
}

RATE_LIMIT_ENABLE = False

# Maps resource names and its rate limit parameters.
# Rate limit has blocking and non-blocking mode.
# In blocking mode (default) rate limit prevents function execution
# either by raising RateLimitException error or executing exceeded_callback.
# In non-blocking mode rate limit do not stops function executing.
# Also we can set additional `callback` parameter, that
# runs when exceeded in non-blocking and ignored in blocking mode.
#
# Example:
#
# RATE_LIMIT_CONFIG = {
#     'user': {
#         'rate': '15/s', 'block': True, 'callback': None
#     },
#     'ip': {
#         'rate': '8/3m', 'block': True, 'callback': None
#     },
#     'create_room': {
#         'rate': '152/24h', 'block': False, 'callback': 'game.security.rate_limit.cr'
#     },
#     'send_message': {
#         'rate': '512/d', 'block': True, 'callback': None
#     }
# }
RATE_LIMIT_CONFIG = {}

##############
# WEBSOCKETS #
##############

WEBSOCKET_PING_INTERVAL = 10
WEBSOCKET_PING_TIMEOUT = 30
WEBSOCKET_MAX_MESSAGE_SIZE = 10 * 1024 * 1024  # 10MiB
WEBSOCKET_COMPRESSION_LEVEL = -1
WEBSOCKET_MEM_LEVEL = 6

#############################
# WEBSOCKET CLIENTS WATCHER #
#############################

CACHES['websocket_clients_watcher'] = {
    "BACKEND": "anthill.framework.core.cache.backends.redis.cache.RedisCache",
    "LOCATION": "redis://localhost:6379/1",
    "OPTIONS": {
        "CLIENT_CLASS": "anthill.framework.core.cache.backends.redis.client.DefaultClient",
        "CONNECTION_POOL_KWARGS": {
            "max_connections": 500,
            "retry_on_timeout": True
        }
    },
    "KEY_PREFIX": "websocket_clients_watcher"
}

############
# CHANNELS #
############

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "anthill.platform.core.messenger.channels.layers.backends.redis.ChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
    "internal": {
        "BACKEND": "anthill.platform.core.messenger.channels.layers.backends.redis.ChannelLayer",
        "CONFIG": {
            "hosts": [("localhost", 6379)],
        },
    },
}

#############
# MESSENGER #
#############

MESSENGER = {
    'PERSONAL_GROUP_PREFIX': '__user',  # Must starts with `__` for security reason
    'PERSONAL_GROUP_FUNCTION': 'anthill.platform.core.messenger.client.backends.base.create_personal_group',
    'MODERATORS': []
}

#######
# API #
#######

INTERNAL_API_CONF = 'api.v1.internal'
INTERNAL_REQUEST_CACHING = True
INTERNAL_API_METHOD_CACHING = False
INTERNAL_DEFAULT_CACHE_TIMEOUT = 300  # 5min
PUBLIC_API_URL = None

#########
# GEOIP #
#########

GEOIP_PATH = None
GEOIP_CITY = 'GeoLite2-City.mmdb'
GEOIP_COUNTRY = 'GeoLite2-Country.mmdb'

COMPRESS_RESPONSE = True

# LOGGING_ROOT_DIR = '/var/log/anthill'
LOGGING_ROOT_DIR = '../'
USER_LOGGING_ROOT_DIR = os.path.join(LOGGING_ROOT_DIR, 'users')


UPDATES = {
    'MANAGER': 'anthill.platform.services.update.backends.git.GitUpdateManager',
}
