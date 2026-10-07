from django.db.models import Sum

from .models import Categoria, ItemCarrinho


def menu_categorias(request):
    return {
        "categorias_menu": Categoria.objects.filter(ativo=True).order_by("nome")
    }


def carrinho_resumo(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {"carrinho_total_itens": 0}

    total = (
        ItemCarrinho.objects
        .filter(carrinho__usuario=user, carrinho__status="ativo")
        .aggregate(total=Sum("quantidade"))["total"]
    )
    return {"carrinho_total_itens": total or 0}
