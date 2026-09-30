"""
marketplace/templatetags/marketplace_extras.py

Uso no template: {% load marketplace_extras %}
    {% for _ in nota|to_range %}★{% endfor %}
    {{ produto.preco|brl }}                 -> R$ 1.234,56
    {{ produto|imagem_principal }}           -> URL da imagem principal (ou "")
    <a href="?{% url_replace page=2 %}">     -> mantém os outros filtros da URL
"""

from decimal import Decimal, InvalidOperation

from django import template

register = template.Library()


@register.filter
def to_range(numero):
    """Transforma um inteiro N em range(N), para usar em {% for %}."""
    try:
        return range(int(numero))
    except (TypeError, ValueError):
        return range(0)


@register.filter
def brl(valor):
    """Formata um número como moeda brasileira: R$ 1.234,56."""
    try:
        valor = Decimal(valor)
    except (TypeError, ValueError, InvalidOperation):
        return ""
    texto = f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {texto}"


@register.filter
def imagem_principal(produto):
    """
    URL da imagem marcada como principal (ou da primeira, pela ordem de
    exibição). Itera sobre produto.imagens.all() para aproveitar o
    prefetch_related("imagens") feito nas views, sem consultas extras.
    """
    if produto is None:
        return ""
    imagens = list(produto.imagens.all())
    for imagem in imagens:
        if imagem.principal:
            return imagem.url_imagem
    return imagens[0].url_imagem if imagens else ""


@register.simple_tag(takes_context=True)
def url_replace(context, **kwargs):
    """
    Devolve a querystring atual com os parâmetros informados trocados.
    Parâmetros com valor None/"" são removidos. Usado na paginação e na
    ordenação do catálogo para não perder os filtros aplicados.
    """
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
