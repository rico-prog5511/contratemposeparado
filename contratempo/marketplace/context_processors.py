from django.contrib.staticfiles import finders
from django.db.models import Sum
from django.templatetags.static import static

from .models import Categoria, ItemCarrinho

ARQUIVOS_FONTE_LOGO = (
    ("fonts/adult-swim.woff2", "woff2"),
    ("fonts/adult-swim.woff", "woff"),
    ("fonts/adult-swim.ttf", "truetype"),
    ("fonts/adult-swim.otf", "opentype"),
)


def fonte_logo(request):
    return {"fonte_logo": [
        {"url": static(caminho), "formato": formato}
        for caminho, formato in ARQUIVOS_FONTE_LOGO if finders.find(caminho)
    ]}


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
