"""
marketplace/views_errors.py

Handlers de erro, registrados em contratempo/urls.py:
    handler403 = "marketplace.views_errors.acesso_negado"
    handler404 = "marketplace.views_errors.pagina_nao_encontrada"
    handler500 = "marketplace.views_errors.erro_servidor"

IMPORTANTE: para o Django usar estes handlers (em vez da página feia
padrão), o projeto precisa estar com DEBUG = False no settings.py.
Com DEBUG = True (ambiente de desenvolvimento), o Django sempre
mostra a página de depuração técnica, ignorando os handlers e os
templates — isso é comportamento normal do Django, não bug.
"""

from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponseServerError


def acesso_negado(request, exception=None):
    return render(request, "403.html", status=403)


def pagina_nao_encontrada(request, exception):
    return render(request, "404.html", status=404)


def erro_servidor(request):
    # O 500 não passa por context processors (o banco pode estar fora
    # do ar), por isso o template é autossuficiente.
    return HttpResponseServerError(get_template("500.html").render())
