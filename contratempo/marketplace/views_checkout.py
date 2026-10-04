"""
marketplace/views_checkout.py

Fluxo de compra em 3 etapas (endereço → pagamento → revisão) e a área
"Meus pedidos" do comprador. As escolhas de endereço e pagamento ficam
na sessão até a confirmação; os pedidos só são criados no POST da
revisão, dentro de uma transação que trava o estoque (select_for_update).

A compra é dividida em UM pedido por vendedor. Cada pedido tem o frete
da UF de entrega (tabela TabelaFrete) e é enviado e atualizado pelo
próprio vendedor (ver views_vendas.py).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .emails import enviar_aviso_venda, enviar_cancelamento_ao_vendedor, enviar_confirmacao_compra
from .forms import AvaliacaoForm, validar_cvv
from .frete import calcular_envios, faixa_para_uf, resumo_envios
from .models import Avaliacao, Carrinho, ItemPedido, Pedido, Produto
from .views import itens_do_carrinho, validar_itens_carrinho

SESSAO_ENDERECO = "checkout_endereco_id"
SESSAO_PAGAMENTO = "checkout_pagamento_id"  # id do cartão, "pix" ou "boleto"
SESSAO_PEDIDOS = "checkout_pedidos_criados"

# Formas que não precisam de cadastro: são escolhidas direto no checkout.
OPCOES_SEM_CADASTRO = {
    "pix": ("PIX", "Pagamento instantâneo pelo app do seu banco."),
    "boleto": ("Boleto", "Compensação em até 3 dias úteis."),
}

ETAPAS_PEDIDO = [
    ("aguardando_pagamento", "Pedido realizado"),
    ("pagamento_aprovado", "Pagamento aprovado"),
    ("processamento", "Em preparação"),
    ("enviado", "Enviado"),
    ("entregue", "Entregue"),
]


class CheckoutInvalido(Exception):
    pass


def _carrinho_para_checkout(request):
    """
    Devolve (carrinho, itens, redirect). O redirect vem preenchido se o
    carrinho não puder seguir (vazio ou com itens indisponíveis).
    """
    carrinho = Carrinho.objects.filter(usuario=request.user, status="ativo").first()
    itens = itens_do_carrinho(carrinho)
    if not itens:
        messages.info(request, "Seu carrinho está vazio.")
        return None, None, redirect("carrinho")
    if validar_itens_carrinho(itens):
        messages.error(request, "Alguns itens do carrinho precisam de atenção antes de continuar.")
        return None, None, redirect("carrinho")
    return carrinho, itens, None


def _contexto_envios(itens, endereco):
    envios, faixa = calcular_envios(itens, endereco.estado if endereco else None)
    return {
        "envios": envios,
        "faixa": faixa,
        "itens": itens,
        "total_itens": sum(item.quantidade for item in itens),
        **resumo_envios(envios),
    }


def _snapshot_endereco(endereco):
    partes = [f"{endereco.logradouro}, {endereco.numero}"]
    if endereco.complemento:
        partes.append(endereco.complemento)
    partes.append(f"{endereco.bairro} — {endereco.cidade}/{endereco.estado}")
    partes.append(f"CEP {endereco.cep} — {endereco.pais}")
    return f"{endereco.nome_endereco}: " + ", ".join(partes)


def _breadcrumbs_checkout(etapa):
    return [
        {"label": "Carrinho", "url": reverse("carrinho")},
        {"label": f"Checkout — {etapa}", "url": None},
    ]


def _pagamento_escolhido(usuario, valor):
    """
    Interpreta a escolha de pagamento (id do cartão, "pix" ou "boleto").
    Devolve (cartão ou None, texto que vai para o pedido). O texto é None
    se a escolha for inválida — cartão de outra pessoa, apagado ou vencido.
    """
    if valor in OPCOES_SEM_CADASTRO:
        return None, OPCOES_SEM_CADASTRO[valor][0]
    if not str(valor).isdigit():
        return None, None
    cartao = usuario.formas_pagamento.filter(pk=valor).first()
    if cartao is None or cartao.vencido:
        return None, None
    return cartao, cartao.descricao


def _endereco_da_sessao(request):
    """Endereço escolhido na etapa 1, desde que a UF tenha frete."""
    endereco = request.user.enderecos.filter(pk=request.session.get(SESSAO_ENDERECO)).first()
    if endereco and faixa_para_uf(endereco.estado) is None:
        return None
    return endereco


# =====================================================================
# CHECKOUT
# =====================================================================

@login_required
def checkout_endereco(request):
    _, itens, redirecionar = _carrinho_para_checkout(request)
    if redirecionar:
        return redirecionar

    enderecos = list(request.user.enderecos.order_by("-endereco_principal", "nome_endereco"))
    qtd_vendedores = len({item.produto.vendedor_id for item in itens})
    for endereco in enderecos:
        endereco.faixa = faixa_para_uf(endereco.estado)
        endereco.frete_total = endereco.faixa.valor * qtd_vendedores if endereco.faixa else None

    atendidos = [e for e in enderecos if e.faixa]
    selecionado = request.session.get(SESSAO_ENDERECO)
    if selecionado not in [e.pk for e in atendidos]:
        selecionado = atendidos[0].pk if atendidos else None

    if request.method == "POST":
        endereco = next((e for e in atendidos if str(e.pk) == request.POST.get("endereco")), None)
        if endereco:
            request.session[SESSAO_ENDERECO] = endereco.pk
            return redirect("checkout_pagamento")
        messages.error(request, "Selecione um endereço de entrega atendido pelo frete.")

    endereco_resumo = next((e for e in atendidos if e.pk == selecionado), None)
    return render(request, "compra/checkout_endereco.html", {
        **_contexto_envios(itens, endereco_resumo),
        "enderecos": enderecos,
        "selecionado": selecionado,
        "qtd_vendedores": qtd_vendedores,
        "etapa": 1,
        "breadcrumbs": _breadcrumbs_checkout("Entrega"),
    })


@login_required
def checkout_pagamento(request):
    _, itens, redirecionar = _carrinho_para_checkout(request)
    if redirecionar:
        return redirecionar

    endereco = _endereco_da_sessao(request)
    if not endereco:
        return redirect("checkout_endereco")

    cartoes = list(request.user.formas_pagamento.order_by("-principal", "-data_cadastro"))
    validos = [str(c.pk) for c in cartoes if not c.vencido]
    selecionado = str(request.session.get(SESSAO_PAGAMENTO, ""))
    if selecionado not in validos and selecionado not in OPCOES_SEM_CADASTRO:
        selecionado = validos[0] if validos else "pix"

    erro_cvv = None
    if request.method == "POST":
        escolha = request.POST.get("forma_pagamento", "")
        cartao, rotulo = _pagamento_escolhido(request.user, escolha)
        if rotulo is None:
            messages.error(request, "Selecione uma forma de pagamento válida.")
        else:
            selecionado = escolha
            if cartao:
                # O CVV é conferido e descartado: nunca vai para a sessão nem para o banco.
                try:
                    validar_cvv(request.POST.get("cvv"), cartao.bandeira)
                except ValidationError as erro:
                    erro_cvv = erro.messages[0]
            if not erro_cvv:
                request.session[SESSAO_PAGAMENTO] = escolha
                return redirect("checkout_revisao")

    return render(request, "compra/checkout_pagamento.html", {
        **_contexto_envios(itens, endereco),
        "endereco": endereco,
        "cartoes": cartoes,
        "opcoes_sem_cadastro": OPCOES_SEM_CADASTRO.items(),
        "erro_cvv": erro_cvv,
        "selecionado": selecionado,
        "etapa": 2,
        "breadcrumbs": _breadcrumbs_checkout("Pagamento"),
    })


@login_required
def checkout_revisao(request):
    carrinho, itens, redirecionar = _carrinho_para_checkout(request)
    if redirecionar:
        return redirecionar

    endereco = _endereco_da_sessao(request)
    if not endereco:
        return redirect("checkout_endereco")
    cartao, rotulo_pagamento = _pagamento_escolhido(request.user, request.session.get(SESSAO_PAGAMENTO, ""))
    if rotulo_pagamento is None:
        return redirect("checkout_pagamento")

    if request.method == "POST":
        try:
            pedidos = _criar_pedidos(request.user, carrinho, itens, endereco, cartao, rotulo_pagamento)
        except CheckoutInvalido as erro:
            messages.error(request, str(erro))
            return redirect("carrinho")

        request.session.pop(SESSAO_ENDERECO, None)
        request.session.pop(SESSAO_PAGAMENTO, None)
        request.session[SESSAO_PEDIDOS] = [p.id for p in pedidos]

        enviar_confirmacao_compra(request, request.user, pedidos)
        for pedido in pedidos:
            enviar_aviso_venda(request, pedido)
        return redirect("pedido_concluido")

    return render(request, "compra/checkout_revisao.html", {
        **_contexto_envios(itens, endereco),
        "endereco": endereco,
        "cartao": cartao,
        "rotulo_pagamento": rotulo_pagamento,
        "etapa": 3,
        "breadcrumbs": _breadcrumbs_checkout("Revisão"),
    })


@transaction.atomic
def _criar_pedidos(usuario, carrinho, itens, endereco, cartao, rotulo_pagamento):
    """
    Cria um pedido por vendedor. Qualquer problema desfaz tudo.
    `cartao` é None quando o pagamento é PIX ou boleto.
    """
    faixa = faixa_para_uf(endereco.estado)
    if faixa is None:
        raise CheckoutInvalido(f"Ainda não entregamos em {endereco.estado}. Escolha outro endereço.")

    ids = [item.produto_id for item in itens]
    produtos = {p.id: p for p in Produto.objects.select_for_update().filter(id__in=ids)}

    for item in itens:
        produto = produtos.get(item.produto_id)
        if produto is None or produto.status_anuncio != "ativo":
            raise CheckoutInvalido(f'"{item.produto.nome}" não está mais disponível.')
        if produto.vendedor_id == usuario.id:
            raise CheckoutInvalido(f'"{produto.nome}" é um anúncio seu e não pode ser comprado.')
        if item.quantidade > produto.quantidade_disponivel:
            raise CheckoutInvalido(
                f'Só há {produto.quantidade_disponivel} unidade(s) de "{produto.nome}". Ajuste o carrinho.'
            )

    envios, _ = calcular_envios(itens, endereco.estado)
    snapshot_endereco = _snapshot_endereco(endereco)[:500]
    snapshot_pagamento = rotulo_pagamento[:150]
    pedidos = []

    for envio in envios:
        subtotal = sum(produtos[i.produto_id].preco * i.quantidade for i in envio["itens"])
        pedido = Pedido.objects.create(
            usuario=usuario,
            vendedor=envio["vendedor"],
            endereco=endereco,
            forma_pagamento=cartao,
            endereco_snapshot=snapshot_endereco,
            forma_pagamento_snapshot=snapshot_pagamento,
            valor_frete=faixa.valor,
            prazo_entrega_dias=faixa.prazo_dias,
            valor_total=subtotal + faixa.valor,
        )
        for item in envio["itens"]:
            produto = produtos[item.produto_id]
            ItemPedido.objects.create(
                pedido=pedido,
                produto=produto,
                nome_produto=produto.nome,
                preco_unitario=produto.preco,
                quantidade=item.quantidade,
                subtotal=produto.preco * item.quantidade,
            )
            produto.quantidade_disponivel -= item.quantidade
            campos = ["quantidade_disponivel", "data_atualizacao"]
            if produto.quantidade_disponivel == 0:
                produto.status_anuncio = "vendido"
                campos.append("status_anuncio")
            produto.save(update_fields=campos)
        pedidos.append(pedido)

    carrinho.status = "finalizado"
    carrinho.save(update_fields=["status", "data_atualizacao"])
    return pedidos


# =====================================================================
# PEDIDOS DO COMPRADOR
# =====================================================================

def _pedido_do_usuario(request, pedido_id):
    return get_object_or_404(
        Pedido.objects.select_related("vendedor").prefetch_related("itens__produto__imagens"),
        pk=pedido_id, usuario=request.user,
    )


def devolver_estoque(pedido):
    """Devolve ao estoque as unidades de um pedido cancelado."""
    for item in pedido.itens.select_related("produto"):
        if item.produto_id is None:
            continue
        produto = Produto.objects.select_for_update().get(pk=item.produto_id)
        produto.quantidade_disponivel += item.quantidade
        campos = ["quantidade_disponivel", "data_atualizacao"]
        if produto.status_anuncio == "vendido":
            produto.status_anuncio = "ativo"
            campos.append("status_anuncio")
        produto.save(update_fields=campos)


def linha_do_tempo(pedido):
    codigos = [codigo for codigo, _ in ETAPAS_PEDIDO]
    atual = codigos.index(pedido.status_pedido) if pedido.status_pedido in codigos else -1
    return [
        {"rotulo": rotulo, "feito": i <= atual, "atual": i == atual}
        for i, (_, rotulo) in enumerate(ETAPAS_PEDIDO)
    ]


@login_required
def pedido_concluido(request):
    ids = request.session.get(SESSAO_PEDIDOS) or []
    pedidos = list(
        Pedido.objects.filter(pk__in=ids, usuario=request.user)
        .select_related("vendedor").prefetch_related("itens").order_by("id")
    )
    if not pedidos:
        return redirect("pedidos")
    return render(request, "compra/concluido.html", {
        "pedidos": pedidos,
        "total": sum(p.valor_total for p in pedidos),
        "breadcrumbs": [{"label": "Compra concluída", "url": None}],
    })


@login_required
def pedidos(request):
    qs = (
        Pedido.objects.filter(usuario=request.user)
        .select_related("vendedor").prefetch_related("itens__produto__imagens")
    )

    status = request.GET.get("status", "")
    if status in dict(Pedido.STATUS_CHOICES):
        qs = qs.filter(status_pedido=status)
    else:
        status = ""

    page_obj = Paginator(qs.order_by("-data_criacao"), 10).get_page(request.GET.get("page"))
    return render(request, "pedidos/lista.html", {
        "page_obj": page_obj,
        "pedidos": page_obj.object_list,
        "status": status,
        "status_choices": Pedido.STATUS_CHOICES,
        "breadcrumbs": [
            {"label": "Minha conta", "url": reverse("perfil")},
            {"label": "Meus pedidos", "url": None},
        ],
    })


@login_required
def pedido_detalhe(request, pedido_id):
    pedido = _pedido_do_usuario(request, pedido_id)
    itens = list(pedido.itens.all())

    if pedido.status_pedido == "entregue":
        avaliados = set(
            Avaliacao.objects.filter(pedido=pedido, usuario=request.user).values_list("produto_id", flat=True)
        )
        for item in itens:
            item.pode_avaliar = item.produto_id is not None and item.produto_id not in avaliados
            item.ja_avaliado = item.produto_id in avaliados

    return render(request, "pedidos/detalhe.html", {
        "pedido": pedido,
        "itens": itens,
        "linha_do_tempo": linha_do_tempo(pedido),
        "pode_cancelar": pedido.status_pedido == "aguardando_pagamento",
        "pode_confirmar": pedido.status_pedido == "enviado",
        "avaliacao_form": AvaliacaoForm(),
        "breadcrumbs": [
            {"label": "Minha conta", "url": reverse("perfil")},
            {"label": "Meus pedidos", "url": reverse("pedidos")},
            {"label": f"Pedido #{pedido.id}", "url": None},
        ],
    })


@login_required
@require_POST
def pedido_cancelar(request, pedido_id):
    with transaction.atomic():
        pedido = get_object_or_404(Pedido.objects.select_for_update(), pk=pedido_id, usuario=request.user)
        if pedido.status_pedido != "aguardando_pagamento":
            messages.error(request, "Este pedido não pode mais ser cancelado pelo site. Fale com o suporte.")
            return redirect("pedido_detalhe", pedido_id=pedido.id)
        devolver_estoque(pedido)
        pedido.status_pedido = "cancelado"
        pedido.save(update_fields=["status_pedido", "data_atualizacao"])

    if pedido.vendedor:
        enviar_cancelamento_ao_vendedor(request, pedido)
    messages.success(request, f"Pedido #{pedido.id} cancelado.")
    return redirect("pedido_detalhe", pedido_id=pedido.id)


@login_required
@require_POST
def pedido_confirmar_recebimento(request, pedido_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, usuario=request.user)
    if pedido.status_pedido != "enviado":
        messages.error(request, "Só é possível confirmar o recebimento de pedidos enviados.")
    else:
        pedido.status_pedido = "entregue"
        pedido.save(update_fields=["status_pedido", "data_atualizacao"])
        messages.success(request, "Recebimento confirmado! Que tal avaliar os produtos?")
    return redirect("pedido_detalhe", pedido_id=pedido.id)


@login_required
@require_POST
def avaliar_produto(request, pedido_id, produto_id):
    pedido = get_object_or_404(Pedido, pk=pedido_id, usuario=request.user)
    produto = get_object_or_404(Produto, pk=produto_id)

    form = AvaliacaoForm(request.POST)
    if not form.is_valid():
        messages.error(request, "Escolha uma nota de 1 a 5 estrelas.")
        return redirect("pedido_detalhe", pedido_id=pedido.id)

    if Avaliacao.objects.filter(usuario=request.user, produto=produto, pedido=pedido).exists():
        messages.info(request, "Você já avaliou este produto neste pedido.")
        return redirect("pedido_detalhe", pedido_id=pedido.id)

    avaliacao = Avaliacao(
        usuario=request.user,
        produto=produto,
        pedido=pedido,
        nota=form.cleaned_data["nota"],
        comentario=form.cleaned_data["comentario"] or None,
    )
    try:
        avaliacao.full_clean()  # aplica a regra "só avalia quem recebeu"
    except ValidationError as erro:
        messages.error(request, " ".join(erro.messages))
        return redirect("pedido_detalhe", pedido_id=pedido.id)

    avaliacao.save()
    messages.success(request, "Obrigado pela avaliação!")
    return redirect("pedido_detalhe", pedido_id=pedido.id)
