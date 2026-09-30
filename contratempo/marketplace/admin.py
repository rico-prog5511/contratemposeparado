"""
marketplace/admin.py

Painel administrativo completo do Contratempo. Não há registro de
Favorito — a funcionalidade foi removida do projeto.
"""

from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.db.models import Q
from django.utils import timezone

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
    list_display = ("produto", "motivo", "status", "vendedor", "status_anuncio", "data_denuncia")
    list_filter = ("status", "motivo")
    search_fields = ("produto__nome", "descricao", "usuario__email", "produto__vendedor__email")
    autocomplete_fields = ("produto", "usuario")
    readonly_fields = ("data_denuncia", "data_analise")
    actions = ("marcar_procedente", "marcar_improcedente")

    @admin.display(description="Vendedor")
    def vendedor(self, obj):
        return obj.produto.vendedor

    @admin.display(description="Anúncio")
    def status_anuncio(self, obj):
        return obj.produto.get_status_anuncio_display()

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
        "status_conta",
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
    fields = ("url_imagem", "principal", "ordem_exibicao")


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = (
        "nome", "vendedor", "categoria", "franquia",
        "preco", "quantidade_disponivel", "status_anuncio",
    )
    list_filter = ("status_anuncio", "condicao", "categoria", "franquia")
    search_fields = ("nome", "sku", "vendedor__email")
    autocomplete_fields = ("vendedor", "categoria", "franquia")
    readonly_fields = ("data_criacao", "data_atualizacao")
    list_editable = ("quantidade_disponivel",)
    inlines = [ProdutoImagemInline]
    fieldsets = (
        (None, {"fields": ("vendedor", "categoria", "franquia", "nome", "descricao")}),
        ("Comercial", {
            "fields": ("preco", "quantidade_disponivel", "condicao", "marca", "ano", "sku", "status_anuncio")
        }),
        ("Datas", {"fields": ("data_criacao", "data_atualizacao")}),
    )


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
    list_display = ("id", "usuario", "status", "data_criacao", "data_atualizacao")
    list_filter = ("status",)
    search_fields = ("usuario__email",)
    autocomplete_fields = ("usuario",)
    inlines = [ItemCarrinhoInline]


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
    list_display = ("id", "usuario", "vendedor", "status_pedido", "valor_total", "valor_frete", "data_criacao")
    list_filter = ("status_pedido",)
    search_fields = ("usuario__email", "vendedor__email", "id", "codigo_rastreio")
    autocomplete_fields = ("usuario", "vendedor", "endereco", "forma_pagamento")
    readonly_fields = (
        "endereco_snapshot", "forma_pagamento_snapshot",
        "valor_total", "valor_frete", "prazo_entrega_dias",
        "data_envio", "data_criacao", "data_atualizacao",
    )
    list_editable = ("status_pedido",)
    inlines = [ItemPedidoInline]


# =====================================================================
# CONTATO
# =====================================================================

@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ("assunto", "nome", "email", "status", "data_envio")
    list_filter = ("status",)
    search_fields = ("nome", "email", "assunto", "mensagem")
    readonly_fields = ("nome", "email", "assunto", "mensagem", "usuario", "data_envio")
    list_editable = ("status",)


# =====================================================================
# AVALIAÇÕES
# =====================================================================

@admin.register(Avaliacao)
class AvaliacaoAdmin(admin.ModelAdmin):
    list_display = ("produto", "usuario", "nota", "status", "data_avaliacao")
    list_filter = ("status", "nota")
    search_fields = ("produto__nome", "usuario__email")
    autocomplete_fields = ("usuario", "produto", "pedido")
    readonly_fields = ("data_avaliacao",)