import logging

from .service import Service


class Logging(Service):
    def get_logger(self) -> logging.Logger:
        return logging.getLogger()
