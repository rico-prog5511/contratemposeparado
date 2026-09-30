"""
marketplace/frete.py

Cálculo de frete por UF de destino (tabela TabelaFrete, editável no admin).

Regra: cada vendedor envia seu próprio pacote, então o comprador paga
UM frete por vendedor, com o valor e o prazo da UF de entrega.
"""

from collections import OrderedDict
from decimal import Decimal

from .models import TabelaFrete

# Faixas de CEP dos Correios (5 primeiros dígitos) -> UF.
# Usado na calculadora da página de produto, onde o visitante só
# informa o CEP. No checkout usamos direto o campo `estado` do endereço.
FAIXAS_CEP = [
    (1000, 19999, "SP"), (20000, 28999, "RJ"), (29000, 29999, "ES"),
    (30000, 39999, "MG"), (40000, 48999, "BA"), (49000, 49999, "SE"),
    (50000, 56999, "PE"), (57000, 57999, "AL"), (58000, 58999, "PB"),
    (59000, 59999, "RN"), (60000, 63999, "CE"), (64000, 64999, "PI"),
    (65000, 65999, "MA"), (66000, 68899, "PA"), (68900, 68999, "AP"),
    (69000, 69299, "AM"), (69300, 69399, "RR"), (69400, 69899, "AM"),
    (69900, 69999, "AC"), (70000, 72799, "DF"), (72800, 72999, "GO"),
    (73000, 73699, "DF"), (73700, 76799, "GO"), (76800, 76999, "RO"),
    (77000, 77999, "TO"), (78000, 78899, "MT"), (79000, 79999, "MS"),
    (80000, 87999, "PR"), (88000, 89999, "SC"), (90000, 99999, "RS"),
]


def limpar_cep(cep):
    return "".join(c for c in (cep or "") if c.isdigit())


def uf_por_cep(cep):
    """Devolve a UF de um CEP (8 dígitos) ou None se for inválido."""
    digitos = limpar_cep(cep)
    if len(digitos) != 8:
        return None
    prefixo = int(digitos[:5])
    for inicio, fim, uf in FAIXAS_CEP:
        if inicio <= prefixo <= fim:
            return uf
    return None


def faixa_para_uf(uf):
    """TabelaFrete ativa da UF, ou None se a UF não é atendida."""
    if not uf:
        return None
    return TabelaFrete.objects.filter(uf=uf.upper(), ativo=True).first()


def agrupar_por_vendedor(itens):
    """
    Agrupa itens do carrinho por vendedor, na ordem em que aparecem.
    Devolve uma lista de dicts: {vendedor, itens, subtotal}.
    """
    grupos = OrderedDict()
    for item in itens:
        vendedor = item.produto.vendedor
        grupo = grupos.setdefault(vendedor.id, {"vendedor": vendedor, "itens": [], "subtotal": Decimal("0")})
        grupo["itens"].append(item)
        grupo["subtotal"] += item.subtotal
    return list(grupos.values())


def calcular_envios(itens, uf):
    """
    Monta os envios (um por vendedor) com frete e prazo para a UF.
    Devolve (envios, faixa). Se a UF não for atendida, faixa é None e o
    frete de cada envio fica None.
    """
    faixa = faixa_para_uf(uf)
    envios = agrupar_por_vendedor(itens)
    for envio in envios:
        envio["frete"] = faixa.valor if faixa else None
        envio["prazo_dias"] = faixa.prazo_dias if faixa else None
        envio["total"] = envio["subtotal"] + (faixa.valor if faixa else 0)
    return envios, faixa


def resumo_envios(envios):
    subtotal = sum((e["subtotal"] for e in envios), Decimal("0"))
    frete = sum((e["frete"] or Decimal("0") for e in envios), Decimal("0"))
    return {"subtotal": subtotal, "frete": frete, "total": subtotal + frete}
