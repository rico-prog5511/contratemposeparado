from decimal import Decimal, InvalidOperation

from django import template

from ..imagens import url_miniatura

register = template.Library()


@register.filter
def miniatura(url):
    return url_miniatura(url)


@register.filter
def to_range(numero):
    try:
        return range(int(numero))
    except (TypeError, ValueError):
        return range(0)


@register.filter
def brl(valor):
    try:
        valor = Decimal(valor)
    except (TypeError, ValueError, InvalidOperation):
        return ""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@register.filter
def imagem_principal(produto):
    if produto is None:
        return ""
    imagens = list(produto.imagens.all())
    for imagem in imagens:
        if imagem.principal:
            return imagem.url_imagem
    return imagens[0].url_imagem if imagens else ""


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    request = context.get("request")
    query = request.GET.copy() if request else None
    if query is None:
        return ""
    for chave, valor in kwargs.items():
        if valor in (None, ""):
            query.pop(chave, None)
        else:
            query[chave] = valor
    return query.urlencode()
