from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST

from .emails import enviar_atualizacao_pedido, enviar_pergunta_respondida
from .models import Pedido, PerguntaProduto
from .views_checkout import devolver_estoque, linha_do_tempo
from .views_conta import _proximo


def _breadcrumbs(*itens):
    return [{"label": "Minha conta", "url": reverse("perfil")}, *itens]


@login_required
def vendas(request):
    base = Pedido.objects.filter(vendedor=request.user)
    contagem = dict(base.values_list("status_pedido").annotate(total=Count("id")))

    abas = [{"valor": "", "rotulo": "Todas", "total": sum(contagem.values())}] + [
        {"valor": valor, "rotulo": rotulo, "total": contagem.get(valor, 0)}
        for valor, rotulo in Pedido.STATUS_CHOICES
    ]

    qs = base.select_related("usuario").prefetch_related("itens__produto__imagens")
    status = request.GET.get("status", "")
    if status in dict(Pedido.STATUS_CHOICES):
        qs = qs.filter(status_pedido=status)
    else:
        status = ""

    page_obj = Paginator(qs.order_by("-data_criacao"), 10).get_page(request.GET.get("page"))
    pendentes = base.filter(status_pedido__in=["aguardando_pagamento", "pagamento_aprovado", "processamento"]).count()

    return render(request, "vendas/lista.html", {
        "page_obj": page_obj,
        "vendas": page_obj.object_list,
        "abas": abas,
        "status": status,
        "pendentes": pendentes,
        "breadcrumbs": _breadcrumbs({"label": "Minhas vendas", "url": None}),
    })


@login_required
def venda_detalhe(request, pedido_id):
    pedido = get_object_or_404(
        Pedido.objects.select_related("usuario").prefetch_related("itens__produto__imagens"),
        pk=pedido_id, vendedor=request.user,
    )
    proximo = Pedido.PROXIMO_STATUS_VENDEDOR.get(pedido.status_pedido)
    return render(request, "vendas/detalhe.html", {
        "pedido": pedido,
        "itens": pedido.itens.all(),
        "linha_do_tempo": linha_do_tempo(pedido),
        "proximo_status": proximo,
        "proximo_rotulo": dict(Pedido.STATUS_CHOICES).get(proximo),
        "pode_cancelar": pedido.status_pedido in ("aguardando_pagamento", "pagamento_aprovado", "processamento"),
        "breadcrumbs": _breadcrumbs(
            {"label": "Minhas vendas", "url": reverse("vendas")},
            {"label": f"Pedido #{pedido.id}", "url": None},
        ),
    })


@login_required
@require_POST
def venda_avancar(request, pedido_id):
    with transaction.atomic():
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id, vendedor=request.user)
        proximo = Pedido.PROXIMO_STATUS_VENDEDOR.get(pedido.status_pedido)

        if not proximo or request.POST.get("status_atual") != pedido.status_pedido:
            messages.error(request, "O pedido já foi atualizado. Confira o status atual.")
            return redirect("venda_detalhe", pedido_id=pedido.id)

        campos = ["status_pedido", "data_atualizacao"]
        if proximo == "enviado":
            codigo = (request.POST.get("codigo_rastreio") or "").strip().upper()
            if not (5 <= len(codigo) <= 50):
                messages.error(request, "Informe o código de rastreio para marcar o pedido como enviado.")
                return redirect("venda_detalhe", pedido_id=pedido.id)
            pedido.codigo_rastreio = codigo
            pedido.data_envio = timezone.now()
            campos += ["codigo_rastreio", "data_envio"]

        pedido.status_pedido = proximo
        pedido.save(update_fields=campos)

    enviar_atualizacao_pedido(request, pedido)
    messages.success(request, f"Pedido #{pedido.id}: {pedido.get_status_pedido_display().lower()}. O comprador foi avisado por e-mail.")
    return redirect("venda_detalhe", pedido_id=pedido.id)


@login_required
@require_POST
def venda_cancelar(request, pedido_id):
    with transaction.atomic():
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id, vendedor=request.user)
        if pedido.status_pedido not in ("aguardando_pagamento", "pagamento_aprovado", "processamento"):
            messages.error(request, "Pedidos enviados, entregues ou já cancelados não podem ser cancelados.")
            return redirect("venda_detalhe", pedido_id=pedido.id)
        devolver_estoque(pedido)
        pedido.status_pedido = "cancelado"
        pedido.save(update_fields=["status_pedido", "data_atualizacao"])

    enviar_atualizacao_pedido(request, pedido)
    messages.success(request, f"Pedido #{pedido.id} cancelado. As unidades voltaram ao estoque e o comprador foi avisado.")
    return redirect("venda_detalhe", pedido_id=pedido.id)


@login_required
def perguntas_recebidas(request):
    base = PerguntaProduto.objects.filter(produto__vendedor=request.user, status="publicada")
    filtro = request.GET.get("filtro", "pendentes")
    qs = base.select_related("produto", "usuario").prefetch_related("produto__imagens")
    if filtro == "respondidas":
        qs = qs.filter(resposta__isnull=False)
    else:
        filtro = "pendentes"
        qs = qs.filter(resposta__isnull=True)

    totais = base.aggregate(
        pendentes=Count("id", filter=Q(resposta__isnull=True)),
        respondidas=Count("id", filter=Q(resposta__isnull=False)),
    )
    page_obj = Paginator(qs.order_by("-data_pergunta"), 15).get_page(request.GET.get("page"))
    return render(request, "vendas/perguntas.html", {
        "page_obj": page_obj,
        "perguntas": page_obj.object_list,
        "filtro": filtro,
        "totais": totais,
        "breadcrumbs": _breadcrumbs({"label": "Perguntas recebidas", "url": None}),
    })


@login_required
@require_POST
def responder_pergunta(request, pergunta_id):
    pergunta = get_object_or_404(
        PerguntaProduto.objects.select_related("produto", "usuario"),
        pk=pergunta_id, produto__vendedor=request.user,
    )
    resposta = (request.POST.get("resposta") or "").strip()
    if not resposta:
        messages.error(request, "Escreva a resposta antes de enviar.")
    elif len(resposta) > 1000:
        messages.error(request, "A resposta pode ter no máximo 1000 caracteres.")
    else:
        primeira_resposta = pergunta.resposta is None
        pergunta.resposta = resposta
        pergunta.data_resposta = timezone.now()
        pergunta.save(update_fields=["resposta", "data_resposta"])
        if primeira_resposta:
            enviar_pergunta_respondida(request, pergunta)
        messages.success(request, "Resposta publicada no anúncio.")
    return redirect(_proximo(request, "perguntas_recebidas"))
