import re

from .busca import normalizar
from .models import Denuncia, Usuario

DENUNCIAS_PARA_PAUSAR = 3
ANUNCIOS_PROCEDENTES_PARA_SUSPENDER = 3

TERMOS_PROIBIDOS = {
    "conteúdo para maiores de 18 anos": [
        "porno", "pornos", "pornografia", "pornografias", "pornografico", "pornografica",
        "pornograficos", "pornograficas", "erotico", "erotica", "eroticos", "eroticas",
        "hentai", "ecchi", "nsfw", "playboy", "sexshop", "sex shop", "vibrador", "vibradores",
        "dildo", "dildos", "filme adulto", "filmes adultos", "conteudo adulto", "revista adulta",
        "revistas adultas", "brinquedo sexual", "brinquedos sexuais",
        "somente para adultos", "so para adultos", "apenas para adultos",
    ],
    "drogas": ["maconha", "cocaina", "haxixe", "cannabis", "lanca perfume"],
    "armas ou munição": ["arma de fogo", "armas de fogo", "municao", "municoes", "soco ingles"],
    "documentos ou dinheiro falsos": [
        "documento falso", "documentos falsos", "diploma falso", "diplomas falsos", "cnh falsa",
        "dinheiro falso", "nota falsa", "notas falsas",
    ],
    "cópias piratas": ["copia pirata", "copias piratas", "jogo pirata", "jogos piratas", "dvd pirata", "cd pirata"],
}

_MAIS_18 = re.compile(r"(?<![\d+])(\+\s?18|18\s?\+|maiores de 18)(?![\d+])")
_TROCAS = str.maketrans("013457@$", "oieastas")


def _simplificar(texto):
    trocado = normalizar(texto).translate(_TROCAS)
    return " " + " ".join(re.findall(r"[a-z]+", trocado)) + " "


def termo_proibido(texto):
    if not texto:
        return None
    if _MAIS_18.search(normalizar(texto)):
        return "+18", "conteúdo para maiores de 18 anos"
    simples = _simplificar(texto)
    for motivo, termos in TERMOS_PROIBIDOS.items():
        for termo in termos:
            if f" {termo} " in simples:
                return termo, motivo
    return None


def em_analise(produto):
    pendentes = produto.denuncias.filter(status="pendente")
    return pendentes.values("usuario").distinct().count() >= DENUNCIAS_PARA_PAUSAR


def retido_pela_moderacao(produto):
    return produto.denuncias.filter(status="procedente").exists() or em_analise(produto)


def pausar_se_atingiu_limite(produto):
    if produto.status_anuncio == "ativo" and em_analise(produto):
        produto.status_anuncio = "pausado"
        produto.save(update_fields=["status_anuncio", "data_atualizacao"])


def suspender_reincidentes(ids_vendedores):
    suspensos = 0
    vendedores = Usuario.objects.filter(pk__in=ids_vendedores, is_staff=False).exclude(status_conta="suspenso")
    for vendedor in vendedores:
        retirados = (
            Denuncia.objects
            .filter(status="procedente", produto__vendedor=vendedor)
            .values("produto").distinct().count()
        )
        if retirados >= ANUNCIOS_PROCEDENTES_PARA_SUSPENDER:
            vendedor.status_conta = "suspenso"
            vendedor.save(update_fields=["status_conta"])
            vendedor.produtos.filter(status_anuncio="ativo").update(status_anuncio="pausado")
            suspensos += 1
    return suspensos
