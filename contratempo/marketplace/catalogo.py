"""
marketplace/catalogo.py

Filtros, contagens e ordenação da página de produtos (views.produtos).

Cada filtro é uma "dimensão" (franquia, condição, marca, década...). Para
mostrar quantos produtos cada opção teria, a contagem de uma dimensão usa
TODOS os outros filtros ligados, menos ela mesma — assim marcar "Bandai"
não zera a contagem de "Hasbro", mas marcar "Novo" muda a contagem das
marcas. Opções que dariam zero produtos aparecem desabilitadas.

Tudo usa campos que já existem no banco (nada novo).
"""

from collections import Counter
from decimal import Decimal, InvalidOperation

from django.db.models import Avg, Count, F, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce

from .models import Avaliacao, Franquia, Produto

NOTA_BEM_AVALIADO = 4
DECADA_MINIMA = 1950  # anos anteriores entram numa opção só: "Antes de 1950"

ORDENACOES = {
    "recentes": "Mais recentes",
    "menor_preco": "Menor preço",
    "maior_preco": "Maior preço",
    "mais_vendidos": "Mais vendidos",
    "bem_avaliados": "Vendedores mais bem avaliados",
    "ano_antigo": "Ano (mais antigo primeiro)",
    "nome": "Nome (A–Z)",
}


# ----- Leitura dos filtros da URL -----

def _decimal(valor):
    try:
        numero = Decimal(str(valor).replace(",", "."))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return numero if numero >= 0 else None


def _inteiro(valor, minimo=1000, maximo=2100):
    return int(valor) if str(valor).isdigit() and minimo <= int(valor) <= maximo else None


def ler_filtros(get):
    """request.GET -> dicionário com os filtros válidos (o que for inválido é ignorado)."""
    decadas = sorted({int(d) for d in get.getlist("decada") if d.isdigit() and int(d) % 10 == 0 and 1800 <= int(d) <= 2100})
    return {
        "franquia": [s for s in get.getlist("franquia") if s],
        "condicao": [c for c in get.getlist("condicao") if c in dict(Produto.CONDICAO_CHOICES)],
        "marca": [m.strip() for m in get.getlist("marca") if m.strip()][:30],
        "decada": decadas,
        "ano_min": _inteiro(get.get("ano_min", "")),
        "ano_max": _inteiro(get.get("ano_max", "")),
        "preco_min": _decimal(get.get("preco_min")) if get.get("preco_min") else None,
        "preco_max": _decimal(get.get("preco_max")) if get.get("preco_max") else None,
        "unica": get.get("unica") == "1",
        "bem_avaliado": get.get("bem_avaliado") == "1",
    }


def vendedores_bem_avaliados():
    """Ids dos vendedores com nota média >= 4 (mesma regra da página do vendedor)."""
    return list(
        Avaliacao.objects.filter(status="publicada")
        .values("produto__vendedor")
        .annotate(media=Avg("nota"))
        .filter(media__gte=NOTA_BEM_AVALIADO)
        .values_list("produto__vendedor", flat=True)
    )


def _q_decadas(decadas):
    q = Q()
    for d in decadas:
        q |= Q(ano__lt=DECADA_MINIMA) if d < DECADA_MINIMA else Q(ano__gte=d, ano__lte=d + 9)
    return q


def aplicar(qs, f, exceto=None):
    """Aplica os filtros em `qs`, menos a dimensão `exceto` (usada nas contagens)."""
    if f["franquia"] and exceto != "franquia":
        qs = qs.filter(franquia__slug__in=f["franquia"])
    if f["condicao"] and exceto != "condicao":
        qs = qs.filter(condicao__in=f["condicao"])
    if f["marca"] and exceto != "marca":
        qs = qs.filter(marca__in=f["marca"])
    if f["decada"] and exceto != "decada":
        qs = qs.filter(_q_decadas(f["decada"]))
    if f["ano_min"] is not None:
        qs = qs.filter(ano__gte=f["ano_min"])
    if f["ano_max"] is not None:
        qs = qs.filter(ano__lte=f["ano_max"])
    if f["preco_min"] is not None:
        qs = qs.filter(preco__gte=f["preco_min"])
    if f["preco_max"] is not None:
        qs = qs.filter(preco__lte=f["preco_max"])
    if f["unica"] and exceto != "unica":
        qs = qs.filter(quantidade_disponivel=1)
    if f["bem_avaliado"] and exceto != "bem_avaliado":
        qs = qs.filter(vendedor_id__in=f["_bem_avaliados"])
    return qs


def ordenar(qs, chave):
    if chave == "menor_preco":
        return qs.order_by("preco", "-id")
    if chave == "maior_preco":
        return qs.order_by("-preco", "-id")
    if chave == "nome":
        return qs.order_by("nome", "-id")
    if chave == "ano_antigo":
        return qs.order_by(F("ano").asc(nulls_last=True), "-id")
    if chave == "mais_vendidos":
        return qs.annotate(total_vendido=Coalesce(
            Sum("itens_pedido__quantidade", filter=~Q(itens_pedido__pedido__status_pedido="cancelado")), 0,
        )).order_by("-total_vendido", "-data_criacao", "-id")
    if chave == "bem_avaliados":
        media_vendedor = (
            Avaliacao.objects.filter(status="publicada", produto__vendedor=OuterRef("vendedor"))
            .values("produto__vendedor").annotate(m=Avg("nota")).values("m")
        )
        return qs.annotate(nota_vendedor=Subquery(media_vendedor)).order_by(
            F("nota_vendedor").desc(nulls_last=True), "-data_criacao", "-id",
        )
    return qs.order_by("-data_criacao", "-id")


# ----- Opções com contagem -----

def _decada(ano):
    """1987 -> 1980. Tudo antes de 1950 vira uma opção só ("Antes de 1950", valor 1940)."""
    return ano // 10 * 10 if ano >= DECADA_MINIMA else DECADA_MINIMA - 10


def _rotulo_decada(d):
    if d < DECADA_MINIMA:
        return f"Antes de {DECADA_MINIMA}"
    return f"Anos {str(d)[2:]}" if d < 2000 else f"Anos {d}"


def opcoes(base, f):
    """Listas de opções de cada filtro, com contagem e marcação. `base` = busca + categoria + vendedor."""
    def lista(valores_contagens, selecionados, rotulos=None):
        return [
            {"valor": v, "rotulo": (rotulos or {}).get(v, v), "total": n, "marcado": v in selecionados}
            for v, n in valores_contagens
        ]

    # Franquias: todas as ativas aparecem, com a contagem atual.
    cont_franquia = dict(aplicar(base, f, "franquia").values_list("franquia__slug").annotate(n=Count("id")))
    franquias = [
        {"valor": fr.slug, "rotulo": fr.nome, "total": cont_franquia.get(fr.slug, 0), "marcado": fr.slug in f["franquia"]}
        for fr in Franquia.objects.filter(ativo=True).order_by("nome")
    ]

    cont_condicao = dict(aplicar(base, f, "condicao").values_list("condicao").annotate(n=Count("id")))
    condicoes = [
        {"valor": v, "rotulo": r, "total": cont_condicao.get(v, 0), "marcado": v in f["condicao"]}
        for v, r in Produto.CONDICAO_CHOICES
    ]

    # Marcas e décadas: a lista mostra TODAS as que existem nesta busca/categoria
    # (para não mudar de formato a cada clique); a contagem considera os outros
    # filtros, e as que dariam zero ficam desabilitadas.
    com_marca = base.exclude(marca__isnull=True).exclude(marca="")
    todas_marcas = set(com_marca.values_list("marca", flat=True).distinct()) | set(f["marca"])
    cont_marca = dict(aplicar(com_marca, f, "marca").values_list("marca").annotate(n=Count("id")))
    marcas = lista(
        sorted(((m, cont_marca.get(m, 0)) for m in todas_marcas), key=lambda par: (-par[1], par[0].lower())),
        f["marca"],
    )

    # Décadas: calculadas em Python a partir do ano (funciona igual no SQLite e no MySQL).
    com_ano = base.exclude(ano__isnull=True)
    todas_decadas = {_decada(ano) for ano in com_ano.values_list("ano", flat=True)} | set(f["decada"])
    cont_decada = Counter(_decada(ano) for ano in aplicar(com_ano, f, "decada").values_list("ano", flat=True))
    decadas = [
        {"valor": str(d), "rotulo": _rotulo_decada(d), "total": cont_decada.get(d, 0), "marcado": d in f["decada"]}
        for d in sorted(todas_decadas)
    ]

    extras = [
        {"nome": "unica", "rotulo": "Só peças únicas", "ajuda": "1 unidade disponível",
         "total": aplicar(base, f, "unica").filter(quantidade_disponivel=1).count(), "marcado": f["unica"]},
        {"nome": "bem_avaliado", "rotulo": "Vendedor bem avaliado", "ajuda": f"nota {NOTA_BEM_AVALIADO} ou mais",
         "total": aplicar(base, f, "bem_avaliado").filter(vendedor_id__in=f["_bem_avaliados"]).count(),
         "marcado": f["bem_avaliado"]},
    ]
    return {"franquias": franquias, "condicoes": condicoes, "marcas": marcas, "decadas": decadas, "extras": extras}


# ----- Etiquetas dos filtros ligados -----

def _sem(get, chave, valor=None):
    """Querystring sem um valor (ou sem a chave inteira) e sem a página."""
    copia = get.copy()
    copia.pop("page", None)
    if valor is None:
        copia.pop(chave, None)
    else:
        copia.setlist(chave, [v for v in copia.getlist(chave) if v != valor])
    return "?" + copia.urlencode()


def etiquetas(get, f, op):
    """[{rotulo, url}] — cada filtro ligado, com o link que o remove."""
    nomes_franquia = {o["valor"]: o["rotulo"] for o in op["franquias"]}
    nomes_condicao = dict(Produto.CONDICAO_CHOICES)
    lista = []
    for s in f["franquia"]:
        lista.append({"rotulo": nomes_franquia.get(s, s), "url": _sem(get, "franquia", s)})
    for c in f["condicao"]:
        lista.append({"rotulo": nomes_condicao[c], "url": _sem(get, "condicao", c)})
    for m in f["marca"]:
        lista.append({"rotulo": m, "url": _sem(get, "marca", m)})
    for d in f["decada"]:
        lista.append({"rotulo": _rotulo_decada(d), "url": _sem(get, "decada", str(d))})
    if f["ano_min"] is not None or f["ano_max"] is not None:
        de, ate = f["ano_min"], f["ano_max"]
        rotulo = f"Ano {de}–{ate}" if de and ate else (f"Ano a partir de {de}" if de else f"Ano até {ate}")
        copia = get.copy()
        for chave in ("ano_min", "ano_max", "page"):
            copia.pop(chave, None)
        lista.append({"rotulo": rotulo, "url": "?" + copia.urlencode()})
    if f["preco_min"] is not None or f["preco_max"] is not None:
        de, ate = f["preco_min"], f["preco_max"]
        brl = lambda v: f"R$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")  # noqa: E731
        rotulo = f"{brl(de)} a {brl(ate)}" if de is not None and ate is not None else (f"A partir de {brl(de)}" if de is not None else f"Até {brl(ate)}")
        copia = get.copy()
        for chave in ("preco_min", "preco_max", "page"):
            copia.pop(chave, None)
        lista.append({"rotulo": rotulo, "url": "?" + copia.urlencode()})
    if f["unica"]:
        lista.append({"rotulo": "Peça única", "url": _sem(get, "unica")})
    if f["bem_avaliado"]:
        lista.append({"rotulo": "Vendedor bem avaliado", "url": _sem(get, "bem_avaliado")})
    return lista


def total_ligados(f):
    return (len(f["franquia"]) + len(f["condicao"]) + len(f["marca"]) + len(f["decada"])
            + (f["ano_min"] is not None or f["ano_max"] is not None)
            + (f["preco_min"] is not None or f["preco_max"] is not None)
            + f["unica"] + f["bem_avaliado"])


def url_limpar(get):
    """Mantém busca, categoria, vendedor e ordenação; tira todos os filtros."""
    copia = get.copy()
    for chave in list(copia.keys()):
        if chave not in ("q", "categoria", "vendedor", "ordenar"):
            copia.pop(chave)
    return "?" + copia.urlencode()
