from django.apps import AppConfig


class ShareshelfAppConfig(AppConfig):
    name = 'shareshelf_app'

    def ready(self):
        from . import checks  # noqa: F401  registers the SWI-Prolog check
