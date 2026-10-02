"""
marketplace/admin.py

Painel administrativo completo do Contratempo. Não há registro de
Favorito — a funcionalidade foi removida do projeto.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.template.response import TemplateResponse
from django.templatetags.static import static
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html

from .relatorios import anos_disponiveis, relatorio_anual
from .templatetags.marketplace_extras import brl, imagem_principal
from .models import (
    Avaliacao,
    Carrinho,
    Categoria,
    Contato,
    Denuncia,
    Endereco,
    FormaPagamento,
    Franquia,
    ItemCarrinho,
    ItemPedido,
    Pedido,
    PerguntaFrequente,
    PerguntaProduto,
    Produto,
    ProdutoImagem,
    TabelaFrete,
    Usuario,
)


# =====================================================================
# APARÊNCIA GERAL (o tema visual fica em static/css/admin.css)
# =====================================================================

admin.site.site_header = "Contratempo"
admin.site.site_title = "Contratempo — painel"
admin.site.index_title = "Painel de controle"
admin.site.empty_value_display = "—"

# Tom do selo de cada status. O texto do status sempre aparece junto,
# então a informação não depende só da cor (acessibilidade).
TOM_STATUS = {
    # positivos / em andamento normal
    "ativo": "azul", "publicada": "azul", "entregue": "azul", "respondido": "azul",
    "pagamento_aprovado": "azul", "processamento": "azul", "enviado": "azul",
    "finalizado": "azul", "improcedente": "cinza",
    # pedem atenção
    "pendente": "alerta", "aguardando_pagamento": "alerta", "inativo": "cinza",
    # pausados / arquivados
    "pausado": "cinza", "oculta": "cinza", "arquivado": "cinza", "abandonado": "cinza", "vendido": "lilas",
    # negativos
    "encerrado": "vermelho", "cancelado": "vermelho", "removida": "vermelho",
    "suspenso": "vermelho", "procedente": "vermelho",
}


def selo(valor, rotulo):
    return format_html('<span class="ct-selo ct-selo--{}">{}</span>', TOM_STATUS.get(valor, "cinza"), rotulo)


def miniatura(url, texto_alt=""):
    return format_html(
        '<img src="{}" alt="{}" class="ct-miniatura" loading="lazy" width="48" height="48">',
        url or static("img/produto-sem-imagem.svg"), texto_alt,
    )


# =====================================================================
# FRETE, FAQ E PERGUNTAS
# =====================================================================

@admin.register(TabelaFrete)
class TabelaFreteAdmin(admin.ModelAdmin):
    list_display = ("uf", "regiao", "valor", "prazo_dias", "ativo")
    list_filter = ("regiao", "ativo")
    list_editable = ("valor", "prazo_dias", "ativo")
    search_fields = ("uf",)


@admin.register(PerguntaFrequente)
class PerguntaFrequenteAdmin(admin.ModelAdmin):
    list_display = ("pergunta", "tema", "ordem", "ativo")
    list_filter = ("tema", "ativo")
    list_editable = ("ordem", "ativo")
    search_fields = ("pergunta", "resposta")


@admin.register(Denuncia)
class DenunciaAdmin(admin.ModelAdmin):
    list_display = ("produto", "motivo", "situacao", "vendedor", "status_anuncio", "data_denuncia")
    list_filter = ("status", "motivo", "data_denuncia")
    list_select_related = ("produto", "produto__vendedor")
    search_fields = ("produto__nome", "descricao", "usuario__email", "produto__vendedor__email")
    autocomplete_fields = ("produto", "usuario")
    readonly_fields = ("data_denuncia", "data_analise")
    actions = ("marcar_procedente", "marcar_improcedente")

    @admin.display(description="Situação", ordering="status")
    def situacao(self, obj):
        return selo(obj.status, obj.get_status_display())

    @admin.display(description="Vendedor")
    def vendedor(self, obj):
        return obj.produto.vendedor

    @admin.display(description="Anúncio")
    def status_anuncio(self, obj):
        return selo(obj.produto.status_anuncio, obj.produto.get_status_anuncio_display())

    @admin.action(description="Procedente: encerrar o anúncio")
    def marcar_procedente(self, request, queryset):
        agora = timezone.now()
        # IDs em listas: o MySQL não aceita subconsulta na própria tabela
        # que está sendo atualizada (erro 1093).
        ids_denuncias = list(queryset.values_list("id", flat=True))
        ids_produtos = list(queryset.values_list("produto_id", flat=True).distinct())
        total_produtos = Produto.objects.filter(pk__in=ids_produtos).update(status_anuncio="encerrado")
        # Todas as denúncias pendentes desses anúncios ficam resolvidas.
        Denuncia.objects.filter(
            Q(pk__in=ids_denuncias) | Q(produto_id__in=ids_produtos, status="pendente")
        ).update(status="procedente", data_analise=agora)
        self.message_user(request, f"{total_produtos} anúncio(s) encerrado(s).", messages.SUCCESS)

    @admin.action(description="Improcedente: manter o anúncio")
    def marcar_improcedente(self, request, queryset):
        ids = list(queryset.values_list("id", flat=True))
        total = Denuncia.objects.filter(pk__in=ids).update(status="improcedente", data_analise=timezone.now())
        self.message_user(request, f"{total} denúncia(s) arquivada(s).", messages.SUCCESS)


@admin.register(PerguntaProduto)
class PerguntaProdutoAdmin(admin.ModelAdmin):
    list_display = ("produto", "usuario", "respondida", "status", "data_pergunta")
    list_filter = ("status",)
    list_editable = ("status",)
    search_fields = ("pergunta", "resposta", "produto__nome", "usuario__email")
    autocomplete_fields = ("produto", "usuario")
    readonly_fields = ("data_pergunta", "data_resposta")

    @admin.display(boolean=True, description="Respondida")
    def respondida(self, obj):
        return obj.resposta is not None


# =====================================================================
# USUÁRIO
# =====================================================================

@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    # UserAdmin.fieldsets/add_fieldsets assumem "username" e
    # "date_joined"; como o Usuario usa email + data_cadastro,
    # sobrescrevemos ambos.
    model = Usuario
    ordering = ["-data_cadastro"]
    list_display = (
        "email",
        "nome_completo",
        "situacao",
        "email_confirmado",
        "is_active",
        "is_staff",
        "data_cadastro",
    )
    list_filter = ("status_conta", "email_confirmado", "is_active", "is_staff")
    search_fields = ("email", "nome_completo", "telefone")
    readonly_fields = ("data_cadastro", "data_atualizacao", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Dados pessoais", {
            "fields": ("nome_completo", "data_nascimento", "telefone", "avatar")
        }),
        ("Status", {"fields": ("status_conta", "email_confirmado", "is_active", "is_staff", "is_superuser")}),
        ("Permissões", {"fields": ("groups", "user_permissions")}),
        ("Datas", {"fields": ("data_cadastro", "data_atualizacao", "last_login")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "nome_completo", "password1", "password2"),
        }),
    )

    @admin.display(description="Conta", ordering="status_conta")
    def situacao(self, obj):
        return selo(obj.status_conta, obj.get_status_conta_display())

    def view_on_site(self, obj):
        return reverse("vendedor_perfil", args=[obj.pk])


# =====================================================================
# ENDEREÇOS E PAGAMENTO
# =====================================================================

@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ("nome_endereco", "usuario", "cidade", "estado", "endereco_principal")
    list_filter = ("estado", "endereco_principal")
    search_fields = ("usuario__email", "cidade", "cep", "logradouro")
    autocomplete_fields = ("usuario",)


@admin.register(FormaPagamento)
class FormaPagamentoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "tipo", "apelido", "ultimos_digitos", "principal")
    list_filter = ("tipo", "principal")
    search_fields = ("usuario__email", "apelido")
    autocomplete_fields = ("usuario",)


# =====================================================================
# CATEGORIAS E FRANQUIAS
# =====================================================================

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}
    list_editable = ("ativo",)


@admin.register(Franquia)
class FranquiaAdmin(admin.ModelAdmin):
    list_display = ("nome", "slug", "ativo")
    list_filter = ("ativo",)
    search_fields = ("nome", "slug")
    prepopulated_fields = {"slug": ("nome",)}
    list_editable = ("ativo",)


# =====================================================================
# PRODUTOS
# =====================================================================

class ProdutoImagemInline(admin.TabularInline):
    model = ProdutoImagem
    extra = 1
    fields = ("previa", "url_imagem", "principal", "ordem_exibicao")
    readonly_fields = ("previa",)

    @admin.display(description="Foto")
    def previa(self, obj):
        return miniatura(obj.url_imagem) if obj.pk else "—"


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "foto", "nome", "vendedor_nome", "categoria",
        "preco_brl", "quantidade_disponivel", "situacao",
    )
    list_display_links = ("foto", "nome")
    list_filter = ("status_anuncio", "condicao", "categoria", "franquia", "data_criacao")
    list_select_related = ("vendedor", "categoria")
    search_fields = ("nome", "sku", "vendedor__email")
    autocomplete_fields = ("vendedor", "categoria", "franquia")
    readonly_fields = ("data_criacao", "data_atualizacao")
    list_editable = ("quantidade_disponivel",)
    inlines = [ProdutoImagemInline]
    fieldsets = (
        ("Anúncio", {"fields": ("vendedor", "categoria", "franquia", "nome", "descricao")}),
        ("Preço e estoque", {
            "fields": ("preco", "quantidade_disponivel", "condicao", "marca", "ano", "sku", "status_anuncio")
        }),
        ("Datas", {"fields": ("data_criacao", "data_atualizacao"), "classes": ("collapse",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("imagens")

    @admin.display(description="Foto")
    def foto(self, obj):
        return miniatura(imagem_principal(obj), obj.nome)

    @admin.display(description="Preço", ordering="preco")
    def preco_brl(self, obj):
        return brl(obj.preco)

    @admin.display(description="Vendedor", ordering="vendedor__nome_completo")
    def vendedor_nome(self, obj):
        return obj.vendedor.nome_completo

    @admin.display(description="Status", ordering="status_anuncio")
    def situacao(self, obj):
        return selo(obj.status_anuncio, obj.get_status_anuncio_display())

    def view_on_site(self, obj):
        return reverse("produto_detalhe", args=[obj.pk])


# =====================================================================
# CARRINHO
# =====================================================================

class ItemCarrinhoInline(admin.TabularInline):
    model = ItemCarrinho
    extra = 0
    autocomplete_fields = ("produto",)
    readonly_fields = ("data_adicionado",)


@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    list_display = ("id", "usuario", "situacao", "data_criacao", "data_atualizacao")
    list_filter = ("status",)
    search_fields = ("usuario__email",)
    autocomplete_fields = ("usuario",)
    inlines = [ItemCarrinhoInline]

    @admin.display(description="Status", ordering="status")
    def situacao(self, obj):
        return selo(obj.status, obj.get_status_display())


# =====================================================================
# PEDIDOS
# =====================================================================

class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    readonly_fields = ("produto", "nome_produto", "preco_unitario", "quantidade", "subtotal")
    can_delete = False

    def has_add_permission(self, request, obj=None):
        # Itens de pedido só devem ser criados pelo fluxo de checkout,
        # nunca manualmente pelo Admin.
        return False


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("numero", "usuario", "vendedor", "status_pedido", "total_brl", "frete_brl", "data_criacao")
    list_display_links = ("numero",)
    list_filter = ("status_pedido", "data_criacao")
    list_select_related = ("usuario", "vendedor")
    search_fields = ("usuario__email", "vendedor__email", "id", "codigo_rastreio")
    autocomplete_fields = ("usuario", "vendedor", "endereco", "forma_pagamento")
    readonly_fields = (
        "endereco_snapshot", "forma_pagamento_snapshot",
        "valor_total", "valor_frete", "prazo_entrega_dias",
        "data_envio", "data_criacao", "data_atualizacao",
    )
    list_editable = ("status_pedido",)
    inlines = [ItemPedidoInline]
    fieldsets = (
        ("Pedido", {"fields": ("usuario", "vendedor", "status_pedido", "codigo_rastreio", "data_envio")}),
        ("Valores", {"fields": ("valor_total", "valor_frete", "prazo_entrega_dias")}),
        ("Entrega e pagamento", {
            "fields": ("endereco", "endereco_snapshot", "forma_pagamento", "forma_pagamento_snapshot"),
        }),
        ("Datas", {"fields": ("data_criacao", "data_atualizacao"), "classes": ("collapse",)}),
    )

    # Lista de pedidos com o botão "Relatório anual" no topo
    change_list_template = "admin/marketplace/pedido/change_list.html"

    def get_urls(self):
        rota = path(
            "relatorio-anual/",
            self.admin_site.admin_view(self.relatorio_anual_view),
            name="marketplace_pedido_relatorio",
        )
        return [rota] + super().get_urls()

    def relatorio_anual_view(self, request):
        """Página "Relatório do ano" (/admin/marketplace/pedido/relatorio-anual/)."""
        if not self.has_view_permission(request):
            raise PermissionDenied
        anos = anos_disponiveis()
        try:
            ano = int(request.GET.get("ano", anos[0]))
        except ValueError:
            ano = anos[0]
        if ano not in anos:
            ano = anos[0]
        return TemplateResponse(request, "admin/relatorio_anual.html", {
            **self.admin_site.each_context(request),
            "title": f"Relatório de {ano}",
            "opts": self.model._meta,
            "anos": anos,
            **relatorio_anual(ano),
        })

    @admin.display(description="Pedido", ordering="id")
    def numero(self, obj):
        return f"#{obj.id}"

    @admin.display(description="Total", ordering="valor_total")
    def total_brl(self, obj):
        return brl(obj.valor_total)

    @admin.display(description="Frete", ordering="valor_frete")
    def frete_brl(self, obj):
        return brl(obj.valor_frete)


# =====================================================================
# CONTATO
# =====================================================================

@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ("assunto", "nome", "email", "status", "data_envio")
    list_filter = ("status", "data_envio")
    search_fields = ("nome", "email", "assunto", "mensagem")
    readonly_fields = ("nome", "email", "assunto", "mensagem", "usuario", "data_envio")
    list_editable = ("status",)


# =====================================================================
# AVALIAÇÕES
# =====================================================================

@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("produto", "usuario", "estrelas", "situacao", "data_avaliacao")
    list_filter = ("status", "nota", "data_avaliacao")
    list_select_related = ("produto", "usuario")
    search_fields = ("produto__nome", "usuario__email")
    autocomplete_fields = ("usuario", "produto", "pedido")
    readonly_fields = ("data_avaliacao",)

    @admin.display(description="Nota", ordering="nota")
    def estrelas(self, obj):
        return format_html(
            '<span class="ct-estrelas" aria-label="{} de 5">{}<span class="ct-estrelas-vazias">{}</span></span>',
            obj.nota, "★" * obj.nota, "★" * (5 - obj.nota),
        )

    @admin.display(description="Status", ordering="status")
    def situacao(self, obj):
        return selo(obj.status, obj.get_status_display())