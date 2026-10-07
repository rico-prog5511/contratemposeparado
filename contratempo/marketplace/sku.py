import re

from .busca import normalizar

PADRAO = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}$")
EXEMPLO = "COL-NAR-001"
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalizar_sku(texto):
    texto = normalizar(texto or "").upper().strip()
    texto = re.sub(r"[\s_./]+", "-", texto)
    return re.sub(r"-{2,}", "-", texto).strip("-")


def _tres(texto, padrao="GEN"):
    limpo = re.sub(r"[^A-Z0-9]", "", normalizar(texto or "").upper())
    if not limpo:
        return padrao
    return limpo[:3].ljust(3, "X")


def _sufixo(numero):
    if numero <= 999:
        return f"{numero:03d}"
    resto, saida = numero, ""
    for _ in range(3):
        resto, digito = divmod(resto, 36)
        saida = _BASE36[digito] + saida
    return saida


def gerar_sku(categoria, franquia=None, marca=""):
    from .models import Produto

    prefixo = f"{_tres(categoria.nome)}-{_tres(franquia.nome if franquia else marca)}-"
    usados = set(Produto.objects.filter(sku__startswith=prefixo).values_list("sku", flat=True))
    numero = 1
    while f"{prefixo}{_sufixo(numero)}" in usados:
        numero += 1
    return f"{prefixo}{_sufixo(numero)}"
