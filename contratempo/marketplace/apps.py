from django.apps import AppConfig


class MarketplaceConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'marketplace'

    def ready(self):
        from django.db.backends.signals import connection_created

        from .busca import registrar_funcao_sqlite

        connection_created.connect(registrar_funcao_sqlite, dispatch_uid="marketplace_sem_acento")
