import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'custom_app_formatter': {
            
            'format': '%(asctime)s - %(levelname)s - %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'custom_app_formatter',
        },
        'app_file': {
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': LOG_DIR / 'application.log',
            'maxBytes': 5 * 1024 * 1024,  
            'backupCount': 3,             
            'formatter': 'custom_app_formatter',
        },
    },
    'loggers': {
        'app_logger': {
            'handlers': ['console', 'app_file'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
