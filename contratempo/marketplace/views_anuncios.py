"""
marketplace/views_anuncios.py

Área do vendedor: listar, criar, editar, visualizar, mudar status,
excluir anúncios e gerenciar o estoque em lote.

Imagens: cada foto é reduzida, convertida para WebP e limpa dos dados
escondidos (GPS etc.) por imagens.salvar_foto_produto, que salva em
MEDIA_ROOT/produtos/<id>/ a foto e uma miniatura; a URL pública da foto
vai para ProdutoImagem.url_imagem (coluna VARCHAR já existente).
"""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Avg, Count, Q, Sum
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import LIMITE_IMAGENS_ANUNCIO, ProdutoForm
from .models import ItemPedido, Produto, ProdutoImagem
from .sku import gerar_sku
from .imagens import salvar_foto_produto
from .views_conta import _proximo

VENDAS_VALIDAS = ~Q(itens_pedido__pedido__status_pedido="cancelado")


def _meu_anuncio(request, produto_id):
    return get_object_or_404(Produto, pk=produto_id, vendedor=request.user)


def _breadcrumbs(*itens):
    return [
        {"label": "Minha conta", "url": reverse("perfil")},
        {"label": "Meus anúncios", "url": reverse("anuncios") if itens else None},
        *itens,
    ]


def _salvar_imagens(produto, arquivos):
    ordem = produto.imagens.count()
    tem_principal = produto.imagens.filter(principal=True).exists()
    for arquivo in arquivos:
        ProdutoImagem.objects.create(
            produto=produto,
            url_imagem=salvar_foto_produto(arquivo, f"produtos/{produto.id}"),
            principal=not tem_principal,
            ordem_exibicao=ordem,
        )
        tem_principal = True
        ordem += 1


# =====================================================================
# LISTA
# =====================================================================

@login_required
def anuncios(request):
    base = Produto.objects.filter(vendedor=request.user)

    contagem = dict(base.values_list("status_anuncio").annotate(total=Count("id")))
    abas = [{"valor": "", "rotulo": "Todos", "total": sum(contagem.values())}] + [
        {"valor": valor, "rotulo": rotulo, "total": contagem.get(valor, 0)}
        for valor, rotulo in Produto.STATUS_CHOICES
    ]

    qs = (
        base.select_related("categoria")
        .prefetch_related("imagens")
        .annotate(total_vendido=Coalesce(Sum("itens_pedido__quantidade", filter=VENDAS_VALIDAS), 0))
    )

    status = request.GET.get("status", "")
    if status in dict(Produto.STATUS_CHOICES):
        qs = qs.filter(status_anuncio=status)
    else:
        status = ""

    busca = request.GET.get("q", "").strip()
    if busca:
        qs = qs.filter(Q(nome__icontains=busca) | Q(sku__icontains=busca))

    page_obj = Paginator(qs.order_by("-data_atualizacao"), 10).get_page(request.GET.get("page"))

    return render(request, "anuncios/lista.html", {
        "page_obj": page_obj,
        "anuncios": page_obj.object_list,
        "abas": abas,
        "status": status,
        "busca": busca,
        "breadcrumbs": _breadcrumbs(),
    })


# =====================================================================
# CRIAR / EDITAR
# =====================================================================

def _salvar_com_sku_gerado(produto, tentativas=5):
    """
    Salva o anúncio novo com o próximo SKU livre (sku.gerar_sku). Se outra
    pessoa publicar ao mesmo tempo e pegar o mesmo código, o banco recusa
    (coluna UNIQUE) e tentamos o seguinte.
    """
    for tentativa in range(tentativas):
        produto.sku = gerar_sku(produto.categoria, produto.franquia, produto.marca)
        try:
            with transaction.atomic():
                produto.save()
            return
        except IntegrityError:
            if tentativa == tentativas - 1:
                raise

@login_required
def anuncio_criar(request):
    form = ProdutoForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            produto = form.save(commit=False)
            produto.vendedor = request.user
            gerado = not produto.sku
            if gerado:
                _salvar_com_sku_gerado(produto)
            else:
                produto.save()
            _salvar_imagens(produto, form.cleaned_data["imagens"])
        aviso = f" Código gerado: {produto.sku}." if gerado else ""
        messages.success(request, f'Anúncio "{produto.nome}" publicado.{aviso}')
        return redirect("anuncio_detalhe", produto_id=produto.id)

    return render(request, "anuncios/form.html", {
        "form": form,
        "titulo": "Criar anúncio",
        "limite_imagens": LIMITE_IMAGENS_ANUNCIO,
        "breadcrumbs": _breadcrumbs({"label": "Criar anúncio", "url": None}),
    })


@login_required
def anuncio_editar(request, produto_id):
    produto = _meu_anuncio(request, produto_id)
    imagens = list(produto.imagens.order_by("ordem_exibicao"))

    remover_ids = set()
    if request.method == "POST":
        remover_ids = {int(i) for i in request.POST.getlist("remover_imagens") if i.isdigit()}

    form = ProdutoForm(
        request.POST or None, request.FILES or None, instance=produto,
        imagens_existentes=len([img for img in imagens if img.id not in remover_ids]),
    )

    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            produto = form.save()
            if remover_ids:
                produto.imagens.filter(id__in=remover_ids).delete()

            principal_id = request.POST.get("imagem_principal", "")
            if principal_id.isdigit() and int(principal_id) not in remover_ids:
                imagem = produto.imagens.filter(pk=int(principal_id)).first()
                if imagem and not imagem.principal:
                    imagem.principal = True
                    imagem.save()  # o save() do model desmarca as outras

            _salvar_imagens(produto, form.cleaned_data["imagens"])

            # Se a principal foi removida, promove a primeira restante.
            if not produto.imagens.filter(principal=True).exists():
                primeira = produto.imagens.order_by("ordem_exibicao").first()
                if primeira:
                    primeira.principal = True
                    primeira.save()

        messages.success(request, "Anúncio atualizado.")
        return redirect("anuncio_detalhe", produto_id=produto.id)

    return render(request, "anuncios/form.html", {
        "form": form,
        "produto": produto,
        "imagens": imagens,
        "titulo": "Editar anúncio",
        "limite_imagens": LIMITE_IMAGENS_ANUNCIO,
        "breadcrumbs": _breadcrumbs(
            {"label": produto.nome, "url": reverse("anuncio_detalhe", args=[produto.id])},
            {"label": "Editar", "url": None},
        ),
    })


# =====================================================================
# VISUALIZAR
# =====================================================================

@login_required
def anuncio_detalhe(request, produto_id):
    produto = get_object_or_404(
        Produto.objects.select_related("categoria", "franquia").prefetch_related("imagens"),
        pk=produto_id, vendedor=request.user,
    )

    vendas = (
        ItemPedido.objects
        .filter(produto=produto)
        .exclude(pedido__status_pedido="cancelado")
        .select_related("pedido")
        .order_by("-pedido__data_criacao")
    )
    totais = vendas.aggregate(unidades=Sum("quantidade"), receita=Sum("subtotal"))

    return render(request, "anuncios/detalhe.html", {
        "produto": produto,
        "imagens": produto.imagens.all(),
        "vendas_recentes": vendas[:10],
        "unidades_vendidas": totais["unidades"] or 0,
        "receita": totais["receita"] or 0,
        "em_carrinhos": produto.itens_carrinho.filter(carrinho__status="ativo").count(),
        "media_avaliacoes": produto.avaliacoes.filter(status="publicada").aggregate(m=Avg("nota"))["m"],
        "total_avaliacoes": produto.avaliacoes.filter(status="publicada").count(),
        "breadcrumbs": _breadcrumbs({"label": produto.nome, "url": None}),
    })


# =====================================================================
# STATUS / EXCLUSÃO
# =====================================================================

@login_required
@require_POST
def anuncio_status(request, produto_id):
    produto = _meu_anuncio(request, produto_id)
    acao = request.POST.get("acao")

    if acao == "ativar":
        if produto.quantidade_disponivel == 0:
            messages.error(request, "Adicione estoque antes de reativar o anúncio.")
            return redirect("anuncio_editar", produto_id=produto.id)
        produto.status_anuncio = "ativo"
        texto = "Anúncio reativado."
    elif acao == "pausar":
        produto.status_anuncio = "pausado"
        texto = "Anúncio pausado. Ele não aparece mais na loja."
    elif acao == "encerrar":
        produto.status_anuncio = "encerrado"
        texto = "Anúncio encerrado."
    else:
        messages.error(request, "Ação inválida.")
        return redirect("anuncios")

    produto.save(update_fields=["status_anuncio", "data_atualizacao"])
    messages.success(request, texto)
    return redirect(_proximo(request, "anuncios"))


@login_required
@require_POST
def anuncio_excluir(request, produto_id):
    produto = _meu_anuncio(request, produto_id)
    if produto.itens_pedido.exists():
        messages.error(
            request,
            "Este anúncio já tem vendas e não pode ser excluído (o histórico dos pedidos precisa ser mantido). "
            "Use “Encerrar” no lugar.",
        )
        return redirect("anuncio_detalhe", produto_id=produto.id)

    nome = produto.nome
    produto.delete()
    messages.success(request, f'Anúncio "{nome}" excluído.')
    return redirect("anuncios")


# =====================================================================
# ESTOQUE EM LOTE
# =====================================================================

@login_required
def estoque(request):
    produtos = (
        Produto.objects
        .filter(vendedor=request.user)
        .exclude(status_anuncio="encerrado")
        .select_related("categoria")
        .prefetch_related("imagens")
        .order_by("quantidade_disponivel", "nome")
    )

    if request.method == "POST":
        erros, alterados = [], 0
        with transaction.atomic():
            for produto in produtos:
                bruto = request.POST.get(f"estoque_{produto.id}")
                if bruto is None or bruto.strip() == str(produto.quantidade_disponivel):
                    continue
                try:
                    novo = int(bruto)
                    if novo < 0:
                        raise ValueError
                except ValueError:
                    erros.append(produto.nome)
                    continue

                produto.quantidade_disponivel = novo
                campos = ["quantidade_disponivel", "data_atualizacao"]
                if produto.status_anuncio == "vendido" and novo > 0:
                    produto.status_anuncio = "ativo"
                    campos.append("status_anuncio")
                elif produto.status_anuncio == "ativo" and novo == 0:
                    produto.status_anuncio = "vendido"
                    campos.append("status_anuncio")
                produto.save(update_fields=campos)
                alterados += 1

        if erros:
            messages.error(request, "Quantidade inválida em: " + ", ".join(erros) + ".")
        if alterados:
            messages.success(request, f"Estoque atualizado em {alterados} anúncio(s).")
        elif not erros:
            messages.info(request, "Nenhuma quantidade foi alterada.")
        return redirect("estoque")

    return render(request, "anuncios/estoque.html", {
        "produtos": produtos,
        "breadcrumbs": _breadcrumbs({"label": "Gerenciar estoque", "url": None}),
    })
