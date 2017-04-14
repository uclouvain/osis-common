from django.apps import AppConfig


class OsisCommonConfig(AppConfig):
    name = 'osis_common'

    def ready(self):
        import osis_common.signals