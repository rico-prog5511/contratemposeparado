"""Ponto de entrada ASGI (alternativa ao WSGI; não usado no PythonAnywhere)."""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratempo.settings')

application = get_asgi_application()
