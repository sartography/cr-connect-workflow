# This is the basic logging file, but with some additional details like SMTP Configuration
# which we will want to use on the production servers, which will fire off emails to administrators
# in the event of a failure.
logging_config = {
  'version': 1,
  "loggers": {
    "console": {
      "level": "DEBUG",
      "propagate": False,
      "handlers": [
        "console"
      ]
    },
    "file": {
      "level": "DEBUG",
      "propagate": False,
      "handlers": [
        "file"
      ]
    }
  },
  "formatters": {
    "simple": {
      "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    }
  },
  "root": {
    "level": "DEBUG",
    "handlers": [
      "console",
      "file",
      "email"
    ]
  },
  "handlers": {
    "console": {
      "formatter": "simple",
      "class": "logging.StreamHandler",
      "stream": "ext://sys.stdout",
      "level": "DEBUG"
    },
    "file": {
      "level": "DEBUG",
      "formatter": "simple",
      "class": "logging.FileHandler",
      "filename": "star_drive.log"
    },
    "email": {
      "level": "ERROR",
      "formatter": "simple",
      "class": "logging.handlers.SMTPHandler",
      "credentials": ("<<USERNAME>>","<<PASSWORD>>"),
      "mailhost": ["smtp.mailtrap.io", 2525],
      "fromaddr": "alerts@star.virginia.edu",
      "toaddrs": ["admin@star.virginia.edu"],
      "subject": "Autism DRIVE FAILURE",
    }
  }
}

