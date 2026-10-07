from datetime import timedelta

from django import template
from django.db.models import Sum
from django.urls import reverse
from django.utils import timezone

from ..models import Contato, Denuncia, Pedido, PerguntaProduto, Produto, Usuario
from ..relatorios import resumo_do_ano
from .marketplace_extras import brl

register = template.Library()


def _lista(modelo, filtro=""):
    url = reverse(f"admin:marketplace_{modelo}_changelist")
    return f"{url}?{filtro}" if filtro else url


@register.simple_tag(takes_context=True)
def painel_resumo(context):
    usuario = context["request"].user
    cartoes = []

    def pode(modelo):
        return usuario.has_perm(f"marketplace.view_{modelo}")

    if pode("denuncia"):
        total = Denuncia.objects.filter(status="pendente").count()
        cartoes.append({
            "titulo": "Denúncias pendentes", "valor": total, "alerta": total > 0,
            "ajuda": "anúncios para analisar", "url": _lista("denuncia", "status__exact=pendente"),
        })
    if pode("contato"):
        total = Contato.objects.filter(status="pendente").count()
        cartoes.append({
            "titulo": "Mensagens de contato", "valor": total, "alerta": total > 0,
            "ajuda": "sem resposta", "url": _lista("contato", "status__exact=pendente"),
        })
    if pode("pedido"):
        total = Pedido.objects.filter(status_pedido="aguardando_pagamento").count()
        cartoes.append({
            "titulo": "Pedidos aguardando pagamento", "valor": total, "alerta": False,
            "ajuda": "à espera do vendedor", "url": _lista("pedido", "status_pedido__exact=aguardando_pagamento"),
        })
        inicio_mes = timezone.localtime().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        vendido = (
            Pedido.objects.filter(data_criacao__gte=inicio_mes)
            .exclude(status_pedido="cancelado")
            .aggregate(total=Sum("valor_total"))["total"] or 0
        )
        cartoes.append({
            "titulo": "Vendido no mês", "valor": brl(vendido), "alerta": False,
            "ajuda": "pedidos não cancelados", "url": _lista("pedido"),
        })
        ano = timezone.localdate().year
        do_ano = resumo_do_ano(ano)
        cartoes.append({
            "titulo": f"Movimentado em {ano}", "valor": brl(do_ano["total"]), "alerta": False,
            "ajuda": f"{do_ano['pedidos']} pedido{'s' if do_ano['pedidos'] != 1 else ''} · ver relatório anual",
            "url": reverse("admin:marketplace_pedido_relatorio"),
        })
    if pode("perguntaproduto"):
        total = PerguntaProduto.objects.filter(resposta__isnull=True, status="publicada").count()
        cartoes.append({
            "titulo": "Perguntas sem resposta", "valor": total, "alerta": False,
            "ajuda": "aguardando os vendedores", "url": _lista("perguntaproduto", "resposta__isnull=True"),
        })
    if pode("produto"):
        cartoes.append({
            "titulo": "Anúncios ativos", "valor": Produto.objects.filter(status_anuncio="ativo").count(),
            "alerta": False, "ajuda": "à venda na loja", "url": _lista("produto", "status_anuncio__exact=ativo"),
        })
    if pode("usuario"):
        semana = timezone.now() - timedelta(days=7)
        cartoes.append({
            "titulo": "Usuários", "valor": Usuario.objects.filter(is_active=True).count(), "alerta": False,
            "ajuda": f"{Usuario.objects.filter(data_cadastro__gte=semana).count()} novos nos últimos 7 dias",
            "url": _lista("usuario"),
        })
    return cartoes
