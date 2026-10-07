from django.shortcuts import render
from django.template.loader import get_template
from django.http import HttpResponseServerError


def acesso_negado(request, exception=None):
    return render(request, "403.html", status=403)


def pagina_nao_encontrada(request, exception):
    return render(request, "404.html", status=404)


def erro_servidor(request):
    return HttpResponseServerError(get_template("500.html").render())
