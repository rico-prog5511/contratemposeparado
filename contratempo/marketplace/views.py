"""
marketplace/views.py

Vitrine pública: home, catálogo/busca, categorias, detalhe do produto,
carrinho e páginas institucionais (sobre nós, contato, privacidade).

As demais áreas ficam em arquivos próprios:
    views_conta.py     — login, cadastro, perfil, endereços, pagamentos
    views_checkout.py  — checkout e pedidos
    views_anuncios.py  — área do vendedor (anúncios e estoque)
    views_errors.py    — páginas 403 / 404 / 500
"""

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from django.http import JsonResponse
from django.templatetags.static import static

from .busca import filtrar as filtrar_busca
from .busca import palavras as palavras_busca
from .emails import enviar_nova_pergunta
from .forms import ContatoForm
from .frete import calcular_envios, faixa_para_uf, resumo_envios, uf_por_cep
from .templatetags.marketplace_extras import brl, imagem_principal
from .models import (
    Avaliacao,
    Carrinho,
    Categoria,
    Denuncia,
    Franquia,
    ItemCarrinho,
    ItemPedido,
    PerguntaFrequente,
    PerguntaProduto,
    Produto,
    Usuario,
)

ORDENACOES = {
    "recentes": ("-data_criacao", "Mais recentes"),
    "menor_preco": ("preco", "Menor preço"),
    "maior_preco": ("-preco", "Maior preço"),
    "nome": ("nome", "Nome (A–Z)"),
}
PRODUTOS_POR_PAGINA = 12


def produtos_ativos():
    """Queryset base de tudo que aparece na vitrine."""
    return (
        Produto.objects
        .filter(status_anuncio="ativo")
        .select_related("categoria", "franquia")
        .prefetch_related("imagens")
    )


def _decimal_ou_none(valor):
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero >= 0 else None


def _url_segura(request, url):
    return url and url_has_allowed_host_and_scheme(
        url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    )


# =====================================================================
# HOME E INSTITUCIONAL
# =====================================================================

def home(request):
    categorias = (
        Categoria.objects
        .filter(ativo=True)
        .annotate(total_produtos=Count("produtos", filter=Q(produtos__status_anuncio="ativo")))
        .order_by("nome")
    )

    # "Mais vendidos": soma das quantidades em pedidos não cancelados.
    produtos_destaque = (
        produtos_ativos()
        .annotate(total_vendido=Coalesce(
            Sum("itens_pedido__quantidade", filter=~Q(itens_pedido__pedido__status_pedido="cancelado")),
            0,
        ))
        .order_by("-total_vendido", "-data_criacao")[:8]
    )

    produtos_recentes = produtos_ativos().order_by("-data_criacao")[:4]

    return render(request, "home.html", {
        "categorias": categorias,
        "produtos_destaque": produtos_destaque,
        "produtos_recentes": produtos_recentes,
    })


def sobre_nos(request):
    return render(request, "sobre_nos.html", {
        "breadcrumbs": [{"label": "Sobre nós", "url": None}],
    })


def privacidade(request):
    return render(request, "privacidade.html", {
        "breadcrumbs": [{"label": "Política de privacidade", "url": None}],
    })


def contato(request):
    inicial = {}
    if request.user.is_authenticated:
        inicial = {"nome": request.user.nome_completo, "email": request.user.email}

    if request.method == "POST":
        form = ContatoForm(request.POST)
        if form.is_valid():
            mensagem = form.save(commit=False)
            if request.user.is_authenticated:
                mensagem.usuario = request.user
            mensagem.save()
            messages.success(request, "Mensagem enviada! Responderemos pelo e-mail informado.")
            return redirect("contato")
    else:
        form = ContatoForm(initial=inicial)

    return render(request, "contato.html", {
        "form": form,
        "breadcrumbs": [{"label": "Contato", "url": None}],
    })


# =====================================================================
# CATÁLOGO, BUSCA E CATEGORIAS
# =====================================================================

def produtos(request):
    qs = produtos_ativos()

    busca = request.GET.get("q", "").strip()[:100]
    if busca:
        qs = filtrar_busca(qs, busca)

    categoria_atual = None
    categoria_slug = request.GET.get("categoria", "").strip()
    if categoria_slug:
        categoria_atual = Categoria.objects.filter(slug=categoria_slug, ativo=True).first()
        if categoria_atual:
            qs = qs.filter(categoria=categoria_atual)

    vendedor_atual = None
    vendedor_id = request.GET.get("vendedor", "")
    if vendedor_id.isdigit():
        vendedor_atual = Usuario.objects.filter(pk=vendedor_id, is_active=True).first()
        if vendedor_atual:
            qs = qs.filter(vendedor=vendedor_atual)

    franquias_selecionadas = [slug for slug in request.GET.getlist("franquia") if slug]
    if franquias_selecionadas:
        qs = qs.filter(franquia__slug__in=franquias_selecionadas)

    condicoes_validas = dict(Produto.CONDICAO_CHOICES)
    condicoes_selecionadas = [c for c in request.GET.getlist("condicao") if c in condicoes_validas]
    if condicoes_selecionadas:
        qs = qs.filter(condicao__in=condicoes_selecionadas)

    preco_min = _decimal_ou_none(request.GET.get("preco_min")) if request.GET.get("preco_min") else None
    preco_max = _decimal_ou_none(request.GET.get("preco_max")) if request.GET.get("preco_max") else None
    if preco_min is not None:
        qs = qs.filter(preco__gte=preco_min)
    if preco_max is not None:
        qs = qs.filter(preco__lte=preco_max)

    ordenar = request.GET.get("ordenar", "recentes")
    if ordenar not in ORDENACOES:
        ordenar = "recentes"
    qs = qs.order_by(ORDENACOES[ordenar][0], "-id")

    page_obj = Paginator(qs, PRODUTOS_POR_PAGINA).get_page(request.GET.get("page"))

    total_filtros = (
        len(franquias_selecionadas) + len(condicoes_selecionadas)
        + (preco_min is not None) + (preco_max is not None)
    )

    breadcrumbs = [{"label": "Produtos", "url": reverse("produtos") if categoria_atual or busca else None}]
    if categoria_atual:
        breadcrumbs.append({"label": categoria_atual.nome, "url": None})
    if busca:
        breadcrumbs.append({"label": f'Busca: "{busca}"', "url": None})
    if vendedor_atual:
        breadcrumbs.append({"label": f"Vendedor: {vendedor_atual.nome_completo}", "url": None})

    return render(request, "produtos/lista.html", {
        "page_obj": page_obj,
        "produtos": page_obj.object_list,
        "busca": busca,
        "categoria_atual": categoria_atual,
        "vendedor_atual": vendedor_atual,
        "categorias": Categoria.objects.filter(ativo=True).order_by("nome"),
        "franquias": Franquia.objects.filter(ativo=True).order_by("nome"),
        "condicoes": Produto.CONDICAO_CHOICES,
        "franquias_selecionadas": franquias_selecionadas,
        "condicoes_selecionadas": condicoes_selecionadas,
        "preco_min": request.GET.get("preco_min", ""),
        "preco_max": request.GET.get("preco_max", ""),
        "ordenar": ordenar,
        "ordenacoes": [(chave, rotulo) for chave, (_, rotulo) in ORDENACOES.items()],
        "total_filtros": total_filtros,
        "breadcrumbs": breadcrumbs,
    })


def sugestoes_busca(request):
    """
    JSON das sugestões que aparecem enquanto a pessoa digita na busca do
    topo (ver main.js). Usa a mesma busca do catálogo, sem acentos.
    """
    termo = request.GET.get("q", "").strip()[:100]
    if len("".join(palavras_busca(termo))) < 2:
        return JsonResponse({"produtos": [], "categorias": []})

    produtos = filtrar_busca(
        produtos_ativos(), termo, ["nome", "marca", "franquia__nome", "categoria__nome"]
    ).order_by("-data_criacao")[:6]
    categorias_encontradas = filtrar_busca(Categoria.objects.filter(ativo=True), termo, ["nome"]).order_by("nome")[:3]

    return JsonResponse({
        "produtos": [
            {
                "nome": p.nome,
                "preco": brl(p.preco),
                "categoria": p.categoria.nome,
                "imagem": imagem_principal(p) or static("img/produto-sem-imagem.svg"),
                "url": reverse("produto_detalhe", args=[p.id]),
            }
            for p in produtos
        ],
        "categorias": [
            {"nome": c.nome, "url": f"{reverse('produtos')}?categoria={c.slug}"}
            for c in categorias_encontradas
        ],
    })


def categorias(request):
    lista = (
        Categoria.objects
        .filter(ativo=True)
        .annotate(total_produtos=Count("produtos", filter=Q(produtos__status_anuncio="ativo")))
        .order_by("nome")
    )
    return render(request, "produtos/categorias.html", {
        "categorias": lista,
        "breadcrumbs": [{"label": "Categorias", "url": None}],
    })


def _calcular_frete_cep(cep):
    """Resultado da calculadora de frete da página de produto."""
    if not cep:
        return None
    uf = uf_por_cep(cep)
    if uf is None:
        return {"erro": "CEP inválido. Informe os 8 dígitos."}
    faixa = faixa_para_uf(uf)
    if faixa is None:
        return {"erro": f"Ainda não entregamos em {uf}."}
    return {"uf": uf, "valor": faixa.valor, "prazo_dias": faixa.prazo_dias}


def _resumo_vendedor(vendedor):
    """Nota média, total vendido e anúncios ativos de um vendedor."""
    avaliacoes = Avaliacao.objects.filter(produto__vendedor=vendedor, status="publicada")
    return {
        "media": avaliacoes.aggregate(m=Avg("nota"))["m"],
        "total_avaliacoes": avaliacoes.count(),
        "vendas": (
            ItemPedido.objects
            .filter(produto__vendedor=vendedor)
            .exclude(pedido__status_pedido="cancelado")
            .aggregate(t=Sum("quantidade"))["t"] or 0
        ),
        "anuncios_ativos": Produto.objects.filter(vendedor=vendedor, status_anuncio="ativo").count(),
    }


def produto_detalhe(request, produto_id):
    produto = get_object_or_404(
        Produto.objects.select_related("categoria", "franquia", "vendedor"),
        pk=produto_id,
    )
    imagens = list(produto.imagens.all().order_by("-principal", "ordem_exibicao"))

    avaliacoes = (
        Avaliacao.objects
        .filter(produto=produto, status="publicada")
        .select_related("usuario")
        .order_by("-data_avaliacao")
    )
    media_avaliacoes = avaliacoes.aggregate(media=Avg("nota"))["media"]

    produtos_relacionados = (
        produtos_ativos()
        .filter(categoria=produto.categoria)
        .exclude(pk=produto.pk)
        .exclude(vendedor=produto.vendedor)[:4]
    )
    mais_do_vendedor = (
        produtos_ativos()
        .filter(vendedor=produto.vendedor)
        .exclude(pk=produto.pk)
        .order_by("-data_criacao")[:4]
    )

    eh_dono = request.user.is_authenticated and produto.vendedor_id == request.user.id
    disponivel = produto.status_anuncio == "ativo" and produto.quantidade_disponivel > 0

    # Perguntas: todas as respondidas + as pendentes do próprio usuário
    # (o vendedor vê todas, para poder responder aqui mesmo).
    perguntas = produto.perguntas.filter(status="publicada").select_related("usuario")
    if not eh_dono:
        visiveis = Q(resposta__isnull=False)
        if request.user.is_authenticated:
            visiveis |= Q(usuario=request.user)
        perguntas = perguntas.filter(visiveis)

    # CEP da calculadora: o informado agora ou o do endereço principal.
    cep = request.GET.get("cep", "").strip()
    if not cep and request.user.is_authenticated:
        principal = request.user.enderecos.filter(endereco_principal=True).first()
        cep = principal.cep if principal else ""

    breadcrumbs = [
        {"label": "Produtos", "url": reverse("produtos")},
        {"label": produto.categoria.nome, "url": f"{reverse('produtos')}?categoria={produto.categoria.slug}"},
        {"label": produto.nome, "url": None},
    ]

    return render(request, "produto.html", {
        "produto": produto,
        "imagens": imagens,
        "avaliacoes": avaliacoes,
        "media_avaliacoes": media_avaliacoes,
        "produtos_relacionados": produtos_relacionados,
        "mais_do_vendedor": mais_do_vendedor,
        "vendedor_resumo": _resumo_vendedor(produto.vendedor),
        "perguntas": perguntas.order_by("-data_pergunta")[:30],
        "cep": cep,
        "frete": _calcular_frete_cep(cep),
        "breadcrumbs": breadcrumbs,
        "eh_dono": eh_dono,
        "disponivel": disponivel,
        "motivos_denuncia": Denuncia.MOTIVO_CHOICES,
        "ja_denunciou": (
            request.user.is_authenticated
            and Denuncia.objects.filter(produto=produto, usuario=request.user, status="pendente").exists()
        ),
    })


@login_required
@require_POST
def denunciar_produto(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)
    destino = reverse("produto_detalhe", args=[produto.id])

    if produto.vendedor_id == request.user.id:
        messages.error(request, "Você não pode denunciar o seu próprio anúncio.")
        return redirect(destino)

    motivo = request.POST.get("motivo", "")
    descricao = (request.POST.get("descricao") or "").strip()[:1000]
    if motivo not in dict(Denuncia.MOTIVO_CHOICES):
        messages.error(request, "Escolha o motivo da denúncia.")
        return redirect(destino + "#denunciar")
    if motivo == "outro" and len(descricao) < 10:
        messages.error(request, "Conte em poucas palavras qual é o problema (mínimo de 10 caracteres).")
        return redirect(destino + "#denunciar")

    if Denuncia.objects.filter(produto=produto, usuario=request.user, status="pendente").exists():
        messages.info(request, "Você já denunciou este anúncio. Nossa equipe está analisando.")
        return redirect(destino)

    Denuncia.objects.create(produto=produto, usuario=request.user, motivo=motivo, descricao=descricao or None)
    messages.success(request, "Denúncia enviada. Obrigado! Nossa equipe vai analisar o anúncio — o vendedor não fica sabendo quem denunciou.")
    return redirect(destino)


def vendedor_perfil(request, usuario_id):
    """Página pública do vendedor: reputação, avaliações e anúncios."""
    vendedor = get_object_or_404(Usuario, pk=usuario_id, is_active=True)

    avaliacoes = (
        Avaliacao.objects
        .filter(produto__vendedor=vendedor, status="publicada")
        .select_related("usuario", "produto")
        .order_by("-data_avaliacao")
    )
    contagem = dict(avaliacoes.values_list("nota").annotate(total=Count("id")))
    total_avaliacoes = sum(contagem.values())
    distribuicao = [
        {
            "nota": nota,
            "total": contagem.get(nota, 0),
            "percentual": round(100 * contagem.get(nota, 0) / total_avaliacoes) if total_avaliacoes else 0,
        }
        for nota in range(5, 0, -1)
    ]

    perguntas = PerguntaProduto.objects.filter(produto__vendedor=vendedor, status="publicada")
    total_perguntas = perguntas.count()
    respondidas = perguntas.filter(resposta__isnull=False).count()

    anuncios = produtos_ativos().filter(vendedor=vendedor)
    categorias_vendedor = (
        Categoria.objects
        .filter(produtos__in=anuncios)
        .annotate(total=Count("produtos", filter=Q(produtos__in=anuncios)))
        .order_by("-total", "nome")
    )
    page_obj = Paginator(anuncios.order_by("-data_criacao", "-id"), PRODUTOS_POR_PAGINA).get_page(request.GET.get("page"))

    return render(request, "vendedor.html", {
        "vendedor": vendedor,
        "resumo": _resumo_vendedor(vendedor),
        "distribuicao": distribuicao,
        "avaliacoes": avaliacoes[:6],
        "taxa_resposta": round(100 * respondidas / total_perguntas) if total_perguntas else None,
        "categorias_vendedor": categorias_vendedor,
        "page_obj": page_obj,
        "anuncios": page_obj.object_list,
        "eh_voce": request.user.is_authenticated and request.user.pk == vendedor.pk,
        "breadcrumbs": [
            {"label": "Produtos", "url": reverse("produtos")},
            {"label": vendedor.nome_completo, "url": None},
        ],
    })


@login_required
@require_POST
def fazer_pergunta(request, produto_id):
    produto = get_object_or_404(Produto.objects.select_related("vendedor"), pk=produto_id)
    destino = reverse("produto_detalhe", args=[produto.id]) + "#perguntas"

    if produto.vendedor_id == request.user.id:
        messages.error(request, "Você não pode fazer perguntas no seu próprio anúncio.")
        return redirect(destino)

    texto = (request.POST.get("pergunta") or "").strip()
    if len(texto) < 5:
        messages.error(request, "Escreva sua pergunta (mínimo de 5 caracteres).")
        return redirect(destino)
    if len(texto) > 500:
        messages.error(request, "A pergunta pode ter no máximo 500 caracteres.")
        return redirect(destino)

    # Evita envio duplicado (clique duplo / F5).
    if PerguntaProduto.objects.filter(produto=produto, usuario=request.user, pergunta=texto).exists():
        messages.info(request, "Você já enviou essa pergunta.")
        return redirect(destino)

    pergunta = PerguntaProduto.objects.create(produto=produto, usuario=request.user, pergunta=texto)
    enviar_nova_pergunta(request, pergunta)
    messages.success(request, "Pergunta enviada! Avisaremos por e-mail quando o vendedor responder.")
    return redirect(destino)


def faq(request):
    busca = request.GET.get("q", "").strip()
    perguntas = PerguntaFrequente.objects.filter(ativo=True)
    if busca:
        perguntas = perguntas.filter(Q(pergunta__icontains=busca) | Q(resposta__icontains=busca))

    temas = []
    rotulos = dict(PerguntaFrequente.TEMA_CHOICES)
    for codigo, _ in PerguntaFrequente.TEMA_CHOICES:
        itens = [p for p in perguntas if p.tema == codigo]
        if itens:
            temas.append({"codigo": codigo, "rotulo": rotulos[codigo], "perguntas": itens})

    return render(request, "faq.html", {
        "temas": temas,
        "busca": busca,
        "breadcrumbs": [{"label": "Dúvidas frequentes", "url": None}],
    })


# =====================================================================
# CARRINHO
# =====================================================================

def validar_itens_carrinho(itens):
    """
    Confere cada item contra o estado atual do produto e atualiza o
    preço unitário se o vendedor tiver alterado o preço. Devolve a lista
    de problemas que impedem o checkout (vazia = tudo certo).
    """
    problemas = []
    for item in itens:
        produto = item.produto
        item.problema = None
        if produto.status_anuncio != "ativo":
            item.problema = "Este anúncio não está mais disponível."
        elif produto.quantidade_disponivel == 0:
            item.problema = "Produto sem estoque."
        elif item.quantidade > produto.quantidade_disponivel:
            item.problema = f"Só há {produto.quantidade_disponivel} unidade(s) disponível(is)."
        if item.problema:
            problemas.append(item)

        if item.preco_unitario != produto.preco:
            item.preco_unitario = produto.preco
            item.save(update_fields=["preco_unitario"])
            item.preco_atualizado = True
    return problemas


def itens_do_carrinho(carrinho):
    if carrinho is None:
        return []
    return list(
        carrinho.itens
        .select_related("produto", "produto__categoria", "produto__vendedor")
        .prefetch_related("produto__imagens")
        .order_by("data_adicionado")
    )


def carrinho(request):
    if not request.user.is_authenticated:
        return render(request, "compra/carrinho.html", {
            "itens": [],
            "anonimo": True,
            "breadcrumbs": [{"label": "Carrinho", "url": None}],
        })

    carrinho_ativo = Carrinho.objects.filter(usuario=request.user, status="ativo").first()
    itens = itens_do_carrinho(carrinho_ativo)
    problemas = validar_itens_carrinho(itens)

    # Estimativa de frete pelo endereço principal (o valor final é o do
    # endereço escolhido no checkout).
    principal = request.user.enderecos.filter(endereco_principal=True).first()
    envios, faixa = calcular_envios(itens, principal.estado if principal else None)

    return render(request, "compra/carrinho.html", {
        "itens": itens,
        "problemas": problemas,
        "envios": envios,
        "faixa": faixa,
        "endereco_principal": principal,
        **resumo_envios(envios),
        "total_itens": sum(item.quantidade for item in itens),
        "breadcrumbs": [{"label": "Carrinho", "url": None}],
    })


@login_required
def adicionar_ao_carrinho(request, produto_id):
    produto = get_object_or_404(Produto, pk=produto_id)

    if request.method != "POST":
        return redirect("produto_detalhe", produto_id=produto.id)

    if produto.status_anuncio != "ativo":
        messages.error(request, "Este produto não está disponível para compra no momento.")
        return redirect("produto_detalhe", produto_id=produto.id)

    if produto.vendedor_id == request.user.id:
        messages.error(request, "Você não pode adicionar seu próprio anúncio ao carrinho.")
        return redirect("produto_detalhe", produto_id=produto.id)

    try:
        quantidade = int(request.POST.get("quantidade", 1))
    except (TypeError, ValueError):
        quantidade = 1
    quantidade = max(1, quantidade)

    carrinho_ativo = Carrinho.obter_carrinho_ativo(request.user)
    item = ItemCarrinho.objects.filter(carrinho=carrinho_ativo, produto=produto).first()
    ja_no_carrinho = item.quantidade if item else 0

    if ja_no_carrinho + quantidade > produto.quantidade_disponivel:
        restante = max(produto.quantidade_disponivel - ja_no_carrinho, 0)
        if restante == 0:
            messages.error(request, "Você já tem no carrinho todas as unidades disponíveis deste produto.")
        else:
            messages.error(request, f"Você só pode adicionar mais {restante} unidade(s) deste produto.")
        return redirect("produto_detalhe", produto_id=produto.id)

    if item:
        item.quantidade += quantidade
        item.preco_unitario = produto.preco
        item.save()
    else:
        ItemCarrinho.objects.create(
            carrinho=carrinho_ativo, produto=produto,
            quantidade=quantidade, preco_unitario=produto.preco,
        )

    if request.POST.get("comprar_agora"):
        return redirect("checkout_endereco")

    messages.success(request, f'"{produto.nome}" foi adicionado ao carrinho.')
    proximo = request.POST.get("next")
    if _url_segura(request, proximo):
        return redirect(proximo)
    return redirect("produto_detalhe", produto_id=produto.id)


def _item_do_usuario(request, item_id):
    return get_object_or_404(
        ItemCarrinho.objects.select_related("produto"),
        pk=item_id, carrinho__usuario=request.user, carrinho__status="ativo",
    )


@login_required
@require_POST
def atualizar_item_carrinho(request, item_id):
    item = _item_do_usuario(request, item_id)
    try:
        quantidade = int(request.POST.get("quantidade", item.quantidade))
    except (TypeError, ValueError):
        quantidade = item.quantidade

    if quantidade <= 0:
        item.delete()
        messages.success(request, f'"{item.produto.nome}" foi removido do carrinho.')
    elif quantidade > item.produto.quantidade_disponivel:
        messages.error(request, f"Só há {item.produto.quantidade_disponivel} unidade(s) de \"{item.produto.nome}\".")
    else:
        item.quantidade = quantidade
        item.save(update_fields=["quantidade"])
    return redirect("carrinho")


@login_required
@require_POST
def remover_item_carrinho(request, item_id):
    item = _item_do_usuario(request, item_id)
    nome = item.produto.nome
    item.delete()
    messages.success(request, f'"{nome}" foi removido do carrinho.')
    return redirect("carrinho")
