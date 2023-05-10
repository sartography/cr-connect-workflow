logging_config = {
  'version': 1,
  'disable_existing_loggers': False,
  "loggers": {
    '': {  # root logger
      'handlers': ['console'],
      'level': 'INFO',
      'propagate': True
    },
    'alembic.runtime.migration': {
      'handlers': ['console'],
      'level': 'ERROR',
      'propagate': False
    },
    'urllib3.connectionpool': {
      'handlers': ['console'],
      'level': 'ERROR',
      'propagate': False
    },
    'spiff': {
      'handlers': ['console'],
      'level': 'ERROR',
      'propagate': False
    },
    'werkzeug': {
      'handlers': ['console'],
      'level': 'ERROR',
      'propagate': False
    },
  },
  "formatters": {
    "simple": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "root": {
    "level": "INFO",
    "handlers": [
      "console",
    ]
  },
  "handlers": {
    "console": {
      "formatter": "simple",
      "class": "logging.StreamHandler",
      "stream": "ext://sys.stdout",
      "level": "INFO"
    }
  }
}
