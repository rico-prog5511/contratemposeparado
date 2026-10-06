"""Ponto de entrada WSGI (usado pelo servidor web em produção)."""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'contratempo.settings')

application = get_wsgi_application()
