import os

from django.apps import AppConfig


class RecoveryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'recovery'
    path = os.path.dirname(os.path.abspath(__file__))
    verbose_name = 'Forensic Recovery'
