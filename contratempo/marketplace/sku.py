"""
marketplace/sku.py

Padrão do código SKU dos anúncios: três partes de 3 letras ou números,
separadas por hífen — ex.: COL-NAR-001.

- O vendedor pode escrever o próprio código: o formulário converte para
  maiúsculas, troca espaços por hífen e confere o formato (forms.py).
- Se deixar em branco ao CRIAR o anúncio, o site gera um (views_anuncios):
      1ª parte: categoria  (Colecionáveis -> COL)
      2ª parte: franquia, ou a marca/autor, ou GEN se não houver
      3ª parte: o próximo número livre (001, 002...)
- Anúncios antigos ficam como estão (o código antigo, mesmo fora do
  padrão, continua aceito enquanto não for alterado).

O banco exige SKU único no site inteiro (coluna UNIQUE), então o número
é o próximo livre entre os anúncios de TODOS os vendedores com o mesmo
começo.
"""

import re

from .busca import normalizar

PADRAO = re.compile(r"^[A-Z0-9]{3}-[A-Z0-9]{3}-[A-Z0-9]{3}$")
EXEMPLO = "COL-NAR-001"
_BASE36 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def normalizar_sku(texto):
    """' col nar_001 ' -> 'COL-NAR-001' (sem acento, maiúsculas, hífen no lugar de espaço/_/.)"""
    texto = normalizar(texto or "").upper().strip()
    texto = re.sub(r"[\s_./]+", "-", texto)
    return re.sub(r"-{2,}", "-", texto).strip("-")


def _tres(texto, padrao="GEN"):
    """As 3 primeiras letras/números de um nome. 'Star Wars' -> 'STA'; 'TV' -> 'TVX'."""
    limpo = re.sub(r"[^A-Z0-9]", "", normalizar(texto or "").upper())
    if not limpo:
        return padrao
    return limpo[:3].ljust(3, "X")


def _sufixo(numero):
    """1 -> '001' ... 999 -> '999'; depois segue em letras e números (3 caracteres)."""
    if numero <= 999:
        return f"{numero:03d}"
    resto, saida = numero, ""
    for _ in range(3):
        resto, digito = divmod(resto, 36)
        saida = _BASE36[digito] + saida
    return saida


def gerar_sku(categoria, franquia=None, marca=""):
    """Próximo código livre no site para esta categoria + franquia/marca."""
    from .models import Produto

    prefixo = f"{_tres(categoria.nome)}-{_tres(franquia.nome if franquia else marca)}-"
    usados = set(Produto.objects.filter(sku__startswith=prefixo).values_list("sku", flat=True))
    numero = 1
    while f"{prefixo}{_sufixo(numero)}" in usados:
        numero += 1
    return f"{prefixo}{_sufixo(numero)}"
