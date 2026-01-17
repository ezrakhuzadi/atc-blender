# my_app/apps.py

from django.apps import AppConfig
from loguru import logger


class MyAppConfig(AppConfig):
    name = "flight_feed_operations"

    def ready(self):
        logger.info("flight_feed_operations app ready")
