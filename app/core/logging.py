from logging.config import dictConfig


def configure_logging(level: str) -> None:
    normalized = level.upper()
    dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {"format": "%(asctime)s %(levelname)-8s %(name)s %(message)s"},
            },
            "handlers": {
                "console": {"class": "logging.StreamHandler", "formatter": "default"},
            },
            "root": {"handlers": ["console"], "level": normalized},
            "loggers": {
                "uvicorn": {"handlers": ["console"], "level": normalized, "propagate": False},
                "uvicorn.access": {
                    "handlers": ["console"],
                    "level": normalized,
                    "propagate": False,
                },
            },
        }
    )
