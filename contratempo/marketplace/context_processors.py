"""
marketplace/context_processors.py

Registrados em settings.py -> TEMPLATES -> OPTIONS -> context_processors.
Assim `categorias_menu` e `carrinho_total_itens` ficam disponíveis em
QUALQUER template, sem precisar passar pelo contexto de cada view —
necessário porque o header (submenu de categorias e contador do
carrinho) é incluído em todas as páginas via base.html.
"""

from django.db.models import Sum

from .models import Categoria, ItemCarrinho


def menu_categorias(request):
    return {
        "categorias_menu": Categoria.objects.filter(ativo=True).order_by("nome")
    }


def carrinho_resumo(request):
    """Quantidade total de itens no carrinho ativo (badge do header)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"carrinho_total_itens": 0}

    total = (
        ItemCarrinho.objects
        .filter(carrinho__usuario=user, carrinho__status="ativo")
        .aggregate(total=Sum("quantidade"))["total"]
    )
    return {"carrinho_total_itens": total or 0}
