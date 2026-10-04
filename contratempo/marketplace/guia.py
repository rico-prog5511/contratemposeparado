"""
marketplace/guia.py

Artigos do "Guia do colecionador". Não ficam no banco: cada artigo é um
item desta lista + um template com o texto em
templates/guia/textos/<slug>.html.

Para criar um artigo novo: adicione um item aqui e crie o template com o
mesmo slug. A ordem da lista é a ordem de exibição (os 3 primeiros
aparecem na home).
"""

ARTIGOS = [
    {
        "slug": "carta-original",
        "titulo": "Como saber se uma carta é original",
        "resumo": "Textura, impressão, brilho e verso: o que conferir antes de comprar uma carta colecionável.",
        "assunto": "Autenticidade",
        "minutos": 4,
    },
    {
        "slug": "condicao-das-pecas",
        "titulo": "Novo, semi-novo ou usado?",
        "resumo": "O que cada condição significa na Contratempo e como descrever o estado da sua peça.",
        "assunto": "Anúncios",
        "minutos": 3,
    },
    {
        "slug": "como-embalar",
        "titulo": "Como embalar uma peça para envio",
        "resumo": "Cartas, bonecos, discos e caixas originais: como fazer a peça chegar do jeito que saiu.",
        "assunto": "Envio",
        "minutos": 4,
    },
    {
        "slug": "conservar-colecao",
        "titulo": "Como conservar sua coleção",
        "resumo": "Luz, umidade, poeira e manuseio: os cuidados que mantêm o valor das peças por anos.",
        "assunto": "Cuidados",
        "minutos": 3,
    },
]

POR_SLUG = {artigo["slug"]: artigo for artigo in ARTIGOS}
