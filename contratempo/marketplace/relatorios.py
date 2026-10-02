"""
marketplace/relatorios.py

Números do relatório anual do admin (/admin/marketplace/pedido/relatorio-anual/)
e do cartão "Movimentado no ano" do painel.

"Movimentado" = soma dos pedidos NÃO cancelados (produtos + frete),
pela data em que o pedido foi feito.

Os meses são separados em Python (timezone.localtime), e não com
TruncMonth no banco: assim o relatório não depende das tabelas de fuso
horário do MySQL (que não vêm instaladas no Windows).
"""

from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlencode

from django.db.models import Max, Min
from django.urls import reverse
from django.utils import timezone

from .models import Pedido

MESES = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho",
         "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
ZERO = Decimal("0")


def inicio_do_ano(ano):
    return timezone.make_aware(datetime(ano, 1, 1))


def _intervalo(inicio, fim):
    """Filtro da lista de pedidos do admin entre duas datas."""
    return {"data_criacao__gte": str(inicio), "data_criacao__lt": str(fim)}


def link_pedidos(**filtros):
    return reverse("admin:marketplace_pedido_changelist") + "?" + urlencode(filtros)


def anos_disponiveis():
    """Anos que têm pedidos (mais o atual), do mais recente ao mais antigo."""
    datas = Pedido.objects.aggregate(primeiro=Min("data_criacao"), ultimo=Max("data_criacao"))
    atual = timezone.localdate().year
    if not datas["primeiro"]:
        return [atual]
    primeiro = timezone.localtime(datas["primeiro"]).year
    ultimo = max(timezone.localtime(datas["ultimo"]).year, atual)
    return list(range(ultimo, primeiro - 1, -1))


def resumo_do_ano(ano):
    """Total movimentado e número de pedidos válidos no ano (para o cartão)."""
    pedidos = (
        Pedido.objects
        .filter(data_criacao__gte=inicio_do_ano(ano), data_criacao__lt=inicio_do_ano(ano + 1))
        .exclude(status_pedido="cancelado")
        .values_list("valor_total", flat=True)
    )
    valores = list(pedidos)
    return {"total": sum(valores, ZERO), "pedidos": len(valores)}


def relatorio_anual(ano):
    inicio, fim = inicio_do_ano(ano), inicio_do_ano(ano + 1)
    pedidos = (
        Pedido.objects
        .filter(data_criacao__gte=inicio, data_criacao__lt=fim)
        .select_related("vendedor")
        .only("id", "status_pedido", "valor_total", "valor_frete", "data_criacao",
              "vendedor__id", "vendedor__nome_completo", "vendedor__email")
    )

    meses = [{"numero": m, "nome": MESES[m - 1], "pedidos": 0, "produtos": ZERO, "frete": ZERO,
              "total": ZERO, "cancelados": 0} for m in range(1, 13)]
    por_status = defaultdict(lambda: {"pedidos": 0, "total": ZERO})
    vendedores = {}
    totais = {"pedidos": 0, "produtos": ZERO, "frete": ZERO, "total": ZERO,
              "cancelados": 0, "valor_cancelado": ZERO}

    for pedido in pedidos:
        mes = meses[timezone.localtime(pedido.data_criacao).month - 1]
        por_status[pedido.status_pedido]["pedidos"] += 1
        por_status[pedido.status_pedido]["total"] += pedido.valor_total

        if pedido.status_pedido == "cancelado":
            mes["cancelados"] += 1
            totais["cancelados"] += 1
            totais["valor_cancelado"] += pedido.valor_total
            continue

        produtos = pedido.valor_total - pedido.valor_frete
        for alvo in (mes, totais):
            alvo["pedidos"] += 1
            alvo["produtos"] += produtos
            alvo["frete"] += pedido.valor_frete
            alvo["total"] += pedido.valor_total

        if pedido.vendedor_id:
            v = vendedores.setdefault(pedido.vendedor_id, {
                "vendedor": pedido.vendedor, "pedidos": 0, "total": ZERO,
                "url": reverse("admin:marketplace_usuario_change", args=[pedido.vendedor_id]),
            })
            v["pedidos"] += 1
            v["total"] += pedido.valor_total

    # Barras proporcionais ao maior mês e links para os pedidos de cada mês
    maior = max((m["total"] for m in meses), default=ZERO)
    for m in meses:
        m["percentual"] = round(100 * m["total"] / maior) if maior else 0
        fim_mes = inicio_do_ano(ano + 1) if m["numero"] == 12 else timezone.make_aware(datetime(ano, m["numero"] + 1, 1))
        m["url"] = link_pedidos(**_intervalo(timezone.make_aware(datetime(ano, m["numero"], 1)), fim_mes))

    totais["ticket_medio"] = (totais["total"] / totais["pedidos"]) if totais["pedidos"] else ZERO
    melhor_mes = max(meses, key=lambda m: m["total"]) if maior else None

    nomes_status = dict(Pedido.STATUS_CHOICES)
    status = [
        {
            "codigo": codigo, "nome": nomes_status[codigo],
            "pedidos": por_status[codigo]["pedidos"], "total": por_status[codigo]["total"],
            "url": link_pedidos(status_pedido__exact=codigo, **_intervalo(inicio, fim)),
        }
        for codigo, _ in Pedido.STATUS_CHOICES if por_status[codigo]["pedidos"]
    ]

    return {
        "ano": ano,
        "meses": meses,
        "totais": totais,
        "melhor_mes": melhor_mes,
        "status": status,
        "top_vendedores": sorted(vendedores.values(), key=lambda v: v["total"], reverse=True)[:5],
        "url_ano": link_pedidos(**_intervalo(inicio, fim)),
    }
